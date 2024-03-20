
import logging
_logger = logging.getLogger(__name__)


class cleanSyncData:
    def __init__(self, database):
        _logger.info("cleanSyncData.__init__")
        self.database = database


    #methot to clean SPL with no owner
    def cleanSPLNoOwner(self):
        _logger.info("clean SPL------------------------------------------")
        sq = self.env.database["stock.quant"]  
        spl = self.env.database["stock.production.lot"]
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
                
                for sq1 in sq_:
                    _logger.info("deleting sq: " + str(sq1.name))
                    sq1.unlink()
                spl_.unlink() 


        