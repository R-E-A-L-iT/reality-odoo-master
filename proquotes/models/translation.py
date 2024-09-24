
# Class to get the translation name.  
# Input:
class name_translation:

    def __init__(self, data): 
        self.data = data    

    def get_applied_name(self):
        return True
        #iterate all records
        # for record in self.data:
        #     #get the id for the applied name
        #     id = self.data.env['ir.translation'].search([('value', '=', record.product_id.name),
        #                                             ('name', '=', 'product.template,name')])
        #     if (len(id) > 1):
        #         id = id[-1]
        #     names = self.data.env['ir.translation'].search([('res_id', '=', id.res_id),
        #                                                 ('name', '=',
        #                                                 'product.template,name'),
        #                                                 ('lang', '=', self.data.order_partner_id.lang)])
        #     #get the value of the applied name
        #     if (len(names) > 1):
        #         name = names[-1].value
        #     else:
        #         name = names.value
        #
        #     #Set the applied_name
        #     if (name == False or name == ""):
        #         record.applied_name = record.product_id.name
        #     else:
        #         record.applied_name = name