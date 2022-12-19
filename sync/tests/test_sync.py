from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    #def setUp(self):
    #    super(TestModuleDemo, self).setUp()
            
    def test_is_psw_empty(self):
        synce_model = self.env['sync.sync']

        result = synce_model.is_psw_empty(None)
        self.assertEqual(result, True)

        result = synce_model.is_psw_empty("password")
        self.assertEqual(result, True)
        
           