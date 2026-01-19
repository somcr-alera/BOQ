# Copyright (c) 2025, Som and contributors
# For license information, please see license.txts

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, add_days
class CommercialOffer(Document):
    def autoname(self):
        if not self.purchase_boq:
            frappe.throw("Purchase BOQ is required to generate Commercial Offer name")

        # Base name for Purchase BOQ
        base = f"{self.purchase_boq}-CO"

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
    #     """Generate name from Purchase BOQ by replacing -P with -F"""
    #     if self.purchase_boq:
    #         # Replace -P with -F in the purchase BOQ name
    #         self.name = self.purchase_boq.replace("-P", "-F")
    #     else:
    #         frappe.throw(_("Purchase BOQ is required to generate Commercial Offer name"))
    
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
            
            item.amount = final_amount
            item.discount_amount = discount_amount
            
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
            
            service.amount = final_amount
            service.discount_amount = discount_amount
            
            service_total += final_amount
        
        self.services_total = service_total
    
    def calculate_grand_total(self):
        """Calculate grand total"""
        self.grand_total = (self.item_total or 0) + (self.services_total or 0)
        

@frappe.whitelist()
def make_sales_order(commercial_offer):
    import frappe
    from frappe.utils import flt

    offer = frappe.get_doc("Commercial Offer", commercial_offer)

    so = frappe.new_doc("Sales Order")

    # ------------------------
    # HEADER
    # ------------------------
    so.customer = offer.customer_link
    so.opportunity = offer.opportunity
    so.ignore_pricing_rule = 1
    so.delivery_date= add_days(today(), 7) 
    # ✅ REQUIRED PRICE LIST CONTEXT
    so.selling_price_list = frappe.db.get_single_value(
        "Selling Settings", "selling_price_list"
    )

    if not so.selling_price_list:
        frappe.throw("Default Selling Price List is not set")

    # Fetch price list currency
    price_list_currency = frappe.db.get_value(
        "Price List",
        so.selling_price_list,
        "currency"
    )

    so.price_list_currency = price_list_currency

    # Company currency
    company_currency = frappe.get_cached_value(
        "Company", so.company, "default_currency"
    )

    # ------------------------
    # EXCHANGE RATE
    # ------------------------
    if price_list_currency == company_currency:
        so.plc_conversion_rate = 1
        so.conversion_rate = 1
    else:
        so.plc_conversion_rate = flt(
            frappe.get_value(
                "Currency Exchange",
                {
                    "from_currency": price_list_currency,
                    "to_currency": company_currency
                },
                "exchange_rate"
            )
        ) or 1

        so.conversion_rate = so.plc_conversion_rate

    # ------------------------
    # ITEMS (LOCK RATE)
    # ------------------------
    for item in offer.items:
        final_rate = flt(item.rate or 0) * (flt(item.discount or 0) + 100) / 100
        so.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom,
            "qty": flt(item.qyt or 1),
            "rate": final_rate,
            "price_list_rate": final_rate,
            
        })

    # ------------------------
    # FINALIZE
    # ------------------------
    so.set_missing_values(for_validate=False)
    so.calculate_taxes_and_totals()

    so.insert()
    frappe.db.commit()

    return so.name       




@frappe.whitelist()
def get_purchase_boq_data(purchase_boq):
    """Fetch Purchase BOQ data with stock information"""
    if not purchase_boq:
        return None
    
    doc = frappe.get_doc("Purchase BOQ", purchase_boq)
    
    items = []
    services = []
    
    # Process items with stock data
    for src_item in doc.items or []:
        item = {
            "item_code": src_item.item_code,
            "item_name": src_item.item_name,
            "qyt": src_item.qyt or 0,
            "rate": src_item.rate or 0,
            "discount": 0,
            "amount": (src_item.qyt or 0) * (src_item.rate or 0)
        }
        
        # Get stock quantity
        if src_item.item_code:
            stock_qty = get_item_stock(src_item.item_code)
            item["current_stock"] = stock_qty
        
        items.append(item)
    
    # Process services
    for src_service in doc.services or []:
        service = {
            "service_code": src_service.service_code,
            "service_name": src_service.service_name,
            "description": src_service.description,
            "service_cost": src_service.service_cost or 0,
            "discount": 0,
            "amount": src_service.service_cost or 0
        }
        services.append(service)
    
    return {
        "opportunity": doc.get("opportunity"),
        "opportunity_from": doc.get("opportunity_from"),
        "party": doc.get("party"),
        "items": items,
        "services": services
    }


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