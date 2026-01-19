# technical_offer.py (Server-side)

import frappe
from frappe import _
from frappe.model.document import Document

# class TechnicalOffer(Document):
#     def autoname(self):
#         # NEW BASE DOCUMENT (R0)
#         if not self.previous_version and not self.base_document:
#             base = frappe.model.naming.make_autoname(
#                 "CSPL-.YY.####.-.DD.-.MM."
#             )
#             self.revision = 0
#             self.name = f"{base}"
#             self.base_document = self.name
#             self.is_latest = 1
#         elif not self.previous_version and self.base_document:
#             base = frappe.get_doc(self.doctype, self.base_document)
#             self.name = f"{self.base_document}-R{self.revision}"
#             self.revision = base.revision + 1
#             self.previous_version=self.base_document
#             self.is_latest=1
#             frappe.db.set_value(self.doctype,base.name,"is_latest",0)
#         else:
#             prev = frappe.get_doc(self.doctype, self.previous_version)
#             self.revision = prev.revision + 1
#             self.base_document = prev.base_document
#             self.name = f"{self.base_document}-R{self.revision}"
#             frappe.db.set_value(self.doctype,prev.name,"is_latest",0)
#     # def before_save(self):
#     #     if not self.is_latest:
#     #         frappe.throw(_("This revision is locked"))

#     # def before_insert(self):
#     #     self.is_latest = 1


class TechnicalOffer(Document):

    def autoname(self):

        # ------------------------------------------------
        # CASE 1: NEW BASE DOCUMENT (REVISION 0)
        # ------------------------------------------------
        if not self.previous_version and not self.base_document:
            base = frappe.model.naming.make_autoname(
                "CSPL-.YY.####./.DD./.MM."
            )

            self.name = base                # ❗ NO -R0
            self.base_document = base
            self.revision = 0
            self.previous_version = None
            self.is_latest = 1
            return

        # ------------------------------------------------
        # CASE 2: FIRST REVISION (R1)
        # ------------------------------------------------
        if not self.previous_version and self.base_document:
            base = frappe.get_doc(self.doctype, self.base_document)

            self.revision = base.revision + 1
            self.name = f"{self.base_document}-R{self.revision}"
            self.previous_version = base.name
            self.is_latest = 1

            frappe.db.set_value(
                self.doctype,
                base.name,
                "is_latest",
                0
            )
            return

        # ------------------------------------------------
        # CASE 3: NEXT REVISIONS (R2, R3, ...)
        # ------------------------------------------------
        prev = frappe.get_doc(self.doctype, self.previous_version)

        self.revision = prev.revision + 1
        self.base_document = prev.base_document
        self.name = f"{self.base_document}-R{self.revision}"
        self.is_latest = 1

        frappe.db.set_value(
            self.doctype,
            prev.name,
            "is_latest",
            0
        )

@frappe.whitelist()
def create_new_revision(docname):
    old = frappe.get_doc("Technical Offer", docname)

    if not old.is_latest:
        frappe.throw(_("Only latest revision can be revised"))
        
    old.db_set("is_latest", 0)

    new = frappe.copy_doc(old)
    new.previous_version = old.name
    new.docstatus = 0
    new.amended_from = None

    new.insert(ignore_permissions=True)

    return new.name

# @frappe.whitelist()
# def get_short_forms_data(field_type):
#     """Fetch all short forms for MOC or Make"""
    
#     # Get all Short Forms parent documents
#     parents = frappe.get_all(
#         "Short Forms",
#         filters={"field_name": field_type},
#         fields=["name"],
#         limit_page_length=500
#     )
    
#     if not parents:
#         return []
    
#     collected = []
    
#     # Get child table data from each parent
#     for parent in parents:
#         doc = frappe.get_doc("Short Forms", parent.name)
        
#         # Loop through all fields in the document
#         for key, value in doc.as_dict().items():
#             if isinstance(value, list):
#                 # It's a child table
#                 for row in value:
#                     if isinstance(row, dict) and row.get("name1"):
#                         collected.append(row.get("name1"))
    
#     # Return unique sorted list
#     return sorted(list(set(collected)))


# @frappe.whitelist()
# def get_filtered_items(filters):
#     """Get filtered items based on search criteria"""
    
#     if isinstance(filters, str):
#         import json
#         filters = json.loads(filters)
    
#     query_filters = {}
    
#     if filters.get("search_item_group"):
#         query_filters["item_group"] = filters["search_item_group"]
    
#     if filters.get("search_item_name"):
#         query_filters["item_name"] = ["like", f"%{filters['search_item_name']}%"]
    
#     if filters.get("search_moc"):
#         query_filters["custom_moc"] = ["like", f"%{filters['search_moc']}%"]
    
#     if filters.get("search_make"):
#         query_filters["custom_make"] = ["like", f"%{filters['search_make']}%"]
    
#     if filters.get("search_size"):
#         query_filters["custom_size"] = ["like", f"%{filters['search_size']}%"]
    
#     if filters.get("search_end_connection"):
#         query_filters["custom_end_connection"] = ["like", f"%{filters['search_end_connection']}%"]
    
#     items = frappe.get_all(
#         "Item",
#         filters=query_filters,
#         fields=["name", "item_name", "item_group", "custom_moc", "custom_make", "custom_size", "custom_end_connection"],
#         limit_page_length=100
#     )
    
#     return items


# @frappe.whitelist()
# def check_purchase_boq_exists(technical_offer):
#     """Check if Purchase BOQ already exists for this Sales BOQ"""
    
#     existing = frappe.get_all(
#         "Purchase BOQ",
#         filters={"technical_offer": technical_offer},
#         fields=["name"],
#         limit=1
#     )
    
#     if existing:
#         return {"exists": True, "name": existing[0].name}
#     return {"exists": False}


# @frappe.whitelist()
# def create_purchase_boq(technical_offer):
#     """Create Purchase BOQ from Sales BOQ"""
    
#     # Check if already exists
#     check = check_purchase_boq_exists(technical_offer)
#     if check["exists"]:
#         return {"success": False, "message": "Purchase BOQ already exists", "name": check["name"]}
    
#     try:
#         # Create new Purchase BOQ
#         purchase_boq = frappe.get_doc({
#             "doctype": "Purchase BOQ",
#             "technical_offer": technical_offer
#         })
        
#         purchase_boq.insert(ignore_permissions=True)
#         frappe.db.commit()
        
#         return {
#             "success": True,
#             "message": "Purchase BOQ created successfully",
#             "name": purchase_boq.name
#         }
        
#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), _("Purchase BOQ Creation Failed"))
#         return {
#             "success": False,
#             "message": str(e)
#         }