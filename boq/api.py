# import frappe

# @frappe.whitelist()
# def get_sales_boq_data(sales_boq):
#     doc = frappe.get_doc("Sales BOQ", sales_boq)
#     return {
#         "items": doc.items,
#         "services": doc.services
#     }

import frappe

@frappe.whitelist()
def get_sales_boq_data(sales_boq):
    """Return Sales BOQ items, services, and current stock for each item."""
    doc = frappe.get_doc("Sales BOQ", sales_boq)

    items_with_stock = []
    for item in doc.items:
        # Default stock
        stock_qty = 0
        warehouse_stock = []

        # Fetch from Bin table
        bins = frappe.get_all(
            "Bin",
            filters={"item_code": item.item_code},
            fields=["warehouse", "actual_qty"]
        )

        if bins:
            warehouse_stock = bins
            stock_qty = sum(b.actual_qty for b in bins)
            

        # Add stock data to each item row
        items_with_stock.append({
            **item.as_dict(),
            "current_stock": stock_qty,
            "warehouse_stock": warehouse_stock
        })
    frappe.msgprint(items_with_stock)
    return {
        "items": items_with_stock,
        "services": doc.services
    }
