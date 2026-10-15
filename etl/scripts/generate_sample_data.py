"""
Generates the sample CSV files used by the ETL pipeline.

    python etl/scripts/generate_sample_data.py

Creates three batches:
  etl/data/raw/          initial full extract (with deliberately injected bad rows)
  etl/data/incremental/  a "next day" delta: new records + changes to existing ones
  etl/data/bad_batch/    a broken customers file (missing a column) -> job FAILS

The data is random but reproducible (fixed seed), so everyone gets the same files.
Each injected problem is listed in the DIRTY_* comments so you know what the
ETL validation is expected to catch.
"""

import csv
import random
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXTRACT_DATE = date(2026, 9, 30)          # "today" for the initial extract

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan",
    "Aanya", "Diya", "Saanvi", "Ananya", "Pari", "Myra", "Aadhya", "Kiara", "Riya", "Ira",
    "Rahul", "Amit", "Pooja", "Sneha", "Kunal", "Nikhil", "Divya", "Swati", "Manish", "Tanvi",
    "Farhan", "Zoya", "Imran", "Ayesha", "Harpreet", "Gurpreet", "Joseph", "Maria", "David", "Sarah",
    "Lakshmi", "Venkat", "Karthik", "Deepa", "Siddharth", "Neha", "Varun", "Shreya", "Omar", "Elena",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Patel", "Shah", "Mehta", "Iyer", "Nair", "Reddy",
    "Rao", "Kumar", "Das", "Bose", "Chatterjee", "Mukherjee", "Joshi", "Kulkarni", "Deshpande", "Pillai",
    "Menon", "Khan", "Sheikh", "Fernandes", "D'Souza", "Gill", "Sandhu", "Agarwal", "Bansal", "Malhotra",
    "Kapoor", "Chopra", "Thomas", "George", "Wilson", "Brown", "Tan", "Lim", "Hassan", "Ali",
]
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "proton.me"]
CITIES = [  # (city, state, country, weight)
    ("Mumbai", "Maharashtra", "India", 14), ("Pune", "Maharashtra", "India", 9),
    ("Bengaluru", "Karnataka", "India", 14), ("Hyderabad", "Telangana", "India", 9),
    ("Chennai", "Tamil Nadu", "India", 8), ("New Delhi", "Delhi", "India", 10),
    ("Gurugram", "Haryana", "India", 6), ("Noida", "Uttar Pradesh", "India", 5),
    ("Kolkata", "West Bengal", "India", 6), ("Ahmedabad", "Gujarat", "India", 5),
    ("Jaipur", "Rajasthan", "India", 3), ("Kochi", "Kerala", "India", 3),
    ("Indore", "Madhya Pradesh", "India", 2), ("Chandigarh", "Chandigarh", "India", 2),
    ("Dubai", "Dubai", "United Arab Emirates", 2), ("Singapore", "", "Singapore", 1),
    ("London", "England", "United Kingdom", 1),
]
SEGMENTS = [("Retail", 60), ("SMB", 25), ("Corporate", 15)]

