import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# Path to the database file
db_path = 'inventory.db'

# Global variables
selected_button = None  # Currently selected category button
selected_category_id = None  # Currently selected category ID
cart_items = []  # List to store cart items as dictionaries

customer_info = {}  # Dictionary to store customer information after adding

# Function to create necessary tables
def create_tables():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sales table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            sales_trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    ''')

    # Create customer_list table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_list (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            mobile_number TEXT NOT NULL UNIQUE
        );
    ''')

    # Create customer_sales table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_trans_id INTEGER NOT NULL,
            customer_id TEXT NOT NULL,
            FOREIGN KEY (sales_trans_id) REFERENCES sales(sales_trans_id),
            FOREIGN KEY (customer_id) REFERENCES customer_list(customer_id)
        );
    ''')

    conn.commit()
    conn.close()

# Initialize database tables
create_tables()

# Function to search products
def search_products(search_query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if selected_category_id:
        cursor.execute('''
            SELECT products.product_id, products.product_name, products.sku,
                   IFNULL(stock_management.current_stock, 0) AS current_stock
            FROM products
            LEFT JOIN stock_management ON products.product_id = stock_management.product_id
            WHERE products.category_id = ? AND
                  (products.product_id LIKE ? OR products.sku LIKE ? OR products.product_name LIKE ?)
        ''', (selected_category_id, f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('''
            SELECT products.product_id, products.product_name, products.sku,
                   IFNULL(stock_management.current_stock, 0) AS current_stock
            FROM products
            LEFT JOIN stock_management ON products.product_id = stock_management.product_id
            WHERE products.product_id LIKE ? OR products.sku LIKE ? OR products.product_name LIKE ?
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))

    products = cursor.fetchall()
    conn.close()

    # Clear and repopulate the product list
    for item in product_list.get_children():
        product_list.delete(item)

    for product in products:
        product_list.insert("", "end", values=product)

# Function to filter products by category
def filter_products_by_category(category_id):
    global selected_category_id
    selected_category_id = category_id
    search_products('')  # Refresh product list

# Function to highlight selected category button
def highlight_button(button):
    global selected_button
    if selected_button:
        selected_button.config(bg="SystemButtonFace")
    button.config(bg="light blue")
    selected_button = button

# Function to show all categories
def show_all_categories(btn):
    global selected_category_id
    selected_category_id = None
    search_products('')
    highlight_button(btn)

# Function to add product to cart
def add_to_cart():
    selected_item = product_list.selection()
    if selected_item:
        product_id, product_name, sku, current_stock = product_list.item(selected_item)['values']
        quantity = quantity_var.get()

        # Check stock availability
        if quantity > current_stock:
            messagebox.showwarning("Insufficient Stock", f"Only {current_stock} units available.")
            return

        # Check if product is already in cart
        for item in cart_items:
            if item['product_id'] == product_id:
                total_quantity = item['quantity'] + quantity
                if total_quantity > current_stock:
                    messagebox.showwarning("Insufficient Stock", f"Only {current_stock} units available.")
                    return
                item['quantity'] = total_quantity
                item['total_price'] = item['unit_price'] * item['quantity']
                break
        else:
            # Fetch unit price
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT price FROM products WHERE product_id = ?', (product_id,))
            result = cursor.fetchone()
            unit_price = result[0] if result else 0.0
            conn.close()

            total_price = unit_price * quantity
            cart_items.append({
                'product_id': product_id,
                'product_name': product_name,
                'unit_price': unit_price,
                'quantity': quantity,
                'total_price': total_price
            })

        # Update cart display
        update_cart_display()

        # Reset selection and quantity
        product_list.selection_remove(selected_item)
        cart_list.selection_remove(cart_list.selection())
        quantity_var.set(1)

