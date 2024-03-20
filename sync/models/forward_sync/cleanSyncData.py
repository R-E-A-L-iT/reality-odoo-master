import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)


class cleanSyncData:
    def __init__(self):
        _logger.info("cleanSync ")

    #Methode to clean spl with no owner
    def cleanSPL(self): 
        sq = self.env["stock.quant"]  
        spl = self.env["stock.production.lot"]
        spls = spl.search([])

        for spl_ in spls: 
            s1 = str(spl_.id).ljust(10) 
            s2 = str(spl_.display_name).ljust(40)             
            s3 = str(spl_.sku).ljust(40) 
            slast = str(spl_.owner.name)             
            sf = s1 + s2 + s3 + slast             
            _logger.info (sf) 
            if (slast == "False"): 
                sq_ = sq.search([("lot_id.id", "=", spl_.id)])
                print(sq_)
                for sq1 in sq_:
                    sq1.unlink()
                spl_.unlink() 