PRODUCTS = [  # (sku, name, category, price)
    ("SKU-LAP-001", "ProBook 14 Laptop i5 16GB", "Laptops", 62990),
    ("SKU-LAP-002", "ProBook 15 Laptop i7 16GB", "Laptops", 78990),
    ("SKU-LAP-003", "UltraSlim 13 Laptop i7 32GB", "Laptops", 104990),
    ("SKU-LAP-004", "WorkStation 16 Laptop Ryzen 9", "Laptops", 149990),
    ("SKU-LAP-005", "Student 14 Laptop i3 8GB", "Laptops", 38990),
    ("SKU-LAP-006", "Chromebook 11", "Laptops", 24990),
    ("SKU-LAP-007", "Convertible 2-in-1 Laptop 14", "Laptops", 71990),
    ("SKU-MON-001", "24 inch FHD IPS Monitor", "Monitors", 10990),
    ("SKU-MON-002", "27 inch QHD IPS Monitor", "Monitors", 21990),
    ("SKU-MON-003", "27 inch 4K USB-C Monitor", "Monitors", 34990),
    ("SKU-MON-004", "34 inch Ultrawide Monitor", "Monitors", 45990),
    ("SKU-MON-005", "22 inch Office Monitor", "Monitors", 7490),
    ("SKU-MON-006", "Portable 15.6 inch Monitor", "Monitors", 13990),
    ("SKU-ACC-001", "Wireless Keyboard and Mouse Combo", "Accessories", 2490),
    ("SKU-ACC-002", "Mechanical Keyboard", "Accessories", 5990),
    ("SKU-ACC-003", "Ergonomic Wireless Mouse", "Accessories", 1990),
    ("SKU-ACC-004", "USB-C Docking Station", "Accessories", 12990),
    ("SKU-ACC-005", "Noise Cancelling Headset", "Accessories", 8990),
    ("SKU-ACC-006", "HD Webcam 1080p", "Accessories", 3490),
    ("SKU-ACC-007", "Laptop Backpack", "Accessories", 2290),
    ("SKU-ACC-008", "Laptop Stand Aluminium", "Accessories", 1790),
    ("SKU-ACC-009", "USB-C 65W Charger", "Accessories", 2790),
    ("SKU-ACC-010", "HDMI Cable 2m", "Accessories", 590),
    ("SKU-NET-001", "Dual Band WiFi 6 Router", "Networking", 7990),
    ("SKU-NET-002", "24 Port Gigabit Switch", "Networking", 18990),
    ("SKU-NET-003", "Mesh WiFi System 3-Pack", "Networking", 21990),
    ("SKU-NET-004", "Cat6 Ethernet Cable 10m", "Networking", 690),
    ("SKU-NET-005", "Business Firewall Appliance", "Networking", 54990),
    ("SKU-NET-006", "PoE Access Point", "Networking", 11990),
    ("SKU-STO-001", "1TB NVMe SSD", "Storage", 6990),
    ("SKU-STO-002", "2TB Portable SSD", "Storage", 13990),
    ("SKU-STO-003", "4TB External Hard Drive", "Storage", 9490),
    ("SKU-STO-004", "4-Bay NAS Enclosure", "Storage", 42990),
    ("SKU-STO-005", "128GB USB Flash Drive", "Storage", 990),
    ("SKU-PRN-001", "Mono Laser Printer", "Printers", 12990),
    ("SKU-PRN-002", "Colour Laser Multifunction Printer", "Printers", 32990),
    ("SKU-PRN-003", "Ink Tank Printer", "Printers", 14490),
    ("SKU-PRN-004", "Document Scanner", "Printers", 24990),
    ("SKU-PRN-005", "Toner Cartridge Black", "Printers", 3990),
    ("SKU-FUR-001", "Ergonomic Office Chair", "Office Furniture", 15990),
    ("SKU-FUR-002", "Height Adjustable Desk", "Office Furniture", 32990),
    ("SKU-FUR-003", "Executive Desk", "Office Furniture", 27990),
    ("SKU-FUR-004", "Meeting Table 6-Seater", "Office Furniture", 39990),
    ("SKU-FUR-005", "Filing Cabinet 3-Drawer", "Office Furniture", 11490),
    ("SKU-FUR-006", "Monitor Arm Dual", "Office Furniture", 5490),
    ("SKU-SFT-001", "Office Suite Annual Licence", "Software", 6490),
    ("SKU-SFT-002", "Antivirus Business 1yr (per seat)", "Software", 1490),
    ("SKU-SFT-003", "Accounting Software Licence", "Software", 18990),
    ("SKU-SFT-004", "Design Suite Annual Licence", "Software", 29990),
    ("SKU-SFT-005", "Backup Cloud Storage 1TB 1yr", "Software", 4990),
    ("SKU-SFT-006", "Project Management Tool 1yr (per seat)", "Software", 3490),
    ("SKU-MOB-001", "Business Smartphone 128GB", "Mobiles & Tablets", 32990),
    ("SKU-MOB-002", "Tablet 11 inch 128GB", "Mobiles & Tablets", 41990),
    ("SKU-MOB-003", "Rugged Smartphone", "Mobiles & Tablets", 27990),
    ("SKU-MOB-004", "Tablet 10 inch 64GB", "Mobiles & Tablets", 19990),
    ("SKU-MOB-005", "Stylus Pen", "Mobiles & Tablets", 4990),
    ("SKU-ACC-011", "Wireless Presenter", "Accessories", 1490),
    ("SKU-ACC-012", "Surge Protector 6-Socket", "Accessories", 1290),
    ("SKU-NET-007", "UPS 1kVA", "Networking", 8490),
    ("SKU-STO-006", "Server Rack 12U", "Storage", 23990),
]
SALES_REPS = ["EMP-1006", "EMP-1007", "EMP-1008", "EMP-1009", "EMP-1010", "EMP-1011", "EMP-1012"]
TWO_DP = Decimal("0.01")


