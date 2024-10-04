import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# Database connection
db_path = 'inventory.db'  # Use your updated database file
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch categories from the database
cursor.execute('SELECT category_id, category_name FROM product_categories')
categories = cursor.fetchall()

# Helper functions
def generate_product_id():
    cursor.execute('SELECT product_id FROM products ORDER BY product_id')
    existing_ids = cursor.fetchall()
    existing_nums = sorted([int(id[0].replace('PID-', '')) for id in existing_ids])

    new_id_num = 1
    for num in existing_nums:
        if num != new_id_num:
            break
        new_id_num += 1

    return f'PID-{str(new_id_num).zfill(5)}'

def reset_fields():
    product_id_var.set(generate_product_id())
    name_var.set('')
    sku_var.set('')
    category_var.set('')
    price_var.set('')
    description_var.set('')
    product_table.selection_remove(product_table.selection())

def load_product_details(event):
    selected = product_table.selection()
    if selected:
        item = product_table.item(selected)
        values = item['values']
        product_id_var.set(values[0])       # Product ID
        name_var.set(values[1])             # Product Name
        sku_var.set(values[2])              # SKU
        category_var.set(f"{values[3]}: {values[4]}")  # Category (combination of ID and Name)
        price_var.set(values[5])            # Price
        description_var.set(values[6])      # Description

        # Clear the search field when a selection is made
        search_var.set('')

def is_valid_category(category):
    return category in [f"{cat[0]}: {cat[1]}" for cat in categories]

def search_products(event=None):
    search_term = search_var.get().lower()
    selected_category = category_filter_var.get()
    if selected_category and selected_category != 'All Categories':
        category_id = selected_category.split(":")[0]
    else:
        category_id = None

    # Clear the table
    for row in product_table.get_children():
        product_table.delete(row)

    # Build the SQL query
    query = '''
    SELECT * FROM products 
    WHERE (LOWER(product_id) LIKE ? OR LOWER(product_name) LIKE ? OR LOWER(sku) LIKE ?)
    '''
    params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']

    if category_id:
        query += ' AND category_id = ?'
        params.append(category_id)

    cursor.execute(query, params)
    for product in cursor.fetchall():
        product_table.insert('', 'end', values=product)

def add_product():
    product_id = product_id_var.get()
    name = name_var.get().upper()
    sku = sku_var.get().upper()
    category = category_var.get()

    category_id = category.split(":")[0] if category else None
    price = price_var.get()
    description = description_var.get()

    if not name or not sku or not category_id or not price:
        messagebox.showerror("Error", "All fields except description are required.")
        return

    if not is_valid_category(category):
        messagebox.showerror("Error", "Invalid category selected.")
        return

    try:
        cursor.execute('''
        INSERT INTO products (product_id, product_name, sku, category_id, category_name, price, description) 
        VALUES (?, ?, ?, ?, (SELECT category_name FROM product_categories WHERE category_id = ?), ?, ?)
        ''', (product_id, name, sku, category_id, category_id, price, description))
        conn.commit()
        messagebox.showinfo("Success", "Product added successfully.")
        search_products()
        reset_fields()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "SKU already exists.")

def update_product():
    selected = product_table.selection()
    if not selected:
        messagebox.showerror("Error", "No product selected.")
        return

    product_id = product_id_var.get()
    name = name_var.get().upper()
    sku = sku_var.get().upper()
    category = category_var.get()

    category_id = category.split(":")[0] if category else None
    price = price_var.get()
    description = description_var.get()

    if not is_valid_category(category):
        messagebox.showerror("Error", "Invalid category selected.")
        return

    try:
        cursor.execute('''
        UPDATE products 
        SET product_name = ?, sku = ?, category_id = ?, category_name = (SELECT category_name FROM product_categories WHERE category_id = ?), price = ?, description = ? 
        WHERE product_id = ?
        ''', (name, sku, category_id, category_id, price, description, product_id))
        conn.commit()
        messagebox.showinfo("Success", "Product updated successfully.")
        search_products()
        reset_fields()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "SKU already exists.")

def delete_product():
    selected = product_table.selection()
    if not selected:
        messagebox.showerror("Error", "No product selected.")
        return

    product_id = product_id_var.get()

    cursor.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
    conn.commit()
    messagebox.showinfo("Success", "Product deleted successfully.")
    search_products()
    reset_fields()