# Function to update cart item quantity
def update_cart():
    selected_item = cart_list.selection()
    if selected_item:
        current_qty = quantity_var.get()
        item_index = cart_list.index(selected_item)
        cart_item = cart_items[item_index]

        # Check stock availability
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT IFNULL(current_stock, 0) FROM stock_management WHERE product_id = ?', (cart_item['product_id'],))
        result = cursor.fetchone()
        current_stock = result[0] if result else 0
        conn.close()

        if current_qty > current_stock:
            messagebox.showwarning("Insufficient Stock", f"Only {current_stock} units available.")
            return

        cart_item['quantity'] = current_qty
        cart_item['total_price'] = cart_item['unit_price'] * current_qty

        update_cart_display()

        # Reset selection and quantity
        cart_list.selection_remove(selected_item)
        product_list.selection_remove(product_list.selection())
        quantity_var.set(1)

# Function to remove item from cart
def remove_from_cart():
    selected_item = cart_list.selection()
    if selected_item:
        item_index = cart_list.index(selected_item)
        del cart_items[item_index]
        update_cart_display()
        cart_list.selection_remove(selected_item)

# Function to update cart display
def update_cart_display():
    # Clear and repopulate cart list
    for item in cart_list.get_children():
        cart_list.delete(item)

    total_cost = 0.0
    for item in cart_items:
        cart_list.insert("", "end", values=(item['product_name'], item['unit_price'], item['quantity'], item['total_price']))
        total_cost += item['total_price']

    total_label.config(text=f"Total: ${total_cost:.2f}")

# Function to record sale and update stock
def record_sale_and_update_stock():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        for item in cart_items:
            product_id = item['product_id']
            quantity = item['quantity']
            unit_price = item['unit_price']
            total_price = item['total_price']

            # Record sale
            cursor.execute('''
                INSERT INTO sales (product_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?)
            ''', (product_id, quantity, unit_price, total_price))

            sales_trans_id = cursor.lastrowid

            # Update stock
            cursor.execute('''
                UPDATE stock_management
                SET current_stock = current_stock - ?
                WHERE product_id = ?
            ''', (quantity, product_id))

            # Log stock transaction
            cursor.execute('''
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, ?, ?)
            ''', (product_id, -quantity, 'Sale', 'sales'))

            # Link sale to customer if applicable
            if customer_info:
                cursor.execute('''
                    INSERT INTO customer_sales (sales_trans_id, customer_id)
                    VALUES (?, ?)
                ''', (sales_trans_id, customer_info['customer_id']))

        conn.commit()
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        conn.close()

# Function to handle checkout
def checkout():
    if not cart_items:
        messagebox.showwarning("Warning", "Your cart is empty!")
        return

    summary = "Sales Summary:\n"
    total_sales = 0.0
    for item in cart_items:
        summary += f"{item['product_name']}: Quantity {item['quantity']}, Total ${item['total_price']:.2f}\n"
        total_sales += item['total_price']

    summary += f"\nTotal Sale Amount: ${total_sales:.2f}"

    if customer_info:
        summary += f"\n\nCustomer: {customer_info['customer_name']} ({customer_info['mobile_number']})"

    record_sale_and_update_stock()
    messagebox.showinfo("Checkout", summary)

    # Reset cart and customer info
    clear_cart()
    search_products(search_entry.get())
    clear_customer_info()

# Function to clear the cart
def clear_cart():
    global cart_items
    cart_items = []
    update_cart_display()
    quantity_var.set(1)
    cart_list.selection_remove(cart_list.selection())
    product_list.selection_remove(product_list.selection())

# Function to handle product selection
def on_product_select(event):
    cart_list.selection_remove(cart_list.selection())

# Function to handle cart selection
def on_cart_select(event):
    product_list.selection_remove(product_list.selection())

