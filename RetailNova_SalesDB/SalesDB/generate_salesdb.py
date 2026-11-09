"""
RetailNova S.A. - SalesDB generator
Generates simulated data for the Power BI lab:
  - Customers : 500 rows
  - Products  : 60 rows
  - Branches  : 20 rows
  - Sales     : 10,000 rows (year 2024)
Outputs: CSV files, a SQLite database, a SQL Server script and a PostgreSQL script.

Usage:  python generate_salesdb.py [output_folder]
"""
import csv
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

random.seed(2024)  # same data every run (reproducible)
OUT = sys.argv[1] if len(sys.argv) > 1 else "SalesDB_output"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- Branches
# (city, country, region, relative weight, growth trend during the year)
BRANCH_DATA = [
    ("Bogota", "Colombia", "Andean", 1.6, 0.35),
    ("Medellin", "Colombia", "Andean", 1.3, 0.40),
    ("Cali", "Colombia", "Andean", 1.0, 0.25),
    ("Quito", "Ecuador", "Andean", 0.8, 0.20),
    ("Lima", "Peru", "Andean", 1.4, 0.45),
    ("Arequipa", "Peru", "Andean", 0.6, 0.30),
    ("Mexico City", "Mexico", "North America", 1.8, 0.30),
    ("Guadalajara", "Mexico", "North America", 1.1, 0.25),
    ("Monterrey", "Mexico", "North America", 1.0, 0.35),
    ("Panama City", "Panama", "Central America", 0.7, 0.15),
    ("San Jose", "Costa Rica", "Central America", 0.6, 0.10),
    ("Guatemala City", "Guatemala", "Central America", 0.5, -0.05),
    ("Santiago", "Chile", "Southern Cone", 1.3, 0.10),
    ("Buenos Aires", "Argentina", "Southern Cone", 1.2, -0.15),
    ("Cordoba", "Argentina", "Southern Cone", 0.6, -0.20),
    ("Montevideo", "Uruguay", "Southern Cone", 0.5, 0.00),
    ("Sao Paulo", "Brazil", "Brazil", 1.7, 0.55),
    ("Rio de Janeiro", "Brazil", "Brazil", 1.2, 0.50),
    ("Belo Horizonte", "Brazil", "Brazil", 0.7, 0.45),
    ("Curitiba", "Brazil", "Brazil", 0.6, 0.40),
]
branches = [
    {"branch_id": i + 1, "city": c, "country": co, "region": r}
    for i, (c, co, r, _, _) in enumerate(BRANCH_DATA)
]
branch_weight = [b[3] for b in BRANCH_DATA]
branch_trend = [b[4] for b in BRANCH_DATA]

# ---------------------------------------------------------------- Products
CATALOG = {
    # category: (brands, price range USD, popularity weight)
    "Smartphones": (["Samsung", "Apple", "Xiaomi", "Motorola"], (180, 1200), 1.6),
    "Laptops": (["Lenovo", "HP", "Dell", "Asus", "Apple"], (450, 1800), 0.9),
    "TVs & Audio": (["LG", "Samsung", "Sony", "JBL"], (120, 1500), 1.0),
    "Home Appliances": (["Whirlpool", "Mabe", "Electrolux", "Oster"], (40, 900), 1.1),
    "Wearables": (["Apple", "Garmin", "Huawei", "Xiaomi"], (40, 450), 0.9),
    "Accessories": (["Logitech", "Anker", "Belkin", "Generic"], (8, 120), 2.2),
    "Home Goods": (["IKEA", "Corona", "Imusa", "Tramontina"], (10, 200), 1.3),
}
products = []
pid = 1
for cat, (brands, (lo, hi), _) in CATALOG.items():
    n = 10 if cat in ("Accessories", "Smartphones") else 8
    for _ in range(n):
        products.append({
            "product_id": pid,
            "category": cat,
            "brand": random.choice(brands),
            "list_price": round(random.uniform(lo, hi), 2),
        })
        pid += 1
# 60 products in total -> trim/extend to exactly 60
products = products[:60]
cat_weight = {c: v[2] for c, v in CATALOG.items()}
# a few "star" products get extra demand (high-turnover products)
star_ids = set(random.sample([p["product_id"] for p in products], 8))
product_weight = [
    cat_weight[p["category"]] * (3.0 if p["product_id"] in star_ids else 1.0)
    for p in products
]

