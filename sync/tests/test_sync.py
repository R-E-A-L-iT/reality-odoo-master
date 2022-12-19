from odoo.tests import TransactionCase
#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    def test_some_action(self):
            self.assertEqual("AAA", "AAA")
            #self.assertEqual("AAA", "BBB")
            print('Your test was successful!')