import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# Path to the database file (assumed to be in the same folder)
db_path = 'inventory.db'

# Track the selected category ID globally
selected_button = None  # Keeps track of the currently selected button
selected_category_id = None
cart_items = []  # List to store cart items as dictionaries for easy manipulation

# Function to create necessary tables
def create_tables():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sales table to track sales
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

    # Note: We are not creating 'stock_transactions' table as it already exists
    conn.commit()
    conn.close()

# Call this function when the program starts to ensure the tables exist
create_tables()

# Function to search products in the selected category by product ID, SKU, or product name
def search_products(search_query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Adjust the query to filter by selected category, if any
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

    # Clear the product list before inserting new search results
    for item in product_list.get_children():
        product_list.delete(item)

    # Populate the product list with the search results, including stock
    for product in products:
        product_list.insert("", "end", values=product)

# Function to filter products by category and update the search context
def filter_products_by_category(category_id):
    global selected_category_id
    selected_category_id = category_id

    search_products('')  # Show all products in the selected category

# Function to highlight the selected button and reset others
def highlight_button(button):
    global selected_button
    if selected_button:
        selected_button.config(bg="SystemButtonFace")  # Reset the previous button to default color
    button.config(bg="light blue")  # Set the new button's background to light blue
    selected_button = button  # Track the currently selected button

# Function to reset and show all categories
def show_all_categories(btn):
    global selected_category_id
    selected_category_id = None
    search_products('')  # Show all products
    highlight_button(btn)  # Highlight the "All Categories" button

# Function to add selected product to cart
def add_to_cart():
    selected_item = product_list.selection()
    if selected_item:
        product_id, product_name, sku, current_stock = product_list.item(selected_item)['values']
        quantity = quantity_var.get()

        # Check if product already in cart
        for item in cart_items:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                item['total_price'] = item['unit_price'] * item['quantity']
                break
        else:
            # Fetch unit price from database
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

        update_cart_display()

        # Remove selection before updating the display
        product_list.selection_remove(selected_item)
        cart_list.selection_remove(cart_list.selection())

        update_cart_display()

        # Reset quantity
        quantity_var.set(1)
        
# Function to update the selected cart item's quantity
def update_cart():
    selected_item = cart_list.selection()
    if selected_item:
        current_qty = quantity_var.get()
        item_index = cart_list.index(selected_item)
        cart_item = cart_items[item_index]
        cart_item['quantity'] = current_qty
        cart_item['total_price'] = cart_item['unit_price'] * current_qty

        # Remove selection before updating the display
        cart_list.selection_remove(selected_item)

        update_cart_display()

        # Reset quantity and selections
        quantity_var.set(1)
        product_list.selection_remove(product_list.selection())

# Function to remove the selected entry from the cart
def remove_from_cart():
    selected_item = cart_list.selection()
    if selected_item:
        item_index = cart_list.index(selected_item)

        # Remove selection before updating the display
        cart_list.selection_remove(selected_item)

        del cart_items[item_index]  # Remove the selected item from the cart
        update_cart_display()

# Function to update the cart display
def update_cart_display():
    # Clear the cart display
    for item in cart_list.get_children():
        cart_list.delete(item)

    # Populate the cart display
    total_cost = 0.0
    for item in cart_items:
        cart_list.insert("", "end", values=(item['product_name'], item['unit_price'], item['quantity'], item['total_price']))
        total_cost += item['total_price']

    total_label.config(text=f"Total: ${total_cost:.2f}")

# Function to record the sale and update stock
def record_sale_and_update_stock():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        for item in cart_items:
            product_id = item['product_id']
            quantity = item['quantity']
            unit_price = item['unit_price']
            total_price = item['total_price']

            # Record sale in sales table
            cursor.execute('''
                INSERT INTO sales (product_id, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?)
            ''', (product_id, quantity, unit_price, total_price))

            # Update current stock in stock_management table
            cursor.execute('''
                UPDATE stock_management
                SET current_stock = current_stock - ?
                WHERE product_id = ?
            ''', (quantity, product_id))

            # Log the transaction in stock_transactions table
            cursor.execute('''
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, ?, ?)
            ''', (product_id, -quantity, 'Sale', 'sales'))  # Negative quantity to indicate deduction

        conn.commit()
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        conn.close()

# Function to finalize the sale and display a summary
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
    record_sale_and_update_stock()
    messagebox.showinfo("Checkout", summary)  # Display summary pop-up

    clear_cart()  # Clear the cart after checkout
    search_products(search_entry.get())  # Refresh product list to update stock

# Function to clear the cart
def clear_cart():
    global cart_items
    cart_items = []  # Clear the cart items list
    update_cart_display()
    quantity_var.set(1)
    cart_list.selection_remove(cart_list.selection())
    product_list.selection_remove(product_list.selection())

# Function to handle selection in product list
def on_product_select(event):
    # Clear selection in cart list
    cart_list.selection_remove(cart_list.selection())

# Function to handle selection in cart list
def on_cart_select(event):
    # Clear selection in product list
    product_list.selection_remove(product_list.selection())

# Main window setup
root = tk.Tk()
root.title("POS Interface")
root.geometry("1200x950")  # Adjust size to fit layout

# Configure grid layout with three main sections (columns)
root.columnconfigure(0, weight=1, minsize=200)
root.columnconfigure(1, weight=2, minsize=400)
root.columnconfigure(2, weight=2, minsize=400)

# 1st Column: Product Categories + Search Bar
frame_categories = tk.Frame(root, bd=2, relief="sunken")
frame_categories.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

# Search Bar
search_label = tk.Label(frame_categories, text="Search (ID, SKU, Name):")
search_label.pack(pady=5)
search_entry = tk.Entry(frame_categories)
search_entry.pack(pady=5, padx=5, fill="x")

# Bind search function to search bar
def on_search(event):
    search_query = search_entry.get()
    search_products(search_query)

search_entry.bind('<KeyRelease>', on_search)

# Placeholder for Product Category Icons
categories_label = tk.Label(frame_categories, text="Product Categories", font=("Arial", 14))
categories_label.pack(pady=10)

# Add button for 'All Categories'
btn_all_categories = tk.Button(frame_categories, text="All Categories", height=2, width=20)
btn_all_categories.config(command=lambda btn=btn_all_categories: show_all_categories(btn))
btn_all_categories.pack(pady=5)

# Dynamically generate buttons for categories from the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch categories from the database
cursor.execute("SELECT category_id, category_name FROM product_categories")
categories = cursor.fetchall()

conn.close()

# Create a button for each category to filter products
for category in categories:
    category_id, category_name = category
    btn_category = tk.Button(frame_categories, text=category_name, height=2, width=20)
    btn_category.config(command=lambda cid=category_id, btn=btn_category: (filter_products_by_category(cid), highlight_button(btn)))
    btn_category.pack(pady=5)

# 2nd Column: Product List + Quantity Entry
frame_product = tk.Frame(root, bd=2, relief="sunken")
frame_product.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

# Treeview for product list with fixed column sizes
columns = ("Product ID", "Product Name", "SKU", "Stock")
product_list = ttk.Treeview(frame_product, columns=columns, show="headings")

# Set fixed widths for columns
product_list.column("Product ID", width=80)
product_list.column("Product Name", width=150)
product_list.column("SKU", width=80)
product_list.column("Stock", width=60)  # 'Stock' column for current stock

for col in columns:
    product_list.heading(col, text=col)
product_list.pack(padx=5, pady=5, fill="both", expand=True)

# Bind selection event to handle single selection rule
product_list.bind('<<TreeviewSelect>>', on_product_select)

# Bottom Section: Quantity Entry & Buttons
frame_quantity = tk.Frame(frame_product)
frame_quantity.pack(pady=10)

# Quantity Entry
quantity_label = tk.Label(frame_quantity, text="Quantity:")
quantity_label.grid(row=1, column=0, padx=5)
quantity_var = tk.IntVar(value=1)
quantity_entry = tk.Entry(frame_quantity, textvariable=quantity_var, width=5)
quantity_entry.grid(row=1, column=1)

# Plus/Minus buttons
btn_minus = tk.Button(frame_quantity, text="-", width=2, command=lambda: quantity_var.set(max(quantity_var.get() - 1, 1)))
btn_minus.grid(row=1, column=2)
btn_plus = tk.Button(frame_quantity, text="+", width=2, command=lambda: quantity_var.set(quantity_var.get() + 1))
btn_plus.grid(row=1, column=3)

# Add to Cart Button
btn_add_to_cart = tk.Button(frame_quantity, text="Add to Cart", width=15, command=add_to_cart)
btn_add_to_cart.grid(row=2, column=0, pady=10)

# Update Cart Button
btn_update_cart = tk.Button(frame_quantity, text="Update Cart", width=15, command=update_cart)
btn_update_cart.grid(row=2, column=1, pady=10)

# Remove from Cart Button
btn_remove_from_cart = tk.Button(frame_quantity, text="Remove", width=15, command=remove_from_cart)
btn_remove_from_cart.grid(row=2, column=2, pady=10)

# 3rd Column: Active Cart + Total
frame_cart = tk.Frame(root, bd=2, relief="sunken")
frame_cart.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

# Treeview for cart items with fixed column sizes
cart_columns = ("Product Name", "Unit Price", "Quantity", "Total Price")
cart_list = ttk.Treeview(frame_cart, columns=cart_columns, show="headings")

# Set fixed widths for cart columns
cart_list.column("Product Name", width=150)
cart_list.column("Unit Price", width=80)
cart_list.column("Quantity", width=80)
cart_list.column("Total Price", width=100)

for col in cart_columns:
    cart_list.heading(col, text=col)
cart_list.pack(padx=5, pady=5, fill="both", expand=True)

# Bind selection event to handle single selection rule
cart_list.bind('<<TreeviewSelect>>', on_cart_select)

# Total and Promo Code Section
frame_total = tk.Frame(frame_cart)
frame_total.pack(pady=10)

total_label = tk.Label(frame_total, text="Total: $0.00", font=("Arial", 14))
total_label.grid(row=0, column=0, padx=5)

# Promo Code Entry (Placeholder for future functionality)
promo_label = tk.Label(frame_total, text="Promo Code:")
promo_label.grid(row=1, column=0, padx=5)
promo_entry = tk.Entry(frame_total)
promo_entry.grid(row=1, column=1)

# Sales control buttons in the third column
frame_sales_controls = tk.Frame(frame_cart)
frame_sales_controls.pack(pady=10)

# New Sales Button
btn_new_sales = tk.Button(frame_sales_controls, text="New Sale", width=15, command=clear_cart)
btn_new_sales.pack(side=tk.LEFT, padx=5)

# Clear Cart Button
btn_clear_cart = tk.Button(frame_sales_controls, text="Clear Cart", width=15, command=clear_cart)
btn_clear_cart.pack(side=tk.LEFT, padx=5)

# Checkout Button
btn_checkout = tk.Button(frame_sales_controls, text="Checkout", width=15, command=checkout)
btn_checkout.pack(side=tk.LEFT, padx=5)

# Initialize product list
search_products('')

root.mainloop()