# ---------------------------------------------------------------- Customers
FIRST = ["Ana", "Luis", "Maria", "Carlos", "Sofia", "Juan", "Valentina", "Andres",
         "Camila", "Diego", "Laura", "Jorge", "Paula", "Felipe", "Daniela", "Mateo",
         "Isabella", "Santiago", "Gabriela", "Ricardo", "Lucia", "Fernando", "Mariana",
         "Pedro", "Natalia", "Miguel", "Carolina", "Sebastian", "Juliana", "Tomas"]
LAST = ["Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Perez", "Sanchez",
        "Ramirez", "Torres", "Flores", "Rivera", "Gomez", "Diaz", "Reyes", "Morales",
        "Ortiz", "Castro", "Vargas", "Rojas", "Herrera", "Silva", "Mendoza", "Rios"]
SEGMENTS = [("Consumer", 0.65), ("Corporate", 0.20), ("Small Business", 0.15)]
COUNTRIES = sorted({b["country"] for b in branches})
country_weight = {c: sum(b[3] for b in BRANCH_DATA if b[1] == c) for c in COUNTRIES}
customers = []
for cid in range(1, 501):
    seg = random.choices([s for s, _ in SEGMENTS], [w for _, w in SEGMENTS])[0]
    if seg == "Consumer":
        name = f"{random.choice(FIRST)} {random.choice(LAST)}"
    else:
        name = f"{random.choice(LAST)} {random.choice(['Group', 'S.A.S.', 'Ltda', 'Corp', 'Solutions', 'Trading'])}"
    customers.append({
        "customer_id": cid,
        "name": name,
        "segment": seg,
        "country": random.choices(COUNTRIES, [country_weight[c] for c in COUNTRIES])[0],
    })
# Pareto-like purchase frequency: few customers buy a lot
customer_weight = [min(random.paretovariate(1.8), 12) * (2.5 if c["segment"] == "Corporate" else 1.0)
                   for c in customers]
# each customer tends to buy in branches of their own country
branches_by_country = {}
for i, b in enumerate(branches):
    branches_by_country.setdefault(b["country"], []).append(i)

# ---------------------------------------------------------------- Seasonality
MONTH_FACTOR = {1: 0.80, 2: 0.75, 3: 0.85, 4: 0.85, 5: 1.00, 6: 0.95,
                7: 1.00, 8: 0.95, 9: 0.90, 10: 1.00, 11: 1.45, 12: 1.70}
start = date(2024, 1, 1)
days = [start + timedelta(d) for d in range(366)]  # 2024 is a leap year
day_weight = []
for d in days:
    w = MONTH_FACTOR[d.month]
    if d.weekday() >= 5:            # weekends sell more
        w *= 1.35
    if d.month == 11 and 25 <= d.day <= 30:   # Black Friday week
        w *= 1.8
    day_weight.append(w)

# ---------------------------------------------------------------- Sales
N_SALES = 10_000
sales = []
for sid in range(1, N_SALES + 1):
    d = random.choices(days, day_weight)[0]
    progress = (d - start).days / 365
    c_idx = random.choices(range(len(customers)), customer_weight)[0]
    cust = customers[c_idx]
    # 80 % of purchases in own country, 20 % anywhere (weighted by branch size + trend)
    bw = [branch_weight[i] * (1 + branch_trend[i] * progress) for i in range(len(branches))]
    if random.random() < 0.8:
        pool = branches_by_country[cust["country"]]
        b_idx = random.choices(pool, [bw[i] for i in pool])[0]
    else:
        b_idx = random.choices(range(len(branches)), bw)[0]
    p = random.choices(products, product_weight)[0]
    if p["category"] in ("Accessories", "Home Goods"):
        qty = random.choices([1, 2, 3, 4, 5], [40, 25, 15, 10, 10])[0]
    else:
        qty = random.choices([1, 2, 3], [80, 15, 5])[0]
    if cust["segment"] == "Corporate":
        qty += random.choice([0, 1, 2, 4])
    discount = 0.85 if (d.month == 11 and 25 <= d.day <= 30) else 1.0
    unit_price = round(p["list_price"] * random.uniform(0.95, 1.05) * discount, 2)
    sales.append({
        "sale_id": sid,
        "date": d.isoformat(),
        "customer_id": cust["customer_id"],
        "product_id": p["product_id"],
        "quantity": qty,
        "unit_price": unit_price,
        "branch_id": branches[b_idx]["branch_id"],
    })
sales.sort(key=lambda r: (r["date"], r["sale_id"]))
for i, r in enumerate(sales, 1):  # renumber in date order
    r["sale_id"] = i

