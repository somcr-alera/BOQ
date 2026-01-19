// Copyright (c) 2025, Som and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Commercial Offer", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Commercial Offer', {
    onload(frm) {
        hide_child_fields_for_sales_user(frm);
    },
    refresh(frm) {
        hide_child_fields_for_sales_user(frm);
    }
});

function hide_child_fields_for_sales_user(frm) {
    // Only Sales User
    if (!frappe.user_roles.includes("Sales User") && frappe.user_roles.includes("Administrator") || frappe.user_roles.includes("System Manager")) return;

    const hidden_fields = [
        "rate",
        "discount"
    ];

    const child_table = "items";            // fieldname in parent
    const child_doctype = "Purchase BOQ Item"; // child doctype

    hidden_fields.forEach(field => {
        frm.fields_dict[child_table].grid.update_docfield_property(
            field,
            "hidden",
            1
        );
    });

    frm.refresh_field(child_table);
}

