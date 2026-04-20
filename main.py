import pandas as pd
from datetime import datetime

print("============================================================\n=============PYTHON BAKERY MANAGEMENT SYSTEM================\n============================================================")
# Order Management System
class BakeryOrderManagement:
    def __init__(self):
        self.orders = pd.DataFrame(columns=["Customer Name", "Item", "Quantity", "Price", "Order Date"])

    def add_order(self):
        customer_name = input("Enter customer name: ")
        item = input("Enter item ordered: ")
        quantity = int(input("Enter quantity: "))
        price = int(input("Enter Price: ₹"))
        order_date = datetime.now().strftime("%Y-%m-%d")
        new_order = pd.DataFrame([[customer_name, item, quantity, price, order_date]], 
                                 columns=["Customer Name", "Item", "Quantity", "Price", "Order Date"])
        self.orders = pd.concat([self.orders, new_order], ignore_index=True)
        print("=====Order added successfully!=====")

    def view_orders(self):
        if self.orders.empty:
            print("=====No orders available.=====")
        else:
            print(self.orders)

    def update_order(self):
        order_id = int(input("Enter order ID to update: "))
        if order_id >= len(self.orders):
            print("Order not found.")
        else:
            print("Updating Order ID:", order_id)
            self.orders.at[order_id, "Item"] = input("Enter new item: ")
            self.orders.at[order_id, "Quantity"] = int(input("Enter new quantity: "))
            self.orders.at[order_id, "Price"] = int(input("Enter new price: ₹"))
            print("=====Order updated successfully!====")

    def save_to_excel(self):
        self.orders.to_excel("bakery_orders.xlsx", index=False)
        print("Orders saved to 'bakery_orders.xlsx'.")

# Using the system
order_system = BakeryOrderManagement()

while True:
    print("\n1. Add Order\n2. View Orders\n3. Update Order\n4. Save to Excel\n5. Exit")
    choice = input("Enter your choice: ")

    if choice == '1':
        order_system.add_order()
    elif choice == '2':
        order_system.view_orders()
    elif choice == '3':
        order_system.update_order()
    elif choice == '4':
        order_system.save_to_excel()
    elif choice == '5':
        break
    else:
        print("Invalid choice. Please try again.")
