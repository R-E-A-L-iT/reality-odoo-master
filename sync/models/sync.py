Filter files by name
//proquotes/views/
Name
Last Modified
463
            pricelist_item.product_tmpl_id = product.id
464
            pricelist_item.applied_on = "1_product"
465
            if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
466
                pricelist_item.fixed_price = float(sheet[i][5])
467
        else:
468
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
469
            pricelist_item.applied_on = "1_product"
470
            if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
471
                pricelist_item.fixed_price = sheet[i][5]
472
    
473
    def pricelistUS(self, product, sheet, sheetWidth, i):
474
        external_id = str(sheet[i][16])
475
        pricelist_id = self.env['product.pricelist'].search([('name','=','USD Pricelist')])[0].id
476
        pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
477
        if(len(pricelist_item_ids) > 0): 
478
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
479
            pricelist_item.product_tmpl_id = product.id
480
            pricelist_item.applied_on = "1_product"
481
            if(str(sheet[i][6]) != " " and str(sheet[i][6]) != ""):
482
                pricelist_item.fixed_price = sheet[i][6]
483
        else:
484
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
485
            pricelist_item.applied_on = "1_product"
486
            if(str(sheet[i][6]) != " " and str(sheet[i][6]) != ""):
487
                pricelist_item.fixed_price = sheet[i][6]
488
    
489
    def updatePricelistProducts(self, product, sheet, sheetWidth, i, new=False):
490
        
491
        #if(product.stringRep == str(sheet[i][:])):
492
        #    return product
493
        
494
        product.name = sheet[i][1]
495
        product.description_sale = sheet[i][2]
496
        
497
        if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
498
            product.price = sheet[i][5]
499
        
500
​
501
        _logger.info(str(sheet[i][7]))
502
        if(len(str(sheet[i][7])) > 0):
503
            url = str(sheet[i][7])
504
            req = requests.get(url, stream=True)
505
            if(req.status_code == 200):
506
                product.image_1920 = base64.b64encode(req.text)
507
        
508
        if(str(sheet[i][10]) == "TRUE"):
509
            product.is_published = True
510
        else:
511
            product.is_published = False
512
        product.tracking = "serial"
513
        product.type = "product"
514
        
515
        self.translatePricelistFrench(product, sheet, sheetWidth, i, new)
516
        
517
        if(not new):
518
            product.stringRep = str(sheet[i][:])
519
        
520
        return product
521
        
522
    def translatePricelistFrench(self, product, sheet, sheetWidth, i, new):
523
        if(new == True):
524
            return
525
        else:
526
            product_name_french = self.env['ir.translation'].search([('res_id', '=', product.id),
527
                                                                     ('name', '=', 'product.template,name'),
528
                                                                    ('lang', '=', 'fr_CA')])
529
​
530
            if(len(product_name_french) > 0):
531
                product_name_french[len(product_name_french) - 1].value = sheet[i][3]
532
​
533
            else:
534
                product_name_french_new = self.env['ir.translation'].create({'name':'product.template,name', 
535
                                                                            'lang':'fr_CA',
536
                                                                            'res_id': product.id})[0]
537
                product_name_french_new.value = sheet[i][3]
538
            
539
​
540
            product_description_french = self.env['ir.translation'].search([('res_id', '=', product.id),

updatepricelistprod


updatepricelistprod​



Simple
0
0
Python
Saving failed
sync.py
Spaces: 4
Ln 506, Col 55
Server Connection Error
A connection to the Jupyter server could not be established. JupyterLab will continue trying to reconnect. Check your network connection or Jupyter server configuration.

Dismiss