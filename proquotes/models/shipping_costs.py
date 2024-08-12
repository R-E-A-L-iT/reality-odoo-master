import logging
import binascii
import datetime
import sys

from odoo import models, fields

# import fedex_python as fedex
# from fedex_python import FedexConfig


import importlib  
fedex = importlib.import_module("fedex_python")

# from . import fedex_config
# from fedex.services.ship_service import FedexProcessShipmentRequest
# from fedex.tools.conversion import sobject_to_dict

# https://github.com/python-fedex-devs/python-fedex examples

_logger = logging.getLogger(__name__)


# client = fedex.Client(
#     key, password, account_number, meter_number,
#     localization=(
#         fedex.components.auth.Localization.get(
#             fedex.components.auth.Localization.SPANISH_LATINOAMERICAN
#         )
#     ),
#     test_mode=True
# )


class shipping_costs(models.Model):
    _name = "proquotes.shipping_costs"
    
    if (fedex):
        _logger.info("fedex module loaded properly")
    else:
        _logger.error("no fedex module found")
    
    # name of package
    package_name = fields.Char("Package Name")
    # item in package
    items = fields.Many2many("product.product", string="Items")
    # warehouse location
    warehouse_location = fields.Many2one("stock.warehouse", string="Warehouse Location")
    # delivery location
    delivery_location = fields.Many2one("res.partner", string="Delivery Location")
    
    
    # debug
    
    _logger.info("SYSTEM PATH: " + str(sys.path))
    print(sys.path)
    
    # _logger.info(self.env["shipping_costs.items"])
    
    
    #   config builder
    
    FEDEX_CONFIG = FedexConfig(key='',
                               password='',
                               account_number='',
                               meter_number='',
                               freight_account_number='',
                               use_test_server=True)
    
    #
    #   items in package: list of odoo product objects
    #   start_address: odoo contact object of r-e-a-l.it address it's shipped from
    #   finish_address: odoo contact object of customer's address it's shipped to
    #   units: string "KG" or "LB" only
    #
    
    def getShipmentRate(items_in_package, start_address, finish_address, units):
        
        rate_request = FedexRateServiceRequest(fedex_config.FEDEX_CREDENTIALS)
        
        # settings
        rate_request.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
        rate_request.RequestedShipment.ServiceType = 'FEDEX_GROUND'
        # not fedex box because we package it
        rate_request.RequestedShipment.PackagingType = 'YOUR_PACKAGING'
        
        # warehouse address
        state_id = start_address.state_id
        country_id = start_address.country_id
        postal_code = start_address.zip
        
        rate_request.RequestedShipment.Shipper.Address.StateOrProvinceCode = state_id
        rate_request.RequestedShipment.Shipper.Address.PostalCode = postal_code
        rate_request.RequestedShipment.Shipper.Address.CountryCode = country_id
        # might need to make this configurable
        rate_request.RequestedShipment.Shipper.Address.Residential = False
        
        # delivery address
        state_id = finish_address.state_id
        country_id = finish_address.country_id
        postal_code = finish_address.zip
        
        rate_request.RequestedShipment.Recipient.Address.StateOrProvinceCode = state_id
        rate_request.RequestedShipment.Recipient.Address.PostalCode = postal_code
        rate_request.RequestedShipment.Recipient.Address.CountryCode = country_id
        # This is needed to ensure an accurate rate quote with the response.
        # rate_request.RequestedShipment.Recipient.Address.Residential = True
        # include estimated duties and taxes in rate quote, can be ALL or NONE  
        rate_request.RequestedShipment.EdtRequestType = 'NONE'
        
        rate_request.RequestedShipment.ShippingChargesPayment.PaymentType = 'RECIPIENT'
        
        packageWeight = 0
        
        for item in items_in_package:
            
            packageWeight += item.weight
            
        fedex_weight = rate_request.create_wsdl_object_of_type('Weight')
        fedex_weight.Value = packageWeight
        fedex_weight.Units = units
        
        package = rate_request.create_wsdl_object_of_type('RequestedPackageLineItem')
        package.Weight = fedex_weight
        
        package1.PhysicalPackaging = 'BOX'
        
        # Required, but according to FedEx docs:
        # "Used only with PACKAGE_GROUPS, as a count of packages within a
        # group of identical packages". In practice you can use this to get rates
        # for a shipment with multiple packages of an identical package size/weight
        # on rate request without creating multiple RequestedPackageLineItem elements.
        # You can OPTIONALLY specify a package group:
        # package1.GroupNumber = 0  # default is 0
        # The result will be found in RatedPackageDetail, with specified GroupNumber.
        package1.GroupPackageCount = 1
        # Un-comment this to see the other variables you may set on a package.
        # print(package1)
        
        rate_request.add_package(package)
        rate_request.send_request()
        
        rate = rate_request.response
        
        # This will show the reply to your rate_request being sent. You can access the
        # attributes through the response attribute on the request object. This is
        # good to un-comment to see the variables returned by the FedEx reply.
        # print(rate_request.response)

        # This will convert the response to a python dict object. To
        # make it easier to work with.
        # from fedex.tools.conversion import basic_sobject_to_dict
        # print(basic_sobject_to_dict(rate_request.response))

        # This will dump the response data dict to json.
        # from fedex.tools.conversion import sobject_to_json
        # print(sobject_to_json(rate_request.response))
        
        return rate
    
    def createShipment(weights, start_address, finish_address):
        return
    
    
    # _columns = {
    #     'package_name': fields.Char("Package Name"),
    #     'items': fields.Many2one("product.product", string="Items"),
    #     'warehouse_location': fields.Many2one("stock.warehouse", string="Warehouse Location"),
    #     'delivery_location': fields.Many2one("res.partner", string="Delivery Location"),
    # }

    # get rate button [todo]