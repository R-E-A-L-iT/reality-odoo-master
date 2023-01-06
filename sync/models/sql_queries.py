import logging

_logger = logging.getLogger(__name__)

class sql_queries:

    def __init__(self, db):
        self.db = db
        pass
    
    #Log the list of all SQL table in odoo database
    def listSQLTables(self):
        _logger.info("listSQLTables")
        self.db.env.cr.execute("""
            SELECT table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE table_type = 'BASE TABLE'
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)


    #Log all attributs
    def listTableAttributs(self):
        _logger.info("listTableAttributs")
        self.db.env.cr.execute("""
        SELECT COLUMN_NAME 
        FROM information_schema.columns 
        WHERE table_name = 'product_template'
        """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)  


    #Log all lines in sale_order table
    def listAllLineFromTable(self):
        _logger.info("listAllLineFromTable")
        self.db.env.cr.execute("""
            SELECT * 
            FROM product_attribute
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)


    #Log a specific sale order
    def listSpecificLineFromTable(self):
        _logger.info("listSpecificLineFromTable")
        self.db.env.cr.execute("""
            SELECT * 
            FROM product_template
            WHERE id = 16923
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    #Log a specific sale order
    def listSpecificProducft(self):
        _logger.info("listSpecificLineFromTable")
        self.db.env.cr.execute("""
            SELECT 
                PT.id,
                PT.name,
                PP.id
            FROM product_template PT
            INNER JOIN product_product PP ON
                PP.product_tmpl_id = PT.id
            WHERE PP.id = 19450
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)        



    def listProductFromSpecificSaleOrder(self):
        _logger.info("listProductFromSpecificSaleOrder")
        self.db.env.cr.execute("""
            SELECT 
                SOL.id,
                SOL.order_id,
                SOL.product_id,
                PT.name            
            FROM sale_order_line SOL
            INNER JOIN sale_order SO ON 
                SO.id = SOL.order_id AND 
                SO.name = 'S00140'
            INNER JOIN product_product PP ON
                PP.id = SOL.product_id
            INNER JOIN product_template PT ON
                PT.id = PP.product_tmpl_id
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)