def view_all_products():
    search_var.set('')
    category_filter_var.set('All Categories')
    search_products()

# Main application window
app = tk.Tk()
app.title("Product Management")
app.geometry("900x500")  # Window height is set to 500

# Variables
product_id_var = tk.StringVar(value=generate_product_id())
name_var = tk.StringVar()
sku_var = tk.StringVar()
category_var = tk.StringVar()
price_var = tk.StringVar()
description_var = tk.StringVar()
search_var = tk.StringVar()
category_filter_var = tk.StringVar(value='All Categories')

# Input fields
tk.Label(app, text="Product ID").grid(row=0, column=0, padx=10, pady=5)
tk.Entry(app, textvariable=product_id_var, state='readonly').grid(row=0, column=1, padx=10, pady=5)

tk.Label(app, text="Product Name").grid(row=1, column=0, padx=10, pady=5)
tk.Entry(app, textvariable=name_var).grid(row=1, column=1, padx=10, pady=5)

tk.Label(app, text="SKU").grid(row=2, column=0, padx=10, pady=5)
tk.Entry(app, textvariable=sku_var).grid(row=2, column=1, padx=10, pady=5)

tk.Label(app, text="Category").grid(row=3, column=0, padx=10, pady=5)
category_options = [f"{cat[0]}: {cat[1]}" for cat in categories]
category_menu = ttk.Combobox(app, textvariable=category_var, values=category_options)
category_menu.grid(row=3, column=1, padx=10, pady=5)

tk.Label(app, text="Price").grid(row=4, column=0, padx=10, pady=5)
tk.Entry(app, textvariable=price_var).grid(row=4, column=1, padx=10, pady=5)

tk.Label(app, text="Description").grid(row=5, column=0, padx=10, pady=5)
tk.Entry(app, textvariable=description_var).grid(row=5, column=1, padx=10, pady=5)

# Filter frame for search and category filter
filter_frame = tk.Frame(app)
filter_frame.grid(row=6, column=0, columnspan=5, padx=10, pady=5)

# Search box
tk.Label(filter_frame, text="Search:").grid(row=0, column=0, padx=5)
search_entry = tk.Entry(filter_frame, textvariable=search_var)
search_entry.grid(row=0, column=1, padx=5)
search_entry.bind('<KeyRelease>', search_products)  # Bind the search box to key release event for dynamic search

# Category filter
tk.Label(filter_frame, text="Filter by Category:").grid(row=0, column=2, padx=5)
category_filter_options = ['All Categories'] + [f"{cat[0]}: {cat[1]}" for cat in categories]
category_filter_menu = ttk.Combobox(filter_frame, textvariable=category_filter_var, values=category_filter_options)
category_filter_menu.grid(row=0, column=3, padx=5)
category_filter_menu.bind('<<ComboboxSelected>>', search_products)

# Buttons
tk.Button(app, text="Add Product", command=add_product).grid(row=7, column=0, padx=10, pady=10)
tk.Button(app, text="Update Product", command=update_product).grid(row=7, column=1, padx=10, pady=10)
tk.Button(app, text="Delete Product", command=delete_product).grid(row=7, column=2, padx=10, pady=10)
tk.Button(app, text="View All Products", command=view_all_products).grid(row=7, column=3, padx=10, pady=10)

# Clear fields button
tk.Button(app, text="Clear Fields", command=reset_fields).grid(row=7, column=4, padx=10, pady=10)

# Scrollbar for the table
scrollbar = ttk.Scrollbar(app)
scrollbar.grid(row=8, column=5, sticky="ns")

# Table for displaying products with scrollbar
columns = ("product_id", "product_name", "sku", "category_id", "category_name", "price", "description")
product_table = ttk.Treeview(app, columns=columns, show="headings", yscrollcommand=scrollbar.set)
scrollbar.config(command=product_table.yview)

for col in columns:
    product_table.heading(col, text=col.replace("_", " ").title())  # Adjusting column headers for readability
    product_table.column(col, width=100)
product_table.grid(row=8, column=0, columnspan=5, padx=10, pady=10)

product_table.bind('<<TreeviewSelect>>', load_product_details)

# Start by viewing all products
view_all_products()

# Start the application
app.mainloop()

# Close the database connection when the app closes
conn.close()
