import logging

_logger = logging.getLogger(__name__)

class sql_queries:

    def __init__(self, db):
        self.db = db
        pass
    
    #Log the list of all SQL table in odoo database
    def listSQLTables(self):
        _logger.info("customQuery test")
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

    #Log all lines in sale_order table
    def listAllSaleOrder(self):
        _logger.info("customQuery test")
        self.db.env.cr.execute("""
            SELECT * 
            FROM sale_order
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    #Log all sale_order attribut
    def listSaleOrderAttributs(self):
        _logger.info("customQuery test")
        self.db.env.cr.execute("""
        SELECT COLUMN_NAME 
        FROM information_schema.columns 
        WHERE table_name = 'sale_order'
        """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)  