def money(value) -> Decimal:
    """Round like MySQL's ROUND(x, 2) on DECIMAL values (half away from zero)."""
    return Decimal(value).quantize(TWO_DP, rounding=ROUND_HALF_UP)


def weighted(options):
    values, weights = zip(*[(o[:-1] if len(o) > 2 else o[0], o[-1]) for o in options])
    return random.choices(values, weights=weights, k=1)[0]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_time(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, random.randint(8, 21), random.randint(0, 59), random.randint(0, 59))


def phone_number() -> str:
    digits = f"9{random.randint(100000000, 999999999)}"
    style = random.random()
    if style < 0.5:
        return f"+91{digits}"
    if style < 0.75:
        return f"+91-{digits[:5]}-{digits[5:]}"     # messy format -> cleaned by ETL
    return f"{digits[:5]} {digits[5:]}"


def write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  {path.relative_to(DATA_DIR.parent)}: {len(rows)} rows")


# ---------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------
def make_customers(count=200, start_code=1001):
    customers, used_emails = [], set()
    for i in range(count):
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        base = f"{first}.{last}".lower().replace("'", "")
        email = f"{base}@{random.choice(EMAIL_DOMAINS)}"
        n = 2
        while email in used_emails:
            email = f"{base}{n}@{random.choice(EMAIL_DOMAINS)}"
            n += 1
        used_emails.add(email)
        city, state, country = weighted(CITIES)
        customers.append({
            "customer_code": f"CUST-{start_code + i}",
            "first_name": first, "last_name": last, "email": email,
            "phone": phone_number(), "city": city, "state": state, "country": country,
            "segment": weighted(SEGMENTS),
            "signup_date": random_date(date(2024, 1, 1), date(2026, 6, 30)),
        })
    return customers


def customer_row(c, messy=False):
    first, last, email, segment = c["first_name"], c["last_name"], c["email"], c["segment"]
    if messy:  # formatting problems the ETL should FIX (not reject)
        first, email, segment = f"  {first.lower()} ", f" {email.upper()}", segment.lower()
    return [c["customer_code"], first, last, email, c["phone"], c["city"], c["state"],
            c["country"], segment, c["signup_date"].isoformat()]


# ---------------------------------------------------------------------
# Orders, order items, payments
# ---------------------------------------------------------------------
def month_weight(d: date) -> float:
    growth = 1 + (d.year - 2025) * 0.35 + d.month * 0.02
    seasonal = {3: 1.3, 10: 1.4, 11: 1.5, 12: 1.2}.get(d.month, 1.0)  # fiscal year end, festive season
    return growth * seasonal


def pick_status(order_day: date, today: date) -> str:
    age = (today - order_day).days
    if age > 30:
        return random.choices(["DELIVERED", "CANCELLED"], [94, 6])[0]
    if age > 10:
        return random.choices(["DELIVERED", "SHIPPED", "PROCESSING", "CANCELLED"], [60, 25, 10, 5])[0]
    return random.choices(["PENDING", "PROCESSING", "SHIPPED", "CANCELLED"], [35, 40, 20, 5])[0]


