import os
import random
import datetime
import math
import pandas as pd
import numpy as np

# Try importing Faker, provide custom fallback if not present
try:
    from faker import Faker
    fake = Faker('en_IN')
except ImportError:
    fake = None

# ==========================================
# 1. CONFIGURATION
# ==========================================
NUM_CUSTOMERS = 750
NUM_PURCHASES = 7500
NUM_PRODUCTS = 20
SEED = 42
OUTPUT_DIR = "generated_dataset"

# Minimum requirement checks
assert NUM_CUSTOMERS >= 500, "NUM_CUSTOMERS must be >= 500"
assert NUM_PURCHASES >= 5000, "NUM_PURCHASES must be >= 5000"
assert NUM_PRODUCTS >= 15, "NUM_PRODUCTS must be >= 15"

# Set random seeds for 100% reproducibility
random.seed(SEED)
np.random.seed(SEED)
if fake:
    Faker.seed(SEED)

# ==========================================
# 2. SEED DATA & CONSTANTS
# ==========================================
CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad",
    "Chennai", "Kolkata", "Surat", "Pune", "Jaipur",
    "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Vadodara", "Ghaziabad", "Ludhiana"
]

FIRST_NAMES_MALE = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharva", "Advait", "Pranav", "Adhiraj", "Rohan", "Kabir", "Karan", "Rahul", "Vikram", "Amit", "Rajesh", "Sanjay", "Sunil", "Manish"]
FIRST_NAMES_FEMALE = ["Aanya", "Aadhya", "Ananya", "Pari", "Anika", "Navya", "Diya", "Vanya", "Myra", "Sara", "Ira", "Ahana", "Anvi", "Prisha", "Riya", "Kavya", "Sneha", "Pooja", "Priya", "Neha", "Meera", "Swati", "Shreya", "Deepika", "Sunita"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Shah", "Mehta", "Joshi", "Rao", "Nair", "Reddy", "Chowdhury", "Das", "Mukherjee", "Banerjee", "Deshmukh", "Kulkarni", "Jain", "Agarwal", "Bhasin", "Capoor", "Chawla", "Gill", "Malhotra"]

PRODUCT_CATALOG = [
    {"name": "Smartphone Pro Max", "category": "Electronics", "price": 65000.0, "max_qty": 2, "tier": "premium", "desc": "6.7-inch OLED display, 256GB storage, triple camera system."},
    {"name": "High-Performance Laptop", "category": "Electronics", "price": 85000.0, "max_qty": 2, "tier": "premium", "desc": "Intel Core i7, 16GB RAM, 512GB SSD, dedicated GPU."},
    {"name": "Tablet Ultra", "category": "Electronics", "price": 32000.0, "max_qty": 3, "tier": "high", "desc": "11-inch Retina screen, stylus support, 128GB."},
    {"name": "Smart Fitness Watch", "category": "Electronics", "price": 12500.0, "max_qty": 3, "tier": "mid", "desc": "AMOLED display, SPO2 tracking, 14-day battery life."},
    {"name": "Wireless Noise-Canceling Earbuds", "category": "Mobile Accessories", "price": 4500.0, "max_qty": 4, "tier": "mid", "desc": "Active Noise Cancellation, Bluetooth 5.3, IPX4 water resistance."},
    {"name": "Portable Bluetooth Speaker", "category": "Mobile Accessories", "price": 2800.0, "max_qty": 4, "tier": "mid", "desc": "360-degree sound, 20W output, waterproof casing."},
    {"name": "Fast Charge Power Bank 20000mAh", "category": "Mobile Accessories", "price": 1800.0, "max_qty": 5, "tier": "budget", "desc": "Triple output ports, 22.5W fast charging capacity."},
    {"name": "Mechanical RGB Gaming Keyboard", "category": "Gaming", "price": 4200.0, "max_qty": 5, "tier": "mid", "desc": "Tactile blue switches, customizable RGB backlight."},
    {"name": "Wireless Ergonomic Gaming Mouse", "category": "Gaming", "price": 1900.0, "max_qty": 5, "tier": "budget", "desc": "16000 DPI sensor, ultra-lightweight design."},
    {"name": "Water-Resistant Backpack", "category": "Fashion", "price": 2200.0, "max_qty": 5, "tier": "budget", "desc": "Laptop compartment, anti-theft design, 30L capacity."},
    {"name": "Professional Running Shoes", "category": "Sports", "price": 4500.0, "max_qty": 3, "tier": "mid", "desc": "Breathable mesh upper, high-cushion rubber sole."},
    {"name": "Premium Cotton T-Shirt", "category": "Fashion", "price": 850.0, "max_qty": 6, "tier": "budget", "desc": "100% combed organic cotton, pre-shrunk fabric."},
    {"name": "Automatic Coffee Maker Machine", "category": "Home Appliances", "price": 14500.0, "max_qty": 2, "tier": "high", "desc": "15-bar pressure pump, milk frother wand attached."},
    {"name": "Insulated Stainless Steel Water Bottle", "category": "Sports", "price": 650.0, "max_qty": 8, "tier": "budget", "desc": "Double-wall vacuum insulation, keeps drinks cold for 24h."},
    {"name": "Dimmable LED Desk Lamp", "category": "Office Supplies", "price": 1200.0, "max_qty": 5, "tier": "budget", "desc": "Touch control panel, 5 color temperature modes, USB charging port."},
    {"name": "Executive Hardcover Notebook", "category": "Office Supplies", "price": 450.0, "max_qty": 10, "tier": "budget", "desc": "200 pages, 100 GSM acid-free paper, ribbon bookmark."},
    {"name": "HEPA Filter Air Purifier", "category": "Home Appliances", "price": 18500.0, "max_qty": 2, "tier": "high", "desc": "True HEPA 13 filter, CADR 300m3/h, real-time air quality indicator."},
    {"name": "Organic Darjeeling Green Tea 250g", "category": "Grocery", "price": 550.0, "max_qty": 8, "tier": "budget", "desc": "Hand-picked whole leaf green tea rich in antioxidants."},
    {"name": "Hydrating Face Serum 50ml", "category": "Beauty", "price": 1250.0, "max_qty": 5, "tier": "mid", "desc": "Hyaluronic acid and Vitamin C skin radiance formula."},
    {"name": "Bestseller Fiction Hardcover Book", "category": "Books", "price": 499.0, "max_qty": 5, "tier": "budget", "desc": "Internationally acclaimed bestseller novel."}
]

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def generate_name(gender):
    if fake:
        if gender == "Male":
            return fake.name_male()
        elif gender == "Female":
            return fake.name_female()
        else:
            return fake.name()
    else:
        fname = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        lname = random.choice(LAST_NAMES)
        return f"{fname} {lname}"

def generate_phone(idx):
    # Fictional non-real 10-digit phone number starting with 9876 range
    base = 9876000000 + idx
    return f"+91{base}"

def generate_email(name, idx):
    clean_name = "".join(e for e in name.lower() if e.isalnum())
    domains = ["example.com", "testmail.com", "syntheticdata.org", "demo-mail.com"]
    domain = domains[idx % len(domains)]
    return f"{clean_name}{idx}@{domain}"

def sample_income():
    """Middle-income peaked log-normal distribution between 120,000 and 3,000,000 INR"""
    mean_log = math.log(650000)
    sigma_log = 0.65
    val = np.random.lognormal(mean_log, sigma_log)
    val = max(120000.0, min(3000000.0, val))
    return round(float(val), 2)

def sample_purchase_date(start_date, end_date):
    """Generate realistic date with seasonal peaks (Oct-Nov Diwali, Dec Year-end, May Summer)"""
    delta_days = (end_date - start_date).days
    
    while True:
        random_day = random.randint(0, delta_days)
        candidate_date = start_date + datetime.timedelta(days=random_day, seconds=random.randint(0, 86399))
        month = candidate_date.month
        
        # Seasonal weighting
        weight = 1.0
        if month in [10, 11]: # Diwali / Festival season
            weight = 2.2
        elif month in [12]:   # Year-end sale
            weight = 1.8
        elif month in [5]:    # Summer sale
            weight = 1.5
            
        if random.random() < (weight / 2.5):
            return candidate_date

# ==========================================
# 4. DATA GENERATION FUNCTIONS
# ==========================================

def generate_customers(num_customers):
    """
    Generate customer records with hidden behavioral profiles.
    Profiles:
      A: High Value (High income, premium preference)
      B: Regular (Medium income, mid-range preference)
      C: Budget (Lower income, budget preference)
      D: Frequent Low-Value (Moderate income, frequent small purchases)
      E: Occasional (Variable income, rare purchases)
    """
    profiles = ["High Value", "Regular", "Budget", "Frequent Low-Value", "Occasional"]
    profile_weights = [0.15, 0.35, 0.25, 0.15, 0.10]
    
    customers = []
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=730)
    
    for i in range(1, num_customers + 1):
        cid = f"C{i:05d}"
        gender = random.choices(["Male", "Female", "Other"], weights=[0.49, 0.49, 0.02])[0]
        name = generate_name(gender)
        age = int(np.clip(np.random.normal(36, 12), 18, 70))
        phone = generate_phone(i)
        email = generate_email(name, i)
        city = random.choice(CITIES)
        
        # Profile assignment
        profile = random.choices(profiles, weights=profile_weights)[0]
        
        # Profile-influenced income
        if profile == "High Value":
            income = round(float(np.random.uniform(1400000, 3000000)), 2)
        elif profile == "Regular":
            income = round(float(np.random.uniform(500000, 1400000)), 2)
        elif profile == "Budget":
            income = round(float(np.random.uniform(120000, 500000)), 2)
        elif profile == "Frequent Low-Value":
            income = round(float(np.random.uniform(350000, 900000)), 2)
        else: # Occasional
            income = sample_income()
            
        created_at = start_date + datetime.timedelta(days=random.randint(0, 500))
        status = "Active"
        
        customers.append({
            "customer_id": cid,
            "name": name,
            "age": age,
            "gender": gender,
            "city": city,
            "phone": phone,
            "email": email,
            "annual_income": income,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "_profile": profile
        })
        
    return customers

