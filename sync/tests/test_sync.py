#from odoo.tests.common import TransactionCase
#from odoo.tests import tagged

import unittest
import logging

_logger = logging.getLogger(__name__)

# The CI will run these tests after all the modules are installed,
# not right after installing the one defining it.
#@tagged('standard') 
#class StandardTestCase(TransactionCase):

class TestStringMethods(unittest.TestCase):
    def test_01(self):
       _logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! test_01")
       self.assertEqual('foo'.upper(), 'FOO') 

    def test_02(self):
       _logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! test_02")
       self.assertEqual('bar'.upper(), 'FOO')        

if __name__ == '__main__':
    unittest.main()