def make_items(order, product_prices):
    segment = order["segment"]
    n_lines = random.choices([1, 2, 3, 4], [45, 30, 17, 8])[0]
    skus = random.sample(list(product_prices), n_lines)
    items = []
    for sku in skus:
        if segment == "Corporate":
            qty = random.randint(2, 25)
            discount = Decimal(random.choice([5, 7.5, 10, 12.5, 15]))
        elif segment == "SMB":
            qty = random.randint(1, 8)
            discount = Decimal(random.choice([0, 0, 5, 7.5]))
        else:
            qty = random.choices([1, 2, 3], [75, 20, 5])[0]
            discount = Decimal(10 if order["date"].month in (10, 11) and random.random() < 0.4 else 0)
        price = Decimal(product_prices[sku])
        if order["date"].year == 2025:                 # prices were ~5% lower last year
            price = (price * Decimal("0.95")).quantize(Decimal("1"))
        items.append({"order_number": order["order_number"], "sku": sku, "quantity": qty,
                      "unit_price": money(price), "discount_pct": money(discount)})
    return items


def order_total(items):
    return sum(money(i["quantity"] * i["unit_price"] * (1 - i["discount_pct"] / 100)) for i in items)


class RefGen:
    def __init__(self):
        self.used = set()

    def __call__(self):
        while True:
            ref = f"TXN{random.randint(10**9, 10**10 - 1)}"
            if ref not in self.used:
                self.used.add(ref)
                return ref


def payment_method(segment):
    if segment == "Retail":
        return random.choices(["UPI", "CARD", "WALLET", "NET_BANKING"], [45, 35, 10, 10])[0]
    return random.choices(["BANK_TRANSFER", "NET_BANKING", "CARD"], [60, 20, 20])[0]


def make_payments(order, total, new_ref, today):
    """Return payment dicts that match a realistic payment history for the order."""
    status, segment, odt = order["status"], order["segment"], order["datetime"]
    method = payment_method(segment)

    def pay_time(min_days, max_days):
        when = odt + timedelta(days=random.randint(min_days, max_days), hours=random.randint(0, 6))
        latest = datetime(today.year, today.month, today.day, 23, 0, 0)
        return min(when, latest)

    def p(amount, when, st, m=method):
        return {"payment_reference": new_ref(), "order_number": order["order_number"],
                "payment_date": when, "amount": money(amount), "payment_method": m, "status": st}

    lag = (3, 25) if method == "BANK_TRANSFER" else (0, 1)

    if status == "CANCELLED":
        return [p(total, pay_time(0, 1), "REFUNDED")] if random.random() < 0.5 else []
    if status == "PENDING":
        return [p(total, pay_time(0, 0), "PENDING")] if random.random() < 0.5 else []
    if status in ("PROCESSING", "SHIPPED"):
        return [p(total, pay_time(*lag), "COMPLETED")] if random.random() < 0.8 else []

    # DELIVERED
    r = random.random()
    if r < 0.015:
        return []                                                  # unpaid -> caught by DQ check
    if r < 0.09:                                                   # failed attempt, then success
        first = p(total, pay_time(0, 0), "FAILED")
        return [first, p(total, first["payment_date"] + timedelta(minutes=random.randint(5, 90)), "COMPLETED")]
    if r < 0.14 and segment != "Retail":                           # two instalments
        part = money(total * Decimal("0.4"))
        return [p(part, pay_time(0, 3), "COMPLETED"), p(total - part, pay_time(15, 30), "COMPLETED")]
    return [p(total, pay_time(*lag), "COMPLETED")]


