import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class InventoryManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management")
        self.root.geometry("1000x500")  # Updated window size for new layout

        # Connect to the database and ensure tables are created
        self.conn = sqlite3.connect("inventory.db")
        self.cursor = self.conn.cursor()
        self.create_tables()  # Ensure required tables exist

        # Search and filter section
        search_label = tk.Label(self.root, text="Search:")
        search_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.search_entry = tk.Entry(self.root, width=30)
        self.search_entry.grid(row=0, column=1, padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", self.search_and_filter_products)

        filters_label = tk.Label(self.root, text="Category Filter:")
        filters_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.category_combobox = ttk.Combobox(self.root, state="readonly", width=30)
        self.category_combobox.grid(row=0, column=3, padx=10, pady=10)
        self.category_combobox.bind("<<ComboboxSelected>>", self.search_and_filter_products)

        # Populate the combobox with categories when the app starts
        self.load_categories()

        # Product Table (Treeview)
        self.table = ttk.Treeview(self.root, columns=("product_id", "product_name", "sku", "category_id", "category_name", "current_stock", "safety_stock", "target_stock"), show="headings")

        # Set the headings
        self.table.heading("product_id", text="Product ID")
        self.table.heading("product_name", text="Product Name")
        self.table.heading("sku", text="SKU")
        self.table.heading("category_id", text="Category ID")
        self.table.heading("category_name", text="Category Name")
        self.table.heading("current_stock", text="Current Stock")
        self.table.heading("safety_stock", text="Safety Stock")
        self.table.heading("target_stock", text="Target Stock")

        # Set the column widths
        self.table.column("product_id", width=150)
        self.table.column("product_name", width=200)
        self.table.column("sku", width=100)
        self.table.column("category_id", width=100)
        self.table.column("category_name", width=150)
        self.table.column("current_stock", width=80)
        self.table.column("safety_stock", width=80)
        self.table.column("target_stock", width=80)

        # Pack the Treeview
        self.table.grid(row=1, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

        # Add vertical scrollbar
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.table.yview)
        self.table.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=5, sticky="ns")

        # Quantity field, description field, and stock modification buttons (placed together)
        modify_frame = tk.Frame(self.root)
        modify_frame.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

        tk.Label(modify_frame, text="Quantity:").grid(row=0, column=0, padx=10, pady=10)
        self.quantity_entry = tk.Entry(modify_frame)
        self.quantity_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(modify_frame, text="Description:").grid(row=1, column=0, padx=10, pady=10)
        self.description_entry = tk.Entry(modify_frame, width=50)
        self.description_entry.grid(row=1, column=1, columnspan=3, padx=10, pady=10)

        # Stock modification buttons next to the quantity field
        self.add_stock_button = tk.Button(modify_frame, text="Add Stock", command=self.add_stock)
        self.add_stock_button.grid(row=0, column=2, padx=10, pady=5)

        self.return_from_customer_button = tk.Button(modify_frame, text="Return from Cust.", command=self.return_from_customer)
        self.return_from_customer_button.grid(row=0, column=3, padx=10, pady=5)

        self.return_to_vendor_button = tk.Button(modify_frame, text="Return to Vendor", command=self.return_to_vendor)
        self.return_to_vendor_button.grid(row=0, column=4, padx=10, pady=5)

        # Damaged/Expired removals
        self.damage_expire_button = tk.Button(modify_frame, text="Damaged/Expired Removals", command=self.damage_expire_removal)
        self.damage_expire_button.grid(row=0, column=5, padx=10, pady=5)

        # Radio buttons for damaged/expired
        self.removal_type = tk.StringVar(value="damaged")
        tk.Radiobutton(modify_frame, text="Damaged", variable=self.removal_type, value="damaged").grid(row=1, column=5, padx=10, pady=5)
        tk.Radiobutton(modify_frame, text="Expired", variable=self.removal_type, value="expired").grid(row=2, column=5, padx=10, pady=5)

        # Manual adjustment button and radio buttons for Add/Deduct
        self.manual_adjustment_button = tk.Button(modify_frame, text="Manual Adjustment", command=self.manual_adjustment)
        self.manual_adjustment_button.grid(row=0, column=6, padx=10, pady=5)

        self.adjustment_type = tk.StringVar(value="add")  # Default to 'add'
        tk.Radiobutton(modify_frame, text="Add", variable=self.adjustment_type, value="add").grid(row=1, column=6, padx=10, pady=5)
        tk.Radiobutton(modify_frame, text="Deduct", variable=self.adjustment_type, value="deduct").grid(row=2, column=6, padx=10, pady=5)

        # Fetch and display product data
        self.load_products()

    def create_tables(self):
        """Create the stock_management and stock_transactions tables."""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_management (
            product_id TEXT PRIMARY KEY,
            current_stock INTEGER DEFAULT 0,
            safety_stock INTEGER DEFAULT 0,
            target_stock INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            quantity INTEGER,
            transaction_type TEXT,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            remarks TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        ''')
        self.conn.commit()

    def load_categories(self):
        """Fetch categories from the products table and populate the combobox."""
        self.cursor.execute("SELECT DISTINCT category_name FROM products")
        categories = [row[0] for row in self.cursor.fetchall()]
        categories.insert(0, 'All')  # Insert 'All' option for no filtering
        self.category_combobox['values'] = categories
        self.category_combobox.current(0)  # Set default value to 'All'

    def load_products(self):
        """Fetch data from stock_management and products, calculate stock, and display in the table."""
        # Clear the table
        for row in self.table.get_children():
            self.table.delete(row)

        query = """
        SELECT p.product_id, p.product_name, p.sku, p.category_id, p.category_name,
               s.current_stock, s.safety_stock, s.target_stock
        FROM products p
        LEFT JOIN stock_management s ON p.product_id = s.product_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        # Insert data into the table
        for row in rows:
            self.table.insert("", "end", values=row)

    def search_and_filter_products(self, event):
        """Search and filter products based on user input and selected category."""
        search_term = self.search_entry.get()
        selected_category = self.category_combobox.get()

        # Clear the table
        for row in self.table.get_children():
            self.table.delete(row)

        query = """
        SELECT p.product_id, p.product_name, p.sku, p.category_id, p.category_name,
               s.current_stock, s.safety_stock, s.target_stock
        FROM products p
        LEFT JOIN stock_management s ON p.product_id = s.product_id
        WHERE (p.product_id LIKE ? OR p.product_name LIKE ? OR p.sku LIKE ? OR p.category_name LIKE ?)
        """

        # If a specific category is selected, add it to the WHERE clause
        if selected_category != 'All':
            query += " AND p.category_name = ?"
            self.cursor.execute(query, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', selected_category))
        else:
            self.cursor.execute(query, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))

        rows = self.cursor.fetchall()

        # Insert data into the table
        for row in rows:
            self.table.insert("", "end", values=row)

    def add_stock(self):
        """Add stock to a selected product and update stock_management."""
        product_id = self.get_selected_product_id()
        if not product_id:
            messagebox.showerror("Error", "No product selected")
            return
        
        try:
            quantity = int(self.quantity_entry.get())  # Ensure the quantity is an integer
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero")

            # Check if the product exists in stock_management
            self.cursor.execute("SELECT current_stock FROM stock_management WHERE product_id = ?", (product_id,))
            result = self.cursor.fetchone()

            if result is None:
                # No record exists for this product, insert a new record
                self.cursor.execute("INSERT INTO stock_management (product_id, current_stock) VALUES (?, ?)", (product_id, quantity))
            else:
                # Record exists, update the current stock (handle null current_stock)
                current_stock = result[0] if result[0] is not None else 0
                updated_stock = current_stock + quantity
                self.cursor.execute("UPDATE stock_management SET current_stock = ? WHERE product_id = ?", (updated_stock, product_id))

            # Log the transaction in stock_transactions
            description = self.description_entry.get().strip() or 'Added stock to inventory'
            self.cursor.execute("""
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, 'add stock', ?)
            """, (product_id, quantity, description))

            self.conn.commit()

            # Reload the product list to reflect the updated stock
            self.load_products()
            messagebox.showinfo("Success", "Stock added successfully!")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def return_from_customer(self):
        """Return stock from a customer and update stock_management."""
        product_id = self.get_selected_product_id()
        if not product_id:
            messagebox.showerror("Error", "No product selected")
            return

        try:
            quantity = int(self.quantity_entry.get())  # Ensure the quantity is an integer
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero")

            # Check if the product exists in stock_management
            self.cursor.execute("SELECT current_stock FROM stock_management WHERE product_id = ?", (product_id,))
            result = self.cursor.fetchone()

            if result is None:
                # No record exists for this product, insert a new record
                self.cursor.execute("INSERT INTO stock_management (product_id, current_stock) VALUES (?, ?)", (product_id, quantity))
            else:
                # Record exists, update the current stock (handle null current_stock)
                current_stock = result[0] if result[0] is not None else 0
                updated_stock = current_stock + quantity
                self.cursor.execute("UPDATE stock_management SET current_stock = ? WHERE product_id = ?", (updated_stock, product_id))

            # Log the transaction in stock_transactions
            description = self.description_entry.get().strip() or 'Returned from customer'
            self.cursor.execute("""
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, 'return from customer', ?)
            """, (product_id, quantity, description))

            self.conn.commit()

            # Reload the product list to reflect the updated stock
            self.load_products()
            messagebox.showinfo("Success", "Stock returned from customer successfully!")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def return_to_vendor(self):
        """Deduct stock by returning to vendor and update stock_management."""
        product_id = self.get_selected_product_id()
        if not product_id:
            messagebox.showerror("Error", "No product selected")
            return

        try:
            quantity = int(self.quantity_entry.get())  # Ensure the quantity is an integer
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero")

            # Check if the product exists in stock_management
            self.cursor.execute("SELECT current_stock FROM stock_management WHERE product_id = ?", (product_id,))
            result = self.cursor.fetchone()

            if result is None:
                messagebox.showerror("Error", "Product not found in stock management")
                return
            else:
                current_stock = result[0] if result[0] is not None else 0
                if current_stock < quantity:
                    raise ValueError("Not enough stock to return to vendor")

                updated_stock = current_stock - quantity
                self.cursor.execute("UPDATE stock_management SET current_stock = ? WHERE product_id = ?", (updated_stock, product_id))

            # Log the transaction in stock_transactions
            description = self.description_entry.get().strip() or 'Returned to vendor'
            self.cursor.execute("INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks) VALUES (?, ?, 'return to vendor', ?)", (product_id, -quantity, description))

            self.conn.commit()

            # Reload the product list to reflect the updated stock
            self.load_products()
            messagebox.showinfo("Success", "Stock returned to vendor successfully!")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def damage_expire_removal(self):
        """Remove stock due to damaged or expired goods and update stock_management."""
        product_id = self.get_selected_product_id()
        
        try:
            quantity = int(self.quantity_entry.get())  # Ensure the quantity is an integer
            
            # Fetch the current stock from stock_management
            self.cursor.execute("SELECT current_stock FROM stock_management WHERE product_id = ?", (product_id,))
            result = self.cursor.fetchone()

            if result is None:
                messagebox.showerror("Error", "Product not found in stock management")
                return
            
            current_stock = result[0] if result[0] is not None else 0
            updated_stock = current_stock - quantity
            
            # Deduct the stock in stock_management
            self.cursor.execute("UPDATE stock_management SET current_stock = ? WHERE product_id = ?", (updated_stock, product_id))
            
            # Log the transaction in stock_transactions
            transaction_type = self.removal_type.get()  # Get whether it's 'damaged' or 'expired'
            description = self.description_entry.get().strip() or f'{transaction_type.capitalize()} removal'
            self.cursor.execute("""
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, ?, ?)
            """, (product_id, -quantity, transaction_type, description))

            self.conn.commit()
            
            # Reload the product list to reflect the updated stock
            self.load_products()
            messagebox.showinfo("Success", f"Stock {transaction_type} removal successful!")
            
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def manual_adjustment(self):
        """Adjust stock based on manual entry and update stock_management."""
        product_id = self.get_selected_product_id()
        
        try:
            quantity = int(self.quantity_entry.get())  # Ensure the quantity is an integer

            # Fetch the current stock from stock_management
            self.cursor.execute("SELECT current_stock FROM stock_management WHERE product_id = ?", (product_id,))
            result = self.cursor.fetchone()

            if result is None:
                messagebox.showerror("Error", "Product not found in stock management")
                return
            
            current_stock = result[0] if result[0] is not None else 0
            
            # Determine whether to add or deduct stock based on user selection
            if self.adjustment_type.get() == "add":
                updated_stock = current_stock + quantity
                transaction_type = "manual add"
            else:  # "deduct"
                updated_stock = current_stock - quantity
                transaction_type = "manual deduct"

            # Update the stock in stock_management
            self.cursor.execute("UPDATE stock_management SET current_stock = ? WHERE product_id = ?", (updated_stock, product_id))

            # Log the transaction in stock_transactions
            description = self.description_entry.get().strip() or f'{transaction_type.capitalize()} adjustment'
            self.cursor.execute("""
                INSERT INTO stock_transactions (product_id, quantity, transaction_type, remarks)
                VALUES (?, ?, ?, ?)
            """, (product_id, quantity if self.adjustment_type.get() == "add" else -quantity, transaction_type, description))

            self.conn.commit()

            # Reload the product list to reflect the updated stock
            self.load_products()
            messagebox.showinfo("Success", f"Stock {transaction_type} successful!")
            
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_selected_product_id(self):
        """Helper function to get the selected product's ID from the table."""
        selected = self.table.focus()
        if selected:
            return self.table.item(selected)['values'][0]
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryManagementApp(root)
    root.mainloop()