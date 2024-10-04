import tkinter as tk
import os
import subprocess

# Function to load Product Category Management
def load_product_category_management():
    app_path = 'main-PRODUCT CATEGORY MGNT.py'  # No need for full path if it's in the same folder
    subprocess.Popen(['python', app_path])

# Function to load Product Management
def load_product_management():
    app_path = 'PRODUCT MANAGEMENT.py'  # No need for full path if it's in the same folder
    subprocess.Popen(['python', app_path])

# Create main app window
root = tk.Tk()
root.title('Main Application')
root.geometry('300x200')

# Create buttons for loading the apps
btn_category_management = tk.Button(root, text="Product Category Management", command=load_product_category_management)
btn_category_management.pack(pady=20)

btn_product_management = tk.Button(root, text="Product Management", command=load_product_management)
btn_product_management.pack(pady=20)

# Start the main loop
root.mainloop()
