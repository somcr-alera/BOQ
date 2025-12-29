# technical_offer.py (Server-side)

import frappe
from frappe import _
from frappe.model.document import Document

class TechnicalOffer(Document):
    pass


@frappe.whitelist()
def get_short_forms_data(field_type):
    """Fetch all short forms for MOC or Make"""
    
    # Get all Short Forms parent documents
    parents = frappe.get_all(
        "Short Forms",
        filters={"field_name": field_type},
        fields=["name"],
        limit_page_length=500
    )
    
    if not parents:
        return []
    
    collected = []
    
    # Get child table data from each parent
    for parent in parents:
        doc = frappe.get_doc("Short Forms", parent.name)
        
        # Loop through all fields in the document
        for key, value in doc.as_dict().items():
            if isinstance(value, list):
                # It's a child table
                for row in value:
                    if isinstance(row, dict) and row.get("name1"):
                        collected.append(row.get("name1"))
    
    # Return unique sorted list
    return sorted(list(set(collected)))


@frappe.whitelist()
def get_filtered_items(filters):
    """Get filtered items based on search criteria"""
    
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    
    query_filters = {}
    
    if filters.get("search_item_group"):
        query_filters["item_group"] = filters["search_item_group"]
    
    if filters.get("search_item_name"):
        query_filters["item_name"] = ["like", f"%{filters['search_item_name']}%"]
    
    if filters.get("search_moc"):
        query_filters["custom_moc"] = ["like", f"%{filters['search_moc']}%"]
    
    if filters.get("search_make"):
        query_filters["custom_make"] = ["like", f"%{filters['search_make']}%"]
    
    if filters.get("search_size"):
        query_filters["custom_size"] = ["like", f"%{filters['search_size']}%"]
    
    if filters.get("search_end_connection"):
        query_filters["custom_end_connection"] = ["like", f"%{filters['search_end_connection']}%"]
    
    items = frappe.get_all(
        "Item",
        filters=query_filters,
        fields=["name", "item_name", "item_group", "custom_moc", "custom_make", "custom_size", "custom_end_connection"],
        limit_page_length=100
    )
    
    return items


@frappe.whitelist()
def check_purchase_boq_exists(technical_offer):
    """Check if Purchase BOQ already exists for this Sales BOQ"""
    
    existing = frappe.get_all(
        "Purchase BOQ",
        filters={"technical_offer": technical_offer},
        fields=["name"],
        limit=1
    )
    
    if existing:
        return {"exists": True, "name": existing[0].name}
    return {"exists": False}


@frappe.whitelist()
def create_purchase_boq(technical_offer):
    """Create Purchase BOQ from Sales BOQ"""
    
    # Check if already exists
    check = check_purchase_boq_exists(technical_offer)
    if check["exists"]:
        return {"success": False, "message": "Purchase BOQ already exists", "name": check["name"]}
    
    try:
        # Create new Purchase BOQ
        purchase_boq = frappe.get_doc({
            "doctype": "Purchase BOQ",
            "technical_offer": technical_offer
        })
        
        purchase_boq.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Purchase BOQ created successfully",
            "name": purchase_boq.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Purchase BOQ Creation Failed"))
        return {
            "success": False,
            "message": str(e)
        }