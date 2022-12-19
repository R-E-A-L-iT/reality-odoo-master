from odoo.tests.common import TransactionCase
from odoo.tests import tagged

# The CI will run these tests after all the modules are installed,
# not right after installing the one defining it.
@tagged('post_install', '-at_install')  # add `post_install` and remove `at_install`
class PostInstallTestCase(TransactionCase):
    def test_01(self):
       self.assertEqual('foo'.upper(), 'FOO') 

    def test_02(self):
       self.assertEqual('bar'.upper(), 'FOO')        