def make_orders(customers, start_day, end_day, count, start_number, today, product_prices, new_ref):
    days = [start_day + timedelta(days=d) for d in range((end_day - start_day).days + 1)]
    order_days = sorted(random.choices(days, weights=[month_weight(d) for d in days], k=count))
    activity = {c["customer_code"]: min(random.lognormvariate(0, 0.8), 3.0) for c in customers}  # some customers buy more

    orders, items, payments = [], [], []
    for n, day in enumerate(order_days):
        eligible = [c for c in customers if c["signup_date"] <= day]
        cust = random.choices(eligible, weights=[activity[c["customer_code"]] for c in eligible])[0]
        if cust["segment"] == "Retail":
            rep = random.choice(SALES_REPS) if random.random() < 0.15 else ""
        else:
            rep = random.choice(SALES_REPS) if random.random() < 0.9 else ""
        order = {"order_number": f"ORD-{start_number + n}", "customer_code": cust["customer_code"],
                 "employee_code": rep, "date": day, "datetime": random_time(day),
                 "status": pick_status(day, today), "segment": cust["segment"]}
        order_items = make_items(order, product_prices)
        orders.append(order)
        items.extend(order_items)
        payments.extend(make_payments(order, order_total(order_items), new_ref, today))
    return orders, items, payments


def order_row(o, messy=False):
    status = o["status"].lower() if messy else o["status"]
    return [o["order_number"], o["customer_code"], o["employee_code"],
            o["datetime"].strftime("%Y-%m-%d %H:%M:%S"), status]


def item_row(i):
    return [i["order_number"], i["sku"], i["quantity"], f"{i['unit_price']:.2f}", f"{i['discount_pct']:.2f}"]


def payment_row(p):
    return [p["payment_reference"], p["order_number"], p["payment_date"].strftime("%Y-%m-%d %H:%M:%S"),
            f"{p['amount']:.2f}", p["payment_method"], p["status"]]


CUSTOMER_HEADER = ["customer_code", "first_name", "last_name", "email", "phone", "city", "state",
                   "country", "segment", "signup_date"]
PRODUCT_HEADER = ["sku", "product_name", "category", "unit_price", "stock_quantity"]
ORDER_HEADER = ["order_number", "customer_code", "employee_code", "order_date", "status"]
ITEM_HEADER = ["order_number", "sku", "quantity", "unit_price", "discount_pct"]
PAYMENT_HEADER = ["payment_reference", "order_number", "payment_date", "amount", "payment_method", "status"]


def insert_randomly(rows, extra):
    for row in extra:
        rows.insert(random.randint(1, len(rows)), row)


