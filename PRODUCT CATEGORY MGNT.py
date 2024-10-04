import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

# Create and connect to SQLite database
def create_tables():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    # Create Product Categories Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS product_categories (
                        category_id TEXT PRIMARY KEY,
                        category_name TEXT UNIQUE NOT NULL,
                        description TEXT)''')

    conn.commit()
    conn.close()

# Function to generate unique category ID
def generate_category_id():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category_id FROM product_categories ORDER BY category_id')
    existing_ids = cursor.fetchall()
    conn.close()

    existing_numbers = sorted([int(id[0].split('-')[1]) for id in existing_ids])
    next_id = 1
    for num in existing_numbers:
        if num != next_id:
            break
        next_id += 1

    return f"PC-{next_id:03d}"

# Function to add a product category
def add_category(category_name, description):
    category_id = generate_category_id()  # Automatically generate category ID
    category_name = category_name.upper()  # Convert to uppercase
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO product_categories (category_id, category_name, description)
                          VALUES (?, ?, ?)''', (category_id, category_name, description))
        conn.commit()
    except sqlite3.IntegrityError as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()

# Function to update a product category
def update_category(category_id, category_name, description):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''UPDATE product_categories 
                          SET category_name = ?, description = ?
                          WHERE category_id = ?''', (category_name, description, category_id))
        conn.commit()
    except sqlite3.IntegrityError as e:
        messagebox.showerror("Error", str(e))
    finally:
        conn.close()

# Function to delete a product category
def delete_category(category_id):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM products WHERE category_id = ?', (category_id,))
    product_count = cursor.fetchone()[0]

    if product_count > 0:
        messagebox.showerror("Error", "Cannot delete category. Products are assigned to this category.")
    else:
        cursor.execute('''DELETE FROM product_categories WHERE category_id = ?''', (category_id,))
        conn.commit()

    conn.close()

# Tkinter UI setup for Category Management
class CategoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Category Management")
        create_tables()

        self.setup_category_ui()

    def setup_category_ui(self):
        category_frame = tk.Frame(self.root)
        category_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        lbl_category_name = tk.Label(category_frame, text="Category Name:")
        lbl_category_name.pack(anchor='w')
        self.entry_category_name = tk.Entry(category_frame)
        self.entry_category_name.pack(anchor='w', fill=tk.X)

        lbl_category_desc = tk.Label(category_frame, text="Description:")
        lbl_category_desc.pack(anchor='w')
        self.entry_category_desc = tk.Entry(category_frame)
        self.entry_category_desc.pack(anchor='w', fill=tk.X)

        btn_add_category = tk.Button(category_frame, text="Add Category", command=self.add_category_action)
        btn_add_category.pack(side=tk.LEFT, padx=5, pady=10)

        btn_update_category = tk.Button(category_frame, text="Update Category", command=self.update_category_action)
        btn_update_category.pack(side=tk.LEFT, padx=5, pady=10)

        btn_delete_category = tk.Button(category_frame, text="Delete Category", command=self.delete_category_action)
        btn_delete_category.pack(side=tk.LEFT, padx=5, pady=10)

        btn_clear_fields = tk.Button(category_frame, text="Clear Fields", command=self.clear_fields)
        btn_clear_fields.pack(side=tk.LEFT, padx=5, pady=10)  # Clear Fields button added here

        self.category_tree = ttk.Treeview(category_frame, columns=("ID", "Name", "Description"), show='headings')
        self.category_tree.heading("ID", text="Category ID")
        self.category_tree.heading("Name", text="Category Name")
        self.category_tree.heading("Description", text="Description")
        self.category_tree.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(category_frame, orient="vertical", command=self.category_tree.yview)
        self.category_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.category_tree.bind("<<TreeviewSelect>>", self.on_category_select)

        self.show_category_list()

    def add_category_action(self):
        category_name = self.entry_category_name.get()
        description = self.entry_category_desc.get()
        if category_name:
            add_category(category_name, description)
            self.show_category_list()
            self.clear_fields()  # Clear the fields and selection after adding
        else:
            messagebox.showerror("Error", "Category name is required.")

    def update_category_action(self):
        category_name = self.entry_category_name.get()
        description = self.entry_category_desc.get()
        if category_name and hasattr(self, 'selected_category_id'):
            update_category(self.selected_category_id, category_name, description)
            self.show_category_list()  # Refresh the list after update
            self.clear_fields()  # Clear the fields and selection after updating
        else:
            messagebox.showerror("Error", "Select a category to update.")

    def delete_category_action(self):
        if hasattr(self, 'selected_category_id'):
            delete_category(self.selected_category_id)
            self.show_category_list()  # Refresh the list after delete
            self.clear_fields()  # Clear the fields and selection after deletion
        else:
            messagebox.showerror("Error", "Select a category to delete.")

    def on_category_select(self, event):
        selected_items = self.category_tree.selection()  # Get selected items
        if selected_items:  # Check if there is at least one item selected
            selected_item = selected_items[0]
            category_id, category_name, description = self.category_tree.item(selected_item, "values")
            self.entry_category_name.delete(0, tk.END)
            self.entry_category_name.insert(0, category_name)
            self.entry_category_desc.delete(0, tk.END)
            self.entry_category_desc.insert(0, description)
            self.selected_category_id = category_id  # Set the selected category ID

    def show_category_list(self):
        for i in self.category_tree.get_children():
            self.category_tree.delete(i)

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM product_categories ORDER BY category_id')
        categories = cursor.fetchall()
        conn.close()

        for category in categories:
            self.category_tree.insert("", "end", values=category)

    def clear_fields(self):
        """Clear the input fields and selection in the table."""
        self.entry_category_name.delete(0, tk.END)
        self.entry_category_desc.delete(0, tk.END)
        self.category_tree.selection_remove(self.category_tree.selection())  # Remove selection from the table

# Main application start
if __name__ == "__main__":
    root = tk.Tk()
    app = CategoryApp(root)
    root.mainloop()