# Function to add customer
def add_customer():
    mobile_number = customer_mobile_var.get()
    if not mobile_number:
        messagebox.showwarning("Warning", "Please enter a mobile number.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT customer_id, customer_name FROM customer_list WHERE mobile_number = ?', (mobile_number,))
    result = cursor.fetchone()

    if result:
        # Existing customer
        customer_id, customer_name = result
        customer_info['customer_id'] = customer_id
        customer_info['customer_name'] = customer_name
        customer_info['mobile_number'] = mobile_number
        customer_label.config(text=f"Customer: {customer_name} ({mobile_number})")

        messagebox.showinfo("Customer Assigned", f"Customer {customer_name} assigned to the current cart.")
    else:
        # New customer
        def save_new_customer():
            customer_name = name_entry.get()
            if not customer_name:
                messagebox.showwarning("Warning", "Please enter the customer's name.")
                return
            try:
                conn_inner = sqlite3.connect(db_path)
                cursor_inner = conn_inner.cursor()

                # Generate new customer_id using SQL
                cursor_inner.execute("""
                    SELECT MAX(CAST(SUBSTR(customer_id, 5) AS INTEGER)) 
                    FROM customer_list 
                    WHERE customer_id LIKE 'cus-%'
                """)
                result = cursor_inner.fetchone()
                if result[0]:
                    new_num = result[0] + 1
                else:
                    new_num = 1
                customer_id = f"cus-{new_num:06d}"

                # Insert new customer with customer_id
                cursor_inner.execute('''
                    INSERT INTO customer_list (customer_id, customer_name, mobile_number)
                    VALUES (?, ?, ?)
                ''', (customer_id, customer_name, mobile_number))
                conn_inner.commit()

                customer_info['customer_id'] = customer_id
                customer_info['customer_name'] = customer_name
                customer_info['mobile_number'] = mobile_number

                customer_label.config(text=f"Customer: {customer_name} ({mobile_number})")

                new_customer_window.destroy()

                messagebox.showinfo("Customer Added", f"Customer {customer_name} added and assigned to the current cart.")

            except Exception as e:
                conn_inner.rollback()
                messagebox.showerror("Error", f"An error occurred: {e}")
            finally:
                conn_inner.close()

        new_customer_window = tk.Toplevel(root)
        new_customer_window.title("New Customer")
        tk.Label(new_customer_window, text="Enter Customer Name:").pack(pady=5)
        name_entry = tk.Entry(new_customer_window)
        name_entry.pack(pady=5)
        tk.Button(new_customer_window, text="Save", command=save_new_customer).pack(pady=5)

    conn.close()

# Function to clear customer info
def clear_customer_info():
    global customer_info
    customer_info = {}
    customer_mobile_var.set('')
    customer_label.config(text="Customer:")

# Main window setup
root = tk.Tk()
root.title("POS Interface")
root.geometry("1200x950")

# Configure grid layout
root.columnconfigure(0, weight=1, minsize=200)
root.columnconfigure(1, weight=2, minsize=400)
root.columnconfigure(2, weight=2, minsize=400)

# 1st Column: Categories and Search Bar
frame_categories = tk.Frame(root, bd=2, relief="sunken")
frame_categories.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

# Search Bar
search_label = tk.Label(frame_categories, text="Search (ID, SKU, Name):")
search_label.pack(pady=5)
search_entry = tk.Entry(frame_categories)
search_entry.pack(pady=5, padx=5, fill="x")

def on_search(event):
    search_query = search_entry.get()
    search_products(search_query)

search_entry.bind('<KeyRelease>', on_search)

# Categories Label
categories_label = tk.Label(frame_categories, text="Product Categories", font=("Arial", 14))
categories_label.pack(pady=10)

# All Categories Button
btn_all_categories = tk.Button(frame_categories, text="All Categories", height=2, width=20)
btn_all_categories.config(command=lambda btn=btn_all_categories: show_all_categories(btn))
btn_all_categories.pack(pady=5)

# Fetch and display categories
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT category_id, category_name FROM product_categories")
categories = cursor.fetchall()
conn.close()

for category in categories:
    category_id, category_name = category
    btn_category = tk.Button(frame_categories, text=category_name, height=2, width=20)
    btn_category.config(command=lambda cid=category_id, btn=btn_category: (filter_products_by_category(cid), highlight_button(btn)))
    btn_category.pack(pady=5)

# 2nd Column: Product List and Quantity
frame_product = tk.Frame(root, bd=2, relief="sunken")
frame_product.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

columns = ("Product ID", "Product Name", "SKU", "Stock")
product_list = ttk.Treeview(frame_product, columns=columns, show="headings")

product_list.column("Product ID", width=80)
product_list.column("Product Name", width=150)
product_list.column("SKU", width=80)
product_list.column("Stock", width=60)

for col in columns:
    product_list.heading(col, text=col)
product_list.pack(padx=5, pady=5, fill="both", expand=True)

product_list.bind('<<TreeviewSelect>>', on_product_select)

# Quantity and Buttons
frame_quantity = tk.Frame(frame_product)
frame_quantity.pack(pady=10)

quantity_label = tk.Label(frame_quantity, text="Quantity:")
quantity_label.grid(row=1, column=0, padx=5)
quantity_var = tk.IntVar(value=1)
quantity_entry = tk.Entry(frame_quantity, textvariable=quantity_var, width=5)
quantity_entry.grid(row=1, column=1)

btn_minus = tk.Button(frame_quantity, text="-", width=2, command=lambda: quantity_var.set(max(quantity_var.get() - 1, 1)))
btn_minus.grid(row=1, column=2)
btn_plus = tk.Button(frame_quantity, text="+", width=2, command=lambda: quantity_var.set(quantity_var.get() + 1))
btn_plus.grid(row=1, column=3)

btn_add_to_cart = tk.Button(frame_quantity, text="Add to Cart", width=15, command=add_to_cart)
btn_add_to_cart.grid(row=2, column=0, pady=10)

btn_update_cart = tk.Button(frame_quantity, text="Update Cart", width=15, command=update_cart)
btn_update_cart.grid(row=2, column=1, pady=10)

btn_remove_from_cart = tk.Button(frame_quantity, text="Remove", width=15, command=remove_from_cart)
btn_remove_from_cart.grid(row=2, column=2, pady=10)

# 3rd Column: Cart and Customer Info
frame_cart = tk.Frame(root, bd=2, relief="sunken")
frame_cart.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

cart_columns = ("Product Name", "Unit Price", "Quantity", "Total Price")
cart_list = ttk.Treeview(frame_cart, columns=cart_columns, show="headings")

cart_list.column("Product Name", width=150)
cart_list.column("Unit Price", width=80)
cart_list.column("Quantity", width=80)
cart_list.column("Total Price", width=100)

for col in cart_columns:
    cart_list.heading(col, text=col)
cart_list.pack(padx=5, pady=5, fill="both", expand=True)

cart_list.bind('<<TreeviewSelect>>', on_cart_select)

# Total and Customer Info
frame_total = tk.Frame(frame_cart)
frame_total.pack(pady=10)

total_label = tk.Label(frame_total, text="Total: $0.00", font=("Arial", 14))
total_label.grid(row=0, column=0, padx=5)

promo_label = tk.Label(frame_total, text="Promo Code:")
promo_label.grid(row=1, column=0, padx=5)
promo_entry = tk.Entry(frame_total)
promo_entry.grid(row=1, column=1)

customer_mobile_label = tk.Label(frame_total, text="Customer Mobile:")
customer_mobile_label.grid(row=2, column=0, padx=5)
customer_mobile_var = tk.StringVar()
customer_mobile_entry = tk.Entry(frame_total, textvariable=customer_mobile_var)
customer_mobile_entry.grid(row=2, column=1)

btn_add_customer = tk.Button(frame_total, text="Add Customer", command=add_customer)
btn_add_customer.grid(row=2, column=2, padx=5)

customer_label = tk.Label(frame_total, text="Customer:")
customer_label.grid(row=3, column=0, columnspan=3, pady=5)

# Sales Control Buttons
frame_sales_controls = tk.Frame(frame_cart)
frame_sales_controls.pack(pady=10)

btn_new_sales = tk.Button(frame_sales_controls, text="New Sale", width=15, command=lambda: [clear_cart(), clear_customer_info()])
btn_new_sales.pack(side=tk.LEFT, padx=5)

btn_clear_cart = tk.Button(frame_sales_controls, text="Clear Cart", width=15, command=clear_cart)
btn_clear_cart.pack(side=tk.LEFT, padx=5)

btn_checkout = tk.Button(frame_sales_controls, text="Checkout", width=15, command=checkout)
btn_checkout.pack(side=tk.LEFT, padx=5)

# Initialize product list
search_products('')

root.mainloop()
