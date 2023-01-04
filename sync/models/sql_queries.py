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

    #Log all lines in sale_order table
    def listAllSaleOrder(self):
        _logger.info("listAllSaleOrder")
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
        _logger.info("listSaleOrderAttributs")
        self.db.env.cr.execute("""
        SELECT COLUMN_NAME 
        FROM information_schema.columns 
        WHERE table_name = 'sale_order_line'
        """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)  

    #Log a specific sale order
    def listSpecificSaleOrder(self):
        _logger.info("listSpecificSaleOrder")
        self.db.env.cr.execute("""
            SELECT * 
            FROM sale_order
            WHERE name = 'S00140'
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
                SOL.product_id 
            FROM sale_order_line SOL
            INNER JOIN sale_order SO ON 
                SO.id = SOL.order_id AND 
                SO.name = 'S00140'
            """)
        tables = self.db.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)
        
        
    #(140, 'S00140', None, None, None, 'sale', datetime.datetime(2022, 3, 3, 2, 32, 20), datetime.date(2021, 10, 20), True, False, datetime.datetime(2021, 9, 20, 20, 40, 31, 18518), 2, 58338, 58338, 58338, 1, 4, None, 'no', '<p></p>', 8310.0, 0.0, 8310.0, 1.0, None, None, 7, 1, None, None, None, True, 'c73796ad-8092-4c5d-922f-9c3f6a5f66c1', None, None, None, None, 2, 1, datetime.datetime(2022, 3, 3, 2, 32, 20, 48246), False, None, 66, None, 'direct', 6, 15, None, None, None, '<section class="s_picture bg-200 pb24 o_colored_level pt0" data-snippet="s_picture" data-name="Picture"><div class="container"><p style="text-align: center;"><br></p><p style="text-align: center;"><br></p><div class="row s_nb_column_fixed"><div class="o_colored_level col-lg-10 offset-lg-1 pb0" style="text-align: center;"><figure class="figure"><img src="/web/image/34236-f38a3b2c/Abtech Header.png?access_token=7c7de2b8-f10c-42cb-81f0-52354e92350d" class="figure-img img-thumbnail padding-large" alt="" loading="lazy" data-original-title="" title="" aria-describedby="tooltip159068" data-original-id="34235" data-original-src="/web/image/34235-960a0a45/Abtech Header.png" data-mimetype="image/png" data-resize-width="992"><figcaption class="figure-caption py-3 text-muted"><br></figcaption></figure></div></div></div></section>\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n<section class="o_colored_level s_text_block pb24 pt0" data-snippet="s_text_block" data-name="Text" style=""><font class="text-white"><div style="text-align: center;"><font style="position: relative; caret-color: rgb(51, 51, 51); color: rgb(51, 51, 51); text-align: left;"><div style="text-align: center;"><div><font color="#ffffff" class="text-white" style="font-size: 18px;"><span style="caret-color: rgb(255, 255, 255);"><b>REVIEW THE QUOTE BELOW</b><br>\xa0</span></font><font style="color: rgb(255, 0, 0); font-size: 18px;"><span style="caret-color: rgb(255, 255, 255);">__</span></font><font style="color: rgb(255, 5, 5); font-size: 18px;"><span style="caret-color: rgb(255, 255, 255);">___</span><span style="caret-color: rgb(255, 255, 255);">__</span><span style="caret-color: rgb(255, 255, 255);">_</span></font></div></div></font></div></font><div class="s_allow_columns container">\n            <p class="o_default_snippet_text">Great stories have a <b class="o_default_snippet_text">personality</b>. Consider telling a great story that provides personality. Writing a story with personality for potential clients will assist with making a relationship connection. This shows up in small quirks like word choices or phrases. Write from your point of view, not from someone else\'s experience.\n            </p><p class="o_default_snippet_text">Great stories are <b class="o_default_snippet_text">for everyone</b> even when only written <b class="o_default_snippet_text">for just one person</b>. If you try to write with a wide, general audience in mind, your story will sound fake and lack emotion. No one will be interested. Write for one person. If it’s genuine for the one, it’s genuine for the rest.\n        \n\n\n\n\n\n\n\n\n\n</p></div></section>\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n', None, None, None, None, None, False, 0.0, None, 'reality', 'Surveying', None, None, None, None, None, None, None, None, None, None, None, None, None, None)
        