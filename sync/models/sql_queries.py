import logging

_logger = logging.getLogger(__name__)

class sql_queries:

    def __init__(self):
        pass
    
    def listSQLTables(self):
        _logger.info("customQuery test")
        self.env.cr.execute("""
            SELECT table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE table_type = 'BASE TABLE'
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    def listAllSaleOrder(self):
        _logger.info("customQuery test")
        self.env.cr.execute("""
            SELECT * 
            FROM sale_order
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    def listSaleOrderAttributs(self):
        _logger.info("customQuery test")
        self.env.cr.execute("""
        SELECT COLUMN_NAME 
        FROM information_schema.columns 
        WHERE table_name = 'sale_order'
        """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)  