def generate_products(catalog):
    """Generate product dictionary list from catalog"""
    products = []
    for idx, p in enumerate(catalog, 1):
        pid = f"P{idx:04d}"
        products.append({
            "product_id": pid,
            "product_name": p["name"],
            "category": p["category"],
            "description": p["desc"],
            "price": p["price"],
            "stock_quantity": 0,
            "status": "Active",
            "_max_qty": p["max_qty"],
            "_tier": p["tier"]
        })
    return products

def generate_purchases_and_items(customers, products, target_total_purchases):
    """
    Generate transactions connecting customers and products.
    Enforces profile-based transaction counts and item preference selection.
    """
    purchases = []
    purchase_items = []
    
    # 1. Allocate purchase count targets per customer based on profile
    customer_target_counts = {}
    for c in customers:
        p = c["_profile"]
        if p == "Frequent Low-Value":
            count = random.randint(14, 25)
        elif p == "High Value":
            count = random.randint(8, 20)
        elif p == "Regular":
            count = random.randint(5, 12)
        elif p == "Budget":
            count = random.randint(2, 6)
        else: # Occasional
            count = random.randint(1, 4)
        customer_target_counts[c["customer_id"]] = count
        
    # Scale counts proportionately so total sum equals target_total_purchases
    current_sum = sum(customer_target_counts.values())
    scaling = target_total_purchases / current_sum
    
    allocated_counts = {}
    for cid, cnt in customer_target_counts.items():
        allocated_counts[cid] = max(1, int(round(cnt * scaling)))
        
    # Adjust exact sum difference
    diff = target_total_purchases - sum(allocated_counts.values())
    cids = list(allocated_counts.keys())
    for i in range(abs(diff)):
        cid = random.choice(cids)
        if diff > 0:
            allocated_counts[cid] += 1
        elif allocated_counts[cid] > 1:
            allocated_counts[cid] -= 1

    # Product pools by tier for customer profile selection
    premium_prods = [p for p in products if p["_tier"] in ["premium", "high"]]
    mid_prods = [p for p in products if p["_tier"] in ["mid", "high"]]
    budget_prods = [p for p in products if p["_tier"] in ["budget", "mid"]]
    all_prods = products
    
    product_units_sold = {p["product_id"]: 0 for p in products}
    
    start_date = datetime.datetime.now() - datetime.timedelta(days=365)
    end_date = datetime.datetime.now()
    
    purchase_counter = 1
    item_counter = 1
    
    for c in customers:
        cid = c["customer_id"]
        profile = c["_profile"]
        n_purchases = allocated_counts[cid]
        
        cust_reg_date = datetime.datetime.strptime(c["created_at"], "%Y-%m-%d %H:%M:%S")
        cust_start_date = max(start_date, cust_reg_date)
        
        for _ in range(n_purchases):
            pur_id = f"PUR{purchase_counter:06d}"
            pur_date = sample_purchase_date(cust_start_date, end_date)
            
            if profile == "High Value":
                chosen_pool = random.choices([premium_prods, mid_prods, budget_prods], weights=[0.65, 0.25, 0.10])[0]
            elif profile == "Regular":
                chosen_pool = random.choices([mid_prods, budget_prods, premium_prods], weights=[0.55, 0.35, 0.10])[0]
            elif profile == "Budget":
                chosen_pool = random.choices([budget_prods, mid_prods], weights=[0.80, 0.20])[0]
            elif profile == "Frequent Low-Value":
                chosen_pool = random.choices([budget_prods, mid_prods], weights=[0.75, 0.25])[0]
            else: # Occasional
                chosen_pool = random.choices([all_prods, budget_prods], weights=[0.50, 0.50])[0]
                
            num_items = random.choices([1, 2, 3, 4], weights=[0.50, 0.30, 0.15, 0.05])[0]
            selected_items = random.sample(chosen_pool, k=min(num_items, len(chosen_pool)))
            
            purchase_total = 0.0
            
            for prod in selected_items:
                item_id = f"ITEM{item_counter:07d}"
                max_q = prod["_max_qty"]
                
                qty = random.randint(1, max_q)
                unit_price = prod["price"]
                subtotal = round(qty * unit_price, 2)
                
                purchase_total += subtotal
                product_units_sold[prod["product_id"]] += qty
                
                purchase_items.append({
                    "purchase_item_id": item_id,
                    "purchase_id": pur_id,
                    "product_id": prod["product_id"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "subtotal": subtotal
                })
                item_counter += 1
                
            purchases.append({
                "purchase_id": pur_id,
                "customer_id": cid,
                "purchase_date": pur_date.strftime("%Y-%m-%d %H:%M:%S"),
                "total_amount": round(purchase_total, 2),
                "status": "Completed"
            })
            purchase_counter += 1

    # Update product stock and status
    for prod in products:
        rem_stock = random.choice([0, random.randint(15, 120)]) if random.random() < 0.10 else random.randint(20, 200)
        prod["stock_quantity"] = rem_stock
        prod["status"] = "Out of Stock" if rem_stock == 0 else "Active"
        
    return purchases, purchase_items

def generate_customer_features(customers, purchases, purchase_items):
    """
    Generate derived analytical dataset for K-Means clustering.
    Calculates age, income, total_spending, purchase_count, average_order_value,
    purchase_frequency, unique_products_purchased, average_quantity.
    """
    df_pur = pd.DataFrame(purchases)
    df_items = pd.DataFrame(purchase_items)
    
    df_merged = df_items.merge(df_pur[['purchase_id', 'customer_id', 'purchase_date']], on='purchase_id')
    
    features = []
    
    for c in customers:
        cid = c["customer_id"]
        c_purs = df_pur[df_pur["customer_id"] == cid]
        c_items = df_merged[df_merged["customer_id"] == cid]
        
        p_count = len(c_purs)
        total_spending = round(c_purs["total_amount"].sum(), 2) if p_count > 0 else 0.0
        aov = round(total_spending / p_count, 2) if p_count > 0 else 0.0
        unique_prods = c_items["product_id"].nunique() if p_count > 0 else 0
        avg_qty = round(c_items["quantity"].mean(), 2) if len(c_items) > 0 else 0.0
        
        if p_count > 1:
            dates = pd.to_datetime(c_purs["purchase_date"]).sort_values()
            span_days = max(1, (dates.max() - dates.min()).days)
            freq = round((p_count / span_days) * 30.0, 2)
        else:
            freq = 1.00
            
        features.append({
            "customer_id": cid,
            "age": c["age"],
            "annual_income": c["annual_income"],
            "purchase_count": p_count,
            "total_spending": total_spending,
            "average_order_value": aov,
            "purchase_frequency": freq,
            "unique_products_purchased": unique_prods,
            "average_quantity": avg_qty
        })
        
    return features

# ==========================================
# 5. VALIDATION & EXPORT FUNCTIONS
# ==========================================

def validate_dataset(customers, products, purchases, purchase_items, customer_features):
    """Perform full referential integrity and quality checks"""
    print("\n" + "="*50)
    print("      DATASET VALIDATION REPORT")
    print("="*50)
    
    errors = []
    
    if len(customers) < 500:
        errors.append(f"Customer count ({len(customers)}) < minimum 500")
    if len(purchases) < 5000:
        errors.append(f"Purchase count ({len(purchases)}) < minimum 5000")
    if len(products) < 15:
        errors.append(f"Product count ({len(products)}) < minimum 15")
        
    cust_ids = [c["customer_id"] for c in customers]
    phones = [c["phone"] for c in customers]
    emails = [c["email"] for c in customers]
    prod_ids = [p["product_id"] for p in products]
    pur_ids = [p["purchase_id"] for p in purchases]
    item_ids = [i["purchase_item_id"] for i in purchase_items]
    
    check_unique = [
        ("Customer IDs", cust_ids),
        ("Phone numbers", phones),
        ("Emails", emails),
        ("Product IDs", prod_ids),
        ("Purchase IDs", pur_ids),
        ("Purchase Item IDs", item_ids)
    ]
    
    for name, lst in check_unique:
        status = "PASS" if len(lst) == len(set(lst)) else "FAIL"
        print(f"Unique {name:<22}: {status} ({len(set(lst))}/{len(lst)})")
        if status == "FAIL":
            errors.append(f"Duplicate values found in {name}")
            
    cust_set = set(cust_ids)
    prod_set = set(prod_ids)
    pur_set = set(pur_ids)
    
    invalid_cust_refs = sum(1 for p in purchases if p["customer_id"] not in cust_set)
    invalid_pur_refs = sum(1 for i in purchase_items if i["purchase_id"] not in pur_set)
    invalid_prod_refs = sum(1 for i in purchase_items if i["product_id"] not in prod_set)
    
    print(f"Valid Customer references   : {'PASS' if invalid_cust_refs == 0 else 'FAIL'} (Invalid: {invalid_cust_refs})")
    print(f"Valid Purchase references   : {'PASS' if invalid_pur_refs == 0 else 'FAIL'} (Invalid: {invalid_pur_refs})")
    print(f"Valid Product references    : {'PASS' if invalid_prod_refs == 0 else 'FAIL'} (Invalid: {invalid_prod_refs})")
    
    if invalid_cust_refs > 0 or invalid_pur_refs > 0 or invalid_prod_refs > 0:
        errors.append("Referential integrity checks failed")
        
    invalid_subtotals = 0
    for i in purchase_items:
        expected = round(i["quantity"] * i["unit_price"], 2)
        if abs(i["subtotal"] - expected) > 0.01 or i["quantity"] <= 0 or i["unit_price"] <= 0:
            invalid_subtotals += 1
            
    item_sums = {}
    for i in purchase_items:
        item_sums[i["purchase_id"]] = item_sums.get(i["purchase_id"], 0.0) + i["subtotal"]
        
    invalid_pur_totals = 0
    for p in purchases:
        expected = round(item_sums.get(p["purchase_id"], 0.0), 2)
        if abs(p["total_amount"] - expected) > 0.01:
            invalid_pur_totals += 1
            
    neg_incomes = sum(1 for c in customers if c["annual_income"] <= 0)
    neg_stocks = sum(1 for p in products if p["stock_quantity"] < 0)
    
    print(f"Subtotal calculation errors : {invalid_subtotals}")
    print(f"Purchase total math errors  : {invalid_pur_totals}")
    print(f"Negative income values      : {neg_incomes}")
    print(f"Negative stock values       : {neg_stocks}")
    
    if invalid_subtotals > 0 or invalid_pur_totals > 0 or neg_incomes > 0 or neg_stocks > 0:
        errors.append("Mathematical or data bound checks failed")
        
    print("-" * 50)
    if not errors:
        print("OVERALL VALIDATION STATUS  : SUCCESS (ALL CHECKS PASSED)")
    else:
        print("OVERALL VALIDATION STATUS  : FAILED")
        for e in errors:
            print(f" - {e}")
    print("=" * 50 + "\n")
    return len(errors) == 0

def save_datasets(output_dir, customers, products, purchases, purchase_items, customer_features):
    """Save clean CSV files without internal generation metadata columns"""
    os.makedirs(output_dir, exist_ok=True)
    
    clean_cust = [{k: v for k, v in c.items() if not k.startswith("_")} for c in customers]
    clean_prod = [{k: v for k, v in p.items() if not k.startswith("_")} for p in products]
    
    pd.DataFrame(clean_cust).to_csv(os.path.join(output_dir, "customers.csv"), index=False)
    pd.DataFrame(clean_prod).to_csv(os.path.join(output_dir, "products.csv"), index=False)
    pd.DataFrame(purchases).to_csv(os.path.join(output_dir, "purchases.csv"), index=False)
    pd.DataFrame(purchase_items).to_csv(os.path.join(output_dir, "purchase_items.csv"), index=False)
    pd.DataFrame(customer_features).to_csv(os.path.join(output_dir, "customer_features.csv"), index=False)

def generate_summary(output_dir, customers, products, purchases, purchase_items, customer_features):
    """Write dataset_summary.txt with analytical metrics"""
    df_cust = pd.DataFrame(customers)
    df_prod = pd.DataFrame(products)
    df_pur = pd.DataFrame(purchases)
    df_items = pd.DataFrame(purchase_items)
    df_feat = pd.DataFrame(customer_features)
    
    dates = pd.to_datetime(df_pur["purchase_date"])
    min_date = dates.min().strftime("%Y-%m-%d")
    max_date = dates.max().strftime("%Y-%m-%d")
    
    tot_revenue = df_pur["total_amount"].sum()
    avg_income = df_cust["annual_income"].mean()
    min_income = df_cust["annual_income"].min()
    max_income = df_cust["annual_income"].max()
    
    avg_pur_val = df_pur["total_amount"].mean()
    min_pur_val = df_pur["total_amount"].min()
    max_pur_val = df_pur["total_amount"].max()
    
    prod_sales = df_items.groupby("product_id")["quantity"].sum().reset_index()
    prod_sales = prod_sales.merge(df_prod[["product_id", "product_name"]], on="product_id")
    top_prod = prod_sales.sort_values(by="quantity", ascending=False).iloc[0]
    low_prod = prod_sales.sort_values(by="quantity", ascending=True).iloc[0]
    
    top_cust = df_feat.sort_values(by="total_spending", ascending=False).iloc[0]
    avg_pur_per_cust = len(df_pur) / len(df_cust)
    
    summary_text = f"""==================================================
   CUSTOMER SEGMENTATION SYSTEM - DATASET SUMMARY
==================================================
Generated Date              : {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Random Seed                 : {SEED}

1. DATASET ENTITY COUNTS
--------------------------------------------------
Total Customers             : {len(df_cust):,}
Total Products              : {len(df_prod):,}
Total Purchases             : {len(df_pur):,}
Total Purchase Items        : {len(df_items):,}
Date Range                  : {min_date} to {max_date}

2. FINANCIAL & CUSTOMER METRICS (INR ₹)
--------------------------------------------------
Total Revenue               : ₹{tot_revenue:,.2f}
Average Customer Income     : ₹{avg_income:,.2f}
Minimum Customer Income     : ₹{min_income:,.2f}
Maximum Customer Income     : ₹{max_income:,.2f}

Average Purchase Value      : ₹{avg_pur_val:,.2f}
Minimum Purchase Value      : ₹{min_pur_val:,.2f}
Maximum Purchase Value      : ₹{max_pur_val:,.2f}

3. SALES & ACTIVITY HIGHLIGHTS
--------------------------------------------------
Average Purchases / Customer: {avg_pur_per_cust:.2f}
Top Selling Product         : {top_prod['product_name']} ({top_prod['quantity']} units)
Lowest Selling Product      : {low_prod['product_name']} ({low_prod['quantity']} units)
Most Active Customer (ID)   : {top_cust['customer_id']} (₹{top_cust['total_spending']:,.2f} total spending)

==================================================
Files Generated in '{output_dir}/':
 - customers.csv
 - products.csv
 - purchases.csv
 - purchase_items.csv
 - customer_features.csv
 - dataset_summary.txt
==================================================
"""
    summary_filepath = os.path.join(output_dir, "dataset_summary.txt")
    with open(summary_filepath, "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(f"Summary written to {summary_filepath}")

# ==========================================
# 6. MAIN EXECUTION FLOW
# ==========================================
def main():
    print(f"Generating synthetic dataset with seed={SEED}...")
    print(f"Target: {NUM_CUSTOMERS} Customers, {NUM_PRODUCTS} Products, {NUM_PURCHASES} Purchases")
    
    customers = generate_customers(NUM_CUSTOMERS)
    products = generate_products(PRODUCT_CATALOG)
    purchases, purchase_items = generate_purchases_and_items(customers, products, NUM_PURCHASES)
    customer_features = generate_customer_features(customers, purchases, purchase_items)
    
    valid = validate_dataset(customers, products, purchases, purchase_items, customer_features)
    
    if valid:
        save_datasets(OUTPUT_DIR, customers, products, purchases, purchase_items, customer_features)
        generate_summary(OUTPUT_DIR, customers, products, purchases, purchase_items, customer_features)
        print(f"\nAll files generated successfully in '{OUTPUT_DIR}'!")
    else:
        print("\nDataset generation aborted due to validation failure.")

if __name__ == "__main__":
    main()