def main():
    product_prices = {sku: price for sku, _, _, price in PRODUCTS}
    new_ref = RefGen()

    # ================================================================ RAW
    print("Initial extract -> data/raw")
    customers = make_customers()
    # A "soft" duplicate: same person and city, different email. It passes every
    # row rule, so it is loaded - queries.sql Q27 shows how to spot it.
    twin = customers[20]
    customers[150].update(first_name=twin["first_name"], last_name=twin["last_name"], city=twin["city"],
                          state=twin["state"], country=twin["country"],
                          email=f"{twin['first_name']}{twin['last_name']}@outlook.com".lower().replace("'", ""))
    customer_rows = [customer_row(c, messy=random.random() < 0.08) for c in customers]
    # DIRTY_CUSTOMERS (expected rejects):
    dirty = [
        customer_row(customers[10]), customer_row(customers[57]), customer_row(customers[120]),  # exact duplicates
        ["CUST-1903", "Amit", "Gupta", "", "+919800011122", "New Delhi", "Delhi", "India", "Retail", "2025-04-02"],                        # missing email
        ["CUST-1904", "Sara", "Ali", "", "", "Hyderabad", "Telangana", "India", "Retail", "2025-05-15"],                                     # missing email
        ["CUST-1905", "Kabir", "Singh", "", "+919800011124", "Chennai", "Tamil Nadu", "India", "SMB", "2025-06-01"],                         # missing email
        ["CUST-1906", "Meena", "Rao", "", "+919800011125", "Kochi", "Kerala", "India", "Retail", "2025-06-20"],                             # missing email
        ["CUST-1907", "Vijay", "Kumar", "vijay.kumar@", "+919800011126", "Jaipur", "Rajasthan", "India", "Retail", "2025-01-09"],           # invalid email
        ["CUST-1908", "Asha", "Nair", "asha.nair.gmail.com", "+919800011127", "Kochi", "Kerala", "India", "Retail", "2025-02-14"],         # invalid email
        ["CUST-1909", "Tarun", "Bansal", "tarun bansal@yahoo.com", "+919800011128", "Noida", "Uttar Pradesh", "India", "SMB", "2025-03-03"], # invalid email
        ["CUST-1910", "Leela", "Das", "leela@@outlook.com", "+919800011129", "Kolkata", "West Bengal", "India", "Retail", "2025-03-28"],    # invalid email
        ["CUST-1911", "Mohan", "Joshi", "mohan.joshi@gmail.com", "+919800011130", "Pune", "Maharashtra", "India", "Retail", "2025-02-30"],  # invalid date
        ["CUST-1912", "Nisha", "Kapoor", "nisha.kapoor@gmail.com", "+919800011131", "Mumbai", "Maharashtra", "India", "SMB", "15/07/2025"], # wrong date format
        ["CUST-1913", "", "Thomas", "a.thomas@gmail.com", "+919800011132", "Bengaluru", "Karnataka", "India", "Retail", "2025-04-18"],      # missing first name
        ["CUST-1914", "", "", "unknown.user@gmail.com", "", "Bengaluru", "Karnataka", "India", "Retail", "2025-04-19"],                     # missing names
        ["CUST-1915", "Ravi", "Teja", "ravi.teja@gmail.com", "+919800011134", "Hyderabad", "Telangana", "India", "Enterprise", "2025-05-05"], # invalid segment
        ["CUST-1916", "Gita", "Menon", "gita.menon@gmail.com", "+919800011135", "Chennai", "Tamil Nadu", "India", "Retail", "2027-03-01"],  # future date
    ]
    insert_randomly(customer_rows, dirty)
    # Appended at the END so the genuine customer (earlier in the file) is the one kept.
    customer_rows += [
        ["CUST-1901", "Rahul", "Sharma", customers[3]["email"], "+919812345678", "Mumbai", "Maharashtra", "India", "Retail", "2025-02-11"],   # email already used
        ["CUST-1902", "Priya", "Mehta", customers[44]["email"], "+919812345679", "Pune", "Maharashtra", "India", "SMB", "2025-03-19"],       # email already used
    ]
    write_csv(DATA_DIR / "raw" / "customers.csv", CUSTOMER_HEADER, customer_rows)

    product_rows = [[sku, name, cat, f"{price:.2f}", random.randint(0, 400)] for sku, name, cat, price in PRODUCTS]
    # DIRTY_PRODUCTS:
    product_rows.append(["SKU-ACC-001", "Wireless Keyboard and Mouse Combo v2", "Accessories", "2590.00", 50])  # duplicate SKU
    insert_randomly(product_rows, [
        ["SKU-BAD-001", "Clearance Speaker", "Accessories", "-499.00", 10],                     # negative price
        ["SKU-BAD-002", "Refurbished Tablet", "Mobiles & Tablets", "-12000.00", 4],             # negative price
        ["SKU-BAD-003", "", "Accessories", "799.00", 25],                                        # missing name
        ["SKU-BAD-004", "Smart Pen", "Accessories", "N/A", 25],                                  # not a number
        ["SKU-BAD-005", "Wireless Charger", "Accessories", "1499.00", -5],                       # negative stock
    ])
    write_csv(DATA_DIR / "raw" / "products.csv", PRODUCT_HEADER, product_rows)

    orders, items, payments = make_orders(customers, date(2025, 1, 1), EXTRACT_DATE, 1500, 100001,
                                          EXTRACT_DATE, product_prices, new_ref)
    by_number = {o["order_number"]: o for o in orders}

    # Orders whose customer does not exist in the CRM file -> INVALID_REFERENCE.
    # Their items and payments will then ALSO fail (cascade of bad references).
    for o in random.sample(orders, 5):
        o["customer_code"] = f"CUST-{random.randint(8000, 8999)}"
    # Two orders dated BEFORE the customer signed up -> found by sp_run_data_quality_checks
    cust_by_code = {c["customer_code"]: c for c in customers}
    for o in random.sample([o for o in orders if o["customer_code"] in cust_by_code
                            and o["status"] == "DELIVERED"
                            and cust_by_code[o["customer_code"]]["signup_date"] > date(2025, 2, 1)], 2):
        signup = cust_by_code[o["customer_code"]]["signup_date"]
        o["datetime"] = random_time(signup - timedelta(days=random.randint(3, 20)))

    order_rows = [order_row(o, messy=random.random() < 0.03) for o in orders]
    # DIRTY_ORDERS:
    insert_randomly(order_rows, [
        order_row(orders[100]), order_row(orders[700]), order_row(orders[1200]),          # exact duplicates
        ["ORD-190001", "CUST-1050", "", "2025-02-30 10:15:00", "DELIVERED"],              # invalid date
        ["ORD-190002", "CUST-1051", "", "yesterday", "DELIVERED"],                         # invalid date
        ["ORD-190003", "CUST-1052", "EMP-1007", "", "PROCESSING"],                         # missing date
        ["ORD-190004", "CUST-1053", "", "2026-03-11 12:00:00", "RETURNED"],                # invalid status
        ["ORD-190005", "CUST-1054", "", "2026-04-02 16:20:00", "ON_HOLD"],                 # invalid status
        ["ORD-190006", "", "", "2026-05-09 09:45:00", "DELIVERED"],                        # missing customer
    ])
    write_csv(DATA_DIR / "raw" / "orders.csv", ORDER_HEADER, order_rows)

    # Two orders whose ONLY line has an unknown SKU -> the order loads but has no items
    single_line = [o["order_number"] for o in orders
                   if sum(1 for i in items if i["order_number"] == o["order_number"]) == 1
                   and o["status"] == "DELIVERED"]
    for number in random.sample(single_line, 2):
        for i in items:
            if i["order_number"] == number:
                i["sku"] = "SKU-OLD-999"
    item_rows = [item_row(i) for i in items]
    # DIRTY_ORDER_ITEMS:
    insert_randomly(item_rows, [
        item_row(items[50]), item_row(items[1500]),                       # duplicate (order, sku) lines
        ["ORD-100020", "SKU-ACC-010", "0", "590.00", "0.00"],             # zero quantity
        ["ORD-100021", "SKU-ACC-003", "-2", "1990.00", "0.00"],           # negative quantity
        ["ORD-100022", "SKU-STO-005", "-1", "990.00", "0.00"],            # negative quantity
        ["ORD-100023", "SKU-XYZ-123", "1", "4999.00", "0.00"],            # unknown product
        ["ORD-100024", "SKU-ACC-006", "1", "", "0.00"],                   # missing unit price
        ["ORD-100025", "SKU-ACC-008", "2", "1790.00", "120.00"],          # discount > 100%
        ["ORD-199999", "SKU-ACC-002", "1", "5990.00", "0.00"],            # unknown order
    ])
    write_csv(DATA_DIR / "raw" / "order_items.csv", ITEM_HEADER, item_rows)

    # Gateway glitches: two orders charged twice (two COMPLETED payments) -> overpaid
    completed = [p for p in payments if p["status"] == "COMPLETED"]
    for p in random.sample(completed, 2):
        payments.append({**p, "payment_reference": new_ref(),
                         "payment_date": p["payment_date"] + timedelta(seconds=40)})
    # Two payments dated before their order (timezone bug in the source system)
    for p in random.sample(completed, 2):
        p["payment_date"] = by_number[p["order_number"]]["datetime"] - timedelta(hours=random.randint(2, 9))
    payment_rows = [payment_row(p) for p in payments]
    # DIRTY_PAYMENTS:
    insert_randomly(payment_rows, [
        payment_row(payments[30]), payment_row(payments[400]), payment_row(payments[900]),   # duplicate transactions
        [new_ref(), "ORD-100030", "2025-01-20 11:00:00", "-1500.00", "UPI", "COMPLETED"],    # negative amount
        [new_ref(), "ORD-100031", "2025-01-21 11:00:00", "-250.00", "CARD", "COMPLETED"],    # negative amount
        [new_ref(), "ORD-100032", "2025-01-22 11:00:00", "0.00", "CARD", "COMPLETED"],       # zero amount
        [new_ref(), "ORD-188888", "2025-03-01 10:00:00", "4999.00", "UPI", "COMPLETED"],     # unknown order
        [new_ref(), "ORD-188889", "2025-03-02 10:00:00", "2599.00", "CARD", "COMPLETED"],    # unknown order
        [new_ref(), "ORD-100040", "2025-02-30 09:00:00", "2490.00", "UPI", "COMPLETED"],     # invalid date
        [new_ref(), "ORD-100041", "", "1990.00", "UPI", "COMPLETED"],                        # missing date
        [new_ref(), "ORD-100042", "2025-01-25 13:00:00", "3490.00", "CHEQUE", "COMPLETED"],  # invalid method
    ])
    write_csv(DATA_DIR / "raw" / "payments.csv", PAYMENT_HEADER, payment_rows)

    # ======================================================== INCREMENTAL
    print("Next-day delta -> data/incremental")
    day2 = date(2026, 10, 10)
    changed = random.sample(customers, 5)
    for c in changed:                        # customers who moved city / changed phone
        city, state, country = weighted(CITIES)
        c.update(city=city, state=state, country=country, phone=phone_number())
    new_customers = make_customers(4, start_code=1201)
    for c in new_customers:
        c["signup_date"] = random_date(date(2026, 9, 25), date(2026, 10, 5))
    write_csv(DATA_DIR / "incremental" / "customers.csv", CUSTOMER_HEADER,
              [customer_row(c) for c in changed + new_customers])

    repriced = {"SKU-LAP-001": 59990, "SKU-MON-002": 19990, "SKU-ACC-005": 9490,
                "SKU-NET-003": 23990, "SKU-SFT-004": 27990}
    product_prices.update(repriced)
    new_products = [("SKU-LAP-008", "AI PC 14 Laptop Core Ultra 7", "Laptops", 119990),
                    ("SKU-ACC-013", "Bluetooth Conference Speaker", "Accessories", 7990)]
    for sku, _, _, price in new_products:
        product_prices[sku] = price
    write_csv(DATA_DIR / "incremental" / "products.csv", PRODUCT_HEADER,
              [[sku, name, cat, f"{product_prices[sku]:.2f}", random.randint(20, 300)]
               for sku, name, cat, _ in PRODUCTS if sku in repriced]
              + [[sku, name, cat, f"{price:.2f}", random.randint(20, 100)] for sku, name, cat, price in new_products])

    # Status progress for recent orders that were still open
    open_orders = [o for o in orders if o["status"] in ("PENDING", "PROCESSING", "SHIPPED")
                   and o["customer_code"] in cust_by_code]
    progressed = random.sample(open_orders, min(12, len(open_orders)))
    next_status = {"PENDING": "PROCESSING", "PROCESSING": "SHIPPED", "SHIPPED": "DELIVERED"}
    for o in progressed:
        o["status"] = next_status[o["status"]]
    new_orders, new_items, new_payments = make_orders(customers + new_customers, date(2026, 10, 1), day2, 30,
                                                      101501, day2, product_prices, new_ref)
    write_csv(DATA_DIR / "incremental" / "orders.csv", ORDER_HEADER,
              [order_row(o) for o in progressed + new_orders])
    write_csv(DATA_DIR / "incremental" / "order_items.csv", ITEM_HEADER, [item_row(i) for i in new_items])
    write_csv(DATA_DIR / "incremental" / "payments.csv", PAYMENT_HEADER, [payment_row(p) for p in new_payments])

    # ========================================================= BAD BATCH
    print("Broken file -> data/bad_batch")
    header_without_email = [h for h in CUSTOMER_HEADER if h != "email"]
    write_csv(DATA_DIR / "bad_batch" / "customers.csv", header_without_email,
              [[v for h, v in zip(CUSTOMER_HEADER, customer_row(c)) if h != "email"] for c in customers[:5]])


if __name__ == "__main__":
    main()
