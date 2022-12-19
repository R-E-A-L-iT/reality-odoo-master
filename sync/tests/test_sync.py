from odoo.tests import TransactionCase
#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    def test_that_pass(self):
            self.assertEqual("AAA", "AAA")
            print('test_that_pass: Your test was successful!')

    def test_that_fail(self):
            self.assertEqual("AAA", "BBB")
            print('test_that_fail: Your test was successful!')            