# ---------------------------------------------------------------- Export
TABLES = {
    "Branches": (branches, ["branch_id", "city", "country", "region"]),
    "Products": ([{k: p[k] for k in ("product_id", "category", "brand")} for p in products],
                 ["product_id", "category", "brand"]),
    "Customers": (customers, ["customer_id", "name", "segment", "country"]),
    "Sales": (sales, ["sale_id", "date", "customer_id", "product_id", "quantity",
                      "unit_price", "branch_id"]),
}

for name, (rows, cols) in TABLES.items():
    with open(os.path.join(OUT, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

DDL = {
    "Branches": "branch_id INT PRIMARY KEY, city VARCHAR(50) NOT NULL, country VARCHAR(50) NOT NULL, region VARCHAR(50) NOT NULL",
    "Products": "product_id INT PRIMARY KEY, category VARCHAR(50) NOT NULL, brand VARCHAR(50) NOT NULL",
    "Customers": "customer_id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, segment VARCHAR(30) NOT NULL, country VARCHAR(50) NOT NULL",
    "Sales": ("sale_id INT PRIMARY KEY, date DATE NOT NULL, customer_id INT NOT NULL REFERENCES Customers(customer_id), "
              "product_id INT NOT NULL REFERENCES Products(product_id), quantity INT NOT NULL CHECK (quantity > 0), "
              "unit_price DECIMAL(10,2) NOT NULL, branch_id INT NOT NULL REFERENCES Branches(branch_id)"),
}


def sql_val(v):
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def inserts(name, rows, cols, batch=1000):
    out = []
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        vals = ",\n".join("(" + ", ".join(sql_val(r[c]) for c in cols) + ")" for r in chunk)
        out.append(f"INSERT INTO {name} ({', '.join(cols)}) VALUES\n{vals};\n")
    return out


# SQLite
db_path = os.path.join(OUT, "SalesDB.sqlite")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
con.execute("PRAGMA foreign_keys = ON")
for name, (rows, cols) in TABLES.items():
    con.execute(f"CREATE TABLE {name} ({DDL[name]})")
    for stmt in inserts(name, rows, cols, batch=500):
        con.execute(stmt)
con.commit()
con.close()

# SQL Server (T-SQL) - max 1000 rows per INSERT ... VALUES
with open(os.path.join(OUT, "SalesDB_SQLServer.sql"), "w", encoding="utf-8") as f:
    f.write("-- RetailNova S.A. - SalesDB (SQL Server)\n"
            "IF DB_ID('SalesDB') IS NULL CREATE DATABASE SalesDB;\nGO\nUSE SalesDB;\nGO\n"
            "IF OBJECT_ID('Sales') IS NOT NULL DROP TABLE Sales;\n"
            "IF OBJECT_ID('Customers') IS NOT NULL DROP TABLE Customers;\n"
            "IF OBJECT_ID('Products') IS NOT NULL DROP TABLE Products;\n"
            "IF OBJECT_ID('Branches') IS NOT NULL DROP TABLE Branches;\nGO\n")
    for name in ("Branches", "Products", "Customers", "Sales"):
        f.write(f"CREATE TABLE {name} ({DDL[name]});\nGO\n")
    f.write("SET NOCOUNT ON;\n")
    for name, (rows, cols) in TABLES.items():
        for stmt in inserts(name, rows, cols, batch=1000):
            f.write(stmt + "GO\n")
    f.write("SELECT COUNT(*) AS total_sales FROM Sales;  -- expected: 10000\nGO\n")

# PostgreSQL
with open(os.path.join(OUT, "SalesDB_PostgreSQL.sql"), "w", encoding="utf-8") as f:
    f.write("-- RetailNova S.A. - SalesDB (PostgreSQL)\n"
            "-- 1) Create the database first:  CREATE DATABASE salesdb;   2) connect to it and run this file\n"
            "DROP TABLE IF EXISTS Sales, Customers, Products, Branches;\n")
    for name in ("Branches", "Products", "Customers", "Sales"):
        f.write(f"CREATE TABLE {name} ({DDL[name]});\n")
    for name, (rows, cols) in TABLES.items():
        for stmt in inserts(name, rows, cols, batch=1000):
            f.write(stmt)
    f.write("SELECT COUNT(*) AS total_sales FROM Sales;  -- expected: 10000\n")

print("Done ->", OUT)
for name, (rows, _) in TABLES.items():
    print(f"  {name:<10} {len(rows):>6} rows")
