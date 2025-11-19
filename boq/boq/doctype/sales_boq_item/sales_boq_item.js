frappe.ui.form.on('Sales BOQ Item', {
    item_category: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        frm.fields_dict['items'].grid.get_field('item_code').get_query = function(doc, cdt2, cdn2) {
            let child = locals[cdt2][cdn2];
            return {
                query: "boq.boq.doctype.sales_boq_item.get_filtered_items",
                filters: { item_category: child.item_category }
            };
        };
    }
});
