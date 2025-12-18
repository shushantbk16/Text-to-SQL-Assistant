import sqlite3
import random
from datetime import datetime, timedelta
import os

# Database file
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "ecommerce.db")

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables(conn):
    """Create tables in the database."""
    cursor = conn.cursor()

    # Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        join_date TEXT,
        region TEXT
    );
    """)

    # Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL,
        inventory_count INTEGER
    );
    """)

    # Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_date TEXT,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    );
    """)

    # Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    );
    """)
    
    conn.commit()
    print("Tables created successfully.")

def seed_data(conn):
    """Seed the database with realistic data."""
    cursor = conn.cursor()
    
    # Seed Customers
    print("Seeding customers...")
    regions = ['North', 'South', 'East', 'West', None, 'n/a', 'Northeast']
    names = ['Alice Smith', 'Bob Jones', 'Charlie Brown', 'David Wilson', 'Eva Green', 'Frank White', 'Grace Hall']
    
    customers_data = []
    for i in range(20):
        name = random.choice(names) + f" {i}"
        join_date = (datetime.now() - timedelta(days=random.randint(0, 365*2))).strftime('%Y-%m-%d')
        region = random.choice(regions)
        customers_data.append((name, join_date, region))
        
    cursor.executemany("INSERT INTO customers (name, join_date, region) VALUES (?, ?, ?)", customers_data)

    # Seed Products
    print("Seeding products...")
    categories = ['Electronics', 'electronics', 'Clothing', 'Home', 'Books', 'Toys', 'ELECTRONICS']
    product_names = {
        'Electronics': ['Smartphone', 'Laptop', 'Headphones', 'Monitor', 'Keyboard'],
        'Clothing': ['T-Shirt', 'Jeans', 'Jacket', 'Sneakers', 'Hat'],
        'Home': ['Blender', 'Toaster', 'Lamp', 'Chair', 'Table'],
        'Books': ['Novel', 'Textbook', 'Cookbook', 'Biography', 'Comic'],
        'Toys': ['Action Figure', 'Doll', 'Puzzle', 'Board Game', 'Lego Set']
    }
    
    products_data = []
    for i in range(50):
        category = random.choice(categories)
        # Normalize category for lookup
        lookup_cat = category.capitalize() if category.capitalize() in product_names else 'Electronics'
        name = random.choice(product_names.get(lookup_cat, ['Generic Product'])) + f" {random.randint(100, 999)}"
        price = round(random.uniform(10.0, 1000.0), 2)
        inventory_count = random.randint(0, 100)
        products_data.append((name, category, price, inventory_count))
        
    cursor.executemany("INSERT INTO products (name, category, price, inventory_count) VALUES (?, ?, ?, ?)", products_data)

    # Seed Orders
    print("Seeding orders...")
    statuses = ['Pending', 'Shipped', 'Delivered', 'Cancelled', 'returned']
    
    orders_data = []
    customer_ids = [row[0] for row in cursor.execute("SELECT id FROM customers").fetchall()]
    
    for i in range(100):
        customer_id = random.choice(customer_ids)
        order_date = (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d')
        status = random.choice(statuses)
        orders_data.append((customer_id, order_date, status))
        
    cursor.executemany("INSERT INTO orders (customer_id, order_date, status) VALUES (?, ?, ?)", orders_data)

    # Seed Order Items
    print("Seeding order items...")
    order_ids = [row[0] for row in cursor.execute("SELECT id FROM orders").fetchall()]
    product_ids = [row[0] for row in cursor.execute("SELECT id FROM products").fetchall()]
    
    order_items_data = []
    for order_id in order_ids:
        # Each order has 1-5 items
        num_items = random.randint(1, 5)
        selected_products = random.sample(product_ids, num_items)
        for product_id in selected_products:
            quantity = random.randint(1, 10)
            order_items_data.append((order_id, product_id, quantity))
            
    cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)", order_items_data)

    conn.commit()
    print("Database seeded successfully.")

def main():
    # Remove existing db to start fresh
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        
    conn = create_connection()
    if conn is not None:
        create_tables(conn)
        seed_data(conn)
        conn.close()
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    main()
