from odoo.tests import TransactionCase
from odoo.addons.sync import sync

#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    def test_that_pass(self):
        self.assertEqual("AAA", "AAA")
        print('test_that_pass: Your test was successful!')
            
    def test_is_psw_empty(self):
        s = sync()
        print (s._name)
        self.assertEqual("AAA", "AAA")
        print('test_is_psw_empty: Your test was successful!')
           