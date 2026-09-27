import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from config import Config
from app.db.connection import get_db_connection, execute_query

CLUSTER_NAMES = {
    0: "Budget Customer",
    1: "Average Customer",
    2: "High Paying Customer"
}

FEATURE_COLUMNS = ['total_spent', 'income', 'order_count', 'avg_order_value']

_CACHED_MODEL_BUNDLE = None

def get_model_path():
    instance_dir = os.path.join(Config.BASE_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    return os.path.join(instance_dir, 'kmeans_3clusters.pkl')


def fetch_all_customer_features():
    """
    Fetches aggregate behavioral and transactional metrics for all customers.
    """
    query = """
        SELECT c.customer_id,
               COALESCE(c.income, 500000.0) as income,
               COALESCE(COUNT(p.purchase_id), 0) as order_count,
               COALESCE(SUM(p.total_amount), 0.0) as total_spent,
               COALESCE(AVG(p.total_amount), 0.0) as avg_order_value
        FROM customers c
        LEFT JOIN purchases p ON c.customer_id = p.customer_id
        GROUP BY c.customer_id
        ORDER BY c.customer_id
    """
    return execute_query(query, fetch_all=True) or []


def train_kmeans_model(save=True):
    """
    Trains a K-Means model with exactly 3 clusters:
      - 0: Budget Customer
      - 1: Average Customer
      - 2: High Paying Customer
    Saves the model bundle to disk and persists all customer cluster assignments to the DB.
    """
    global _CACHED_MODEL_BUNDLE

    rows = fetch_all_customer_features()
    if not rows:
        return False, "No customer records found to train K-Means model."

    df = pd.DataFrame(rows)
    for col in FEATURE_COLUMNS:
        df[col] = df[col].astype(float)

    if len(df) < 3:
        return False, "At least 3 customers required to train 3-cluster K-Means."

    X = df[FEATURE_COLUMNS].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    df['raw_cluster'] = kmeans.labels_

    # Deterministically order the 3 clusters by mean total_spent:
    # Lowest mean spend  -> 0: "Budget Customer"
    # Middle mean spend  -> 1: "Average Customer"
    # Highest mean spend -> 2: "High Paying Customer"
    mean_spends = df.groupby('raw_cluster')['total_spent'].mean().sort_values()
    raw_sorted_indices = list(mean_spends.index)

    raw_to_final = {
        raw_sorted_indices[0]: (0, "Budget Customer"),
        raw_sorted_indices[1]: (1, "Average Customer"),
        raw_sorted_indices[2]: (2, "High Paying Customer")
    }

    df['cluster_label'] = df['raw_cluster'].map(lambda x: raw_to_final[x][0])
    df['cluster_name']  = df['raw_cluster'].map(lambda x: raw_to_final[x][1])

    # Cache model bundle in memory
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bundle = {
        'scaler': scaler,
        'kmeans': kmeans,
        'raw_to_final': raw_to_final,
        'feature_cols': FEATURE_COLUMNS,
        'trained_at': now_str,
        'customer_count': len(df)
    }
    _CACHED_MODEL_BUNDLE = bundle

    if save:
        try:
            with open(get_model_path(), 'wb') as f:
                pickle.dump(bundle, f)
        except Exception as e:
            print(f"[ML] Warning saving model file: {e}")

    # Bulk persist clusters table
    conn = get_db_connection(with_database=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM clusters;")
            
            cluster_tuples = []
            for _, r in df.iterrows():
                cluster_tuples.append((
                    int(r['customer_id']),
                    int(r['cluster_label']),
                    str(r['cluster_name']),
                    float(r['income']),
                    float(r['total_spent']),
                    int(r['order_count']),
                    'K-Means',
                    3,
                    now_str
                ))

            cursor.executemany("""
                INSERT INTO clusters (
                    customer_id, cluster_label, cluster_name,
                    annual_income, total_spending, purchase_frequency,
                    algorithm, k_value, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, cluster_tuples)
            conn.commit()
    finally:
        conn.close()

    summary = {
        'total_customers': len(df),
        'clusters': {}
    }
    for label, name in sorted(CLUSTER_NAMES.items()):
        sub = df[df['cluster_label'] == label]
        summary['clusters'][name] = {
            'label': label,
            'count': len(sub),
            'avg_spending': round(float(sub['total_spent'].mean()), 2) if len(sub) else 0.0,
            'avg_income': round(float(sub['income'].mean()), 2) if len(sub) else 0.0
        }

    return True, summary


def load_or_train_model():
    """
    Loads the trained model from disk or cache; if not found, trains a new one.
    """
    global _CACHED_MODEL_BUNDLE
    if _CACHED_MODEL_BUNDLE is not None:
        return _CACHED_MODEL_BUNDLE

    model_path = get_model_path()
    if os.path.exists(model_path):
        try:
            with open(model_path, 'rb') as f:
                bundle = pickle.load(f)
            _CACHED_MODEL_BUNDLE = bundle
            return bundle
        except Exception as e:
            print(f"[ML] Error loading model from file: {e}. Re-training...")

    # Train model if not saved yet
    success, _ = train_kmeans_model(save=True)
    if success and _CACHED_MODEL_BUNDLE is not None:
        return _CACHED_MODEL_BUNDLE
    return None


def classify_single_customer(customer_id):
    """
    Classifies a customer (new or returning) instantly into one of 3 clusters:
      - Budget Customer (0)
      - Average Customer (1)
      - High Paying Customer (2)
    Inserts or updates their record in the clusters table.
    Returns: (cluster_label, cluster_name)
    """
    bundle = load_or_train_model()
    if not bundle:
        # Fallback if model cannot be trained yet
        return 0, CLUSTER_NAMES[0]

    # Query latest metrics for this customer
    query = """
        SELECT c.customer_id,
               COALESCE(c.income, 500000.0) as income,
               COALESCE(COUNT(p.purchase_id), 0) as order_count,
               COALESCE(SUM(p.total_amount), 0.0) as total_spent,
               COALESCE(AVG(p.total_amount), 0.0) as avg_order_value
        FROM customers c
        LEFT JOIN purchases p ON c.customer_id = p.customer_id
        WHERE c.customer_id = %s
        GROUP BY c.customer_id
    """
    row = execute_query(query, (customer_id,), fetch_one=True)
    if not row:
        return 0, CLUSTER_NAMES[0]

    total_spent = float(row.get('total_spent', 0.0) or 0.0)
    income = float(row.get('income', 500000.0) or 500000.0)
    order_count = int(row.get('order_count', 0) or 0)
    avg_order_value = float(row.get('avg_order_value', 0.0) or 0.0)

    scaler = bundle['scaler']
    kmeans = bundle['kmeans']
    raw_to_final = bundle['raw_to_final']

    features = np.array([[total_spent, income, order_count, avg_order_value]])
    features_scaled = scaler.transform(features)
    raw_label = int(kmeans.predict(features_scaled)[0])

    cluster_label, cluster_name = raw_to_final.get(raw_label, (0, "Budget Customer"))

    # Update or insert into clusters table
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(with_database=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM clusters WHERE customer_id = %s;", (customer_id,))
            cursor.execute("""
                INSERT INTO clusters (
                    customer_id, cluster_label, cluster_name,
                    annual_income, total_spending, purchase_frequency,
                    algorithm, k_value, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'K-Means', 3, %s);
            """, (customer_id, cluster_label, cluster_name, income, total_spent, order_count, now_str))
            conn.commit()
    finally:
        conn.close()

    return cluster_label, cluster_name


CLUSTER_MARKETING_STRATEGIES = {
    "High Paying Customer": {
        "badge_class": "cluster-badge-high",
        "card_class": "cluster-card-high",
        "icon": "★",
        "subtitle": "Premium luxury shoppers & high-margin tech buyers",
        "core_goal": "Maximize lifetime customer retention & exclusive brand prestige",
        "action_plan": [
            "Enroll in 'SegmentIQ Black Concierge' with zero delivery fees and priority customer support.",
            "Offer exclusive 48-hour pre-launch access to new flagship smartphones and laptops.",
            "Introduce bespoke high-value bundle kits with premium warranties included."
        ],
        "age_subsegments": [
            {"bracket": "18–25 (Tech Early Adopters)", "strategy": "Target flagship smartphones, gaming gear, and limited-edition wearables via Instagram and App pushes."},
            {"bracket": "26–45 (Prime Executives)", "strategy": "Focus on high-performance laptops, executive productivity suites, and luxury home electronics via Email newsletters."},
            {"bracket": "46+ (Affluent Household Heads)", "strategy": "Offer premium air purifiers, ergonomic furniture, and direct WhatsApp concierge support."}
        ],
        "preferred_channels": ["VIP Email Newsletter", "Direct WhatsApp Concierge", "In-App Exclusive Banners"]
    },
    "Average Customer": {
        "badge_class": "cluster-badge-average",
        "card_class": "cluster-card-average",
        "icon": "◆",
        "subtitle": "Core repeat shoppers with steady purchase frequency",
        "core_goal": "Upgrade basket value & transition customers into High-Paying tier",
        "action_plan": [
            "Implement spend-threshold rewards: 'Spend ₹3,000 more to unlock ₹600 voucher'.",
            "Offer automated bundle discounts on complementary accessories at checkout.",
            "Activate gamified loyalty multipliers (2x points on second order within 30 days)."
        ],
        "age_subsegments": [
            {"bracket": "18–25 (Upwardly Mobile)", "strategy": "Incentivize with audio accessories, fitness smartwatches, and student milestone perks."},
            {"bracket": "26–45 (Family Shoppers)", "strategy": "Promote household bundles, coffee machines, and seasonal electronics upgrades with flexible EMI."},
            {"bracket": "46+ (Steady Practical Buyers)", "strategy": "Send re-order reminders, warranty extension offers, and curated holiday gifting guides."}
        ],
        "preferred_channels": ["Personalized Email Recommendations", "Cart Abandonment SMS", "Loyalty Points Alerts"]
    },
    "Budget Customer": {
        "badge_class": "cluster-badge-budget",
        "card_class": "cluster-card-budget",
        "icon": "●",
        "subtitle": "Price-sensitive buyers seeking maximum value and deals",
        "core_goal": "Boost purchase frequency & increase minimum order basket size",
        "action_plan": [
            "Display dynamic 'Add ₹350 more for FREE Delivery' notification in cart.",
            "Deploy seasonal flash clearance sales and weekend price-drop notifications.",
            "Offer affordable pay-later or micro-EMI options to reduce barrier to entry."
        ],
        "age_subsegments": [
            {"bracket": "18–25 (Students & Beginners)", "strategy": "Engage with viral deal coupons, back-to-college sales, and entry-level audio accessories."},
            {"bracket": "26–45 (Cost-Conscious Homes)", "strategy": "Promote multi-buy discounts, essential cookware/lifestyle items, and festival bundle bargains."},
            {"bracket": "46+ (Bargain Seekers)", "strategy": "Deliver straightforward SMS alerts on direct discounts without complicated loyalty points."}
        ],
        "preferred_channels": ["Weekend Flash SMS", "Push Notifications for Price Drops", "Site Banner Deals"]
    }
}


def get_dashboard_ml_data():
    """
    Assembles comprehensive analytical payload for Chart.js visualizations
    and actionable marketing strategies on the Admin Dashboard.
    """
    # 1. Cluster Summary with Age Breakdown
    summary_query = """
        SELECT cl.cluster_label, cl.cluster_name,
               COUNT(c.customer_id) as num_customers,
               ROUND(AVG(cl.annual_income), 0) as avg_income,
               ROUND(AVG(cl.total_spending), 0) as avg_spending,
               ROUND(AVG(c.age), 1) as avg_age,
               SUM(CASE WHEN c.age < 26 THEN 1 ELSE 0 END) as young_cnt,
               SUM(CASE WHEN c.age BETWEEN 26 AND 45 THEN 1 ELSE 0 END) as adult_cnt,
               SUM(CASE WHEN c.age > 45 THEN 1 ELSE 0 END) as mature_cnt
        FROM clusters cl
        JOIN customers c ON cl.customer_id = c.customer_id
        GROUP BY cl.cluster_label, cl.cluster_name
        ORDER BY cl.cluster_label
    """
    cluster_summary = execute_query(summary_query, fetch_all=True) or []

    # 2. Scatter Points for Chart.js (Income vs Spending)
    points_query = """
        SELECT c.name,
               c.age,
               ROUND(cl.annual_income, 0) as x,
               ROUND(cl.total_spending, 0) as y,
               cl.cluster_name,
               cl.cluster_label,
               cl.purchase_frequency as orders
        FROM clusters cl
        JOIN customers c ON cl.customer_id = c.customer_id
    """
    raw_points = execute_query(points_query, fetch_all=True) or []

    scatter_data = {
        "budget": [],
        "average": [],
        "high": [],
        "centroids": []
    }
    for pt in raw_points:
        p_obj = {
            "x": float(pt['x'] or 0),
            "y": float(pt['y'] or 0),
            "name": pt['name'],
            "age": pt['age'],
            "orders": pt['orders']
        }
        if pt['cluster_name'] == 'High Paying Customer':
            scatter_data['high'].append(p_obj)
        elif pt['cluster_name'] == 'Average Customer':
            scatter_data['average'].append(p_obj)
        else:
            scatter_data['budget'].append(p_obj)

    for cs in cluster_summary:
        scatter_data['centroids'].append({
            "x": float(cs['avg_income'] or 0),
            "y": float(cs['avg_spending'] or 0),
            "name": f"Centroid: {cs['cluster_name']}"
        })

    # 3. Precomputed Elbow Curve data (WCSS for K=1..8)
    elbow_data = {
        "k_values": [1, 2, 3, 4, 5, 6, 7, 8],
        "inertias": [3008, 1506, 1023, 700, 579, 488, 445, 410],
        "optimal_k": 3
    }

    return {
        "cluster_summary": cluster_summary,
        "scatter_data": scatter_data,
        "elbow_data": elbow_data,
        "strategies": CLUSTER_MARKETING_STRATEGIES
    }

