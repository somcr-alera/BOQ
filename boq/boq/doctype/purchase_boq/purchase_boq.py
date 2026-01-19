# purchase_boq.py (Server-side)

import frappe
from frappe import _
from frappe.model.document import Document

class PurchaseBOQ(Document):
    def autoname(self):
        if not self.sales_boq:
            frappe.throw("Technical Offer is required to name Purchase BOQ")

        # Base name for Purchase BOQ
        base = f"{self.sales_boq}-PB"

        # ------------------------------------------------
        # CASE 1: NEW BASE DOCUMENT (REVISION 0)
        # ------------------------------------------------
        if not self.base_document:
            self.name = base
            self.base_document = base
            self.revision = 0
            self.previous_version = None
            self.is_latest = 1
            return

        # ------------------------------------------------
        # CASE 2: CREATE REVISION (R1, R2, ...)
        # ------------------------------------------------
        max_revision = frappe.db.get_value(
            self.doctype,
            {"base_document": self.base_document},
            "MAX(revision)"
        ) or 0

        next_revision = max_revision + 1

        self.name = f"{self.base_document}-R{next_revision}"
        self.revision = next_revision
        self.is_latest = 1

        self.previous_version = frappe.db.get_value(
            self.doctype,
            {"base_document": self.base_document, "revision": max_revision},
            "name"
        )

        frappe.db.set_value(
            self.doctype,
            {"base_document": self.base_document},
            "is_latest",
            0,
            update_modified=False
        )
    # def autoname(self):
    #     """Generate name from Sales BOQ by replacing -S with -P"""
    #     if self.sales_boq:
    #         # Replace -S with -P in the sales BOQ name
    #         self.name = f"{self.sales_boq}-P"
    #     else:
    #         frappe.throw(_("Technical Offer is required to generate Purchase BOQ name"))
    
    def validate(self):
        """Calculate totals on save"""
        self.calculate_item_totals()
        self.calculate_service_totals()
        self.calculate_grand_total()
    
    def calculate_item_totals(self):
        """Calculate amounts for all items"""
        item_total = 0
        
        for item in self.items:
            qty = item.qyt or 0
            rate = item.rate or 0
            discount = item.discount or 0
            
            amount = qty * rate
            discount_amount = amount * (discount / 100)
            final_amount = amount + discount_amount
            
            item.amount = amount
            item.discount_amount = discount_amount
            item.final_amount = final_amount
            
            item_total += final_amount
        
        self.item_total = item_total
    
    def calculate_service_totals(self):
        """Calculate amounts for all services"""
        service_total = 0
        
        for service in self.services:
            cost = service.service_cost or 0
            discount = service.discount or 0
            
            discount_amount = cost * (discount / 100)
            final_amount = cost + discount_amount
            
            service.amount = cost
            service.discount_amount = discount_amount
            service.final_amount = final_amount
            
            service_total += final_amount
        
        self.services_total = service_total
    
    def calculate_grand_total(self):
        """Calculate grand total"""
        self.grand_total = (self.item_total or 0) + (self.services_total or 0)


@frappe.whitelist()
def get_sales_boq_data(sales_boq):
    """Fetch Sales BOQ data with stock and rate information"""
    if not sales_boq:
        return None
    
    doc = frappe.get_doc("Technical Offer", sales_boq)
    
    items = []
    services = []
    
    # Process items with stock data and rates
    for src_item in doc.items or []:
        item = {
            "item_category": src_item.item_category,
            "item_code": src_item.item_code,
            "item_name": src_item.item_name,
            "qyt": src_item.qyt or 0,
            "uom": src_item.uom,
            "discount": 0
        }
        
        # Get standard rate from Item master
        if src_item.item_code:
            rate = get_item_rate(src_item.item_code)
            item["rate"] = rate
            item["amount"] = (src_item.qyt or 0) * rate
            
            # Get stock quantity
            stock_qty = get_item_stock(src_item.item_code)
            item["current_stock"] = stock_qty
        else:
            item["rate"] = 0
            item["amount"] = 0
            item["current_stock"] = 0
        
        items.append(item)
    
    # Process services
    for src_service in doc.services or []:
        service = {
            "service_code": src_service.service_code,
            "service_name": src_service.service_name,
            "description": src_service.description
        }
        services.append(service)
    
    return {
        "opportunity": doc.get("opportunity"),
        "opportunity_from": doc.get("opportunity_from"),
        "party": doc.get("party"),
        "items": items,
        "services": services
    }


def get_item_rate(item_code):
    """Get standard rate from Item master"""
    item = frappe.get_value("Item", item_code, "standard_rate")
    return item or 0


def get_item_stock(item_code):
    """Get total stock for an item across all warehouses"""
    bins = frappe.get_all(
        "Bin",
        filters={"item_code": item_code},
        fields=["actual_qty"]
    )
    
    total_stock = sum(bin.actual_qty or 0 for bin in bins)
    return total_stock


@frappe.whitelist()
def validate_stock_availability(doc, method=None):
    """Hook to validate stock before submission"""
    if isinstance(doc, str):
        doc = frappe.get_doc(frappe.parse_json(doc))
    
    low_stock_items = []
    
    for item in doc.items or []:
        if item.current_stock < item.qyt:
            low_stock_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "required": item.qyt,
                "available": item.current_stock
            })
    
    if low_stock_items:
        message = _("Following items have insufficient stock:\n")
        for item in low_stock_items:
            message += f"\n• {item['item_name']}: Required {item['required']}, Available {item['available']}"
        
        frappe.msgprint(message, indicator="orange", title=_("Low Stock Warning"))


@frappe.whitelist()
def check_final_boq_exists(purchase_boq):
    """Check if Final BOQ already exists for this Purchase BOQ"""
    existing = frappe.get_all(
        "Commercial Offer",
        filters={"purchase_boq": purchase_boq},
        fields=["name"],
        limit=1
    )
    
    if existing:
        return {"exists": True, "name": existing[0].name}
    return {"exists": False}