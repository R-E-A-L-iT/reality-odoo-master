# R-E-A-L.iT ODOO EXTENSIONS DOCUMENTATION

## Modules:

- ba_customer_portal_extension
- ba_odoo_debranding | Removes Odoo branding from various places where it was visible in the frontend
- ba_realit_staging_ribbon | Adds a ribbon when in a staging branch to remind the developer that all actions are non-permanent
- ba_website_product_country_wise

- proCRMCustom | [Jump](#procrm-documentation)
- problog | [Jump](#problog-documentation)
- procontact | [Jump](#procontact-documentation)
- proleads  | [Jump](#proleads-documentation)
- proportal | [Jump](#proportal-documentation)
- proquotes | [Jump](#proquotes-documentation)
- sync | [Jump](#sync-documentation)

## ProCRM Documentation

Nothing here yet



## ProBlog Documentation

Nothing here yet



## ProContact Documentation

Nothing here yet



## ProLeads Documentation

Nothing here yet



## ProPortal Documentation

Nothing here yet



## ProQuotes Documentation

### FRONTEND VISUAL

All quotes now have a header and footer that can be changed depending on the region of the customer or salesperson. Employees can select each header and footer upon creation of the quote in a dropdown selection menu. 

The headers and footers are both stored as links to images or videos in our CDN. The fields for the selection menu are determined and added to the backend quote creation menu in models/models.py and models/footer_header.py. The default footer is also determined in models/models.py, and their corresponding links are then fed into an image or video field in views/quotesFrontend.xml.

file: models/models.py (generating fields for footer/header selection)

    class order(models.Model):
    
    footer = fields.Selection(
        [
            ("ABtechFooter_Atlantic_Derek", "Abtech_Atlantic_Derek"),
            ...,
            ("REALiTFooter_Derek_Transcanada", "REALiTFooter_Derek_Transcanada"),
        ],
        help="Footer selection field",
        string="Footer OLD",
    )

    header = fields.Selection(
        [
            ("QH_REALiT+Abtech.mp4", "QH_REALiT+Abtech.mp4"),
            ...,
            ("Software.jpg", "Software.jpg"),
        ],
        string="Header OLD",
        help="Header selection field",
    )

All quotes also have sections that are determined in the backend by an employee, visible to the customer. These sections can be minimized or maximized by the user by clicking a button. They can also have a default value. The folding section functionality is all found in /static/JS/fold.js.

Quote sections come in two types. 

  The first type is an information section, which uses the $ symbol at the beginning of it's shortcuts, and is not part of the product list in the quote but only provides more information. The section names are checked and then substituted with the appropriate content in views/quotesFrontend.xml. All the shortcuts for information sections (which must generate in the correct language) are: $hardware, $software, $subscription, $rental_pricenote, $rental_address, and $rental_info.

file: views/Quote/quotesFrontend.xml (placeholder section title from backend is replaced by section content)

        <!-- Info Sections -->
		<xpath expr="//table[@id=&quot;sales_order_table&quot;]/tbody/t[2]/tr" position="before">
			<t t-if="line.name == '$hardware'">
				<tr>
					<td style="border-style: none;" colspan="100">
						<t t-set="isPDF" t-value="False" />
						<t t-if="clang ==  'en_CA' or clang == 'en_US'" t-call="proquotes.renewal-hardware-english" />
						<t t-elif="clang == 'fr_CA'" t-call="proquotes.renewal-hardware-french" />
					</td>
				</tr>
			</t>
			<t t-if="line.name == '$software'">
				<tr>
					<td style="border-style: none;" colspan="100">
						<t t-call="proquotes.renewal-software" />
					</td>
				</tr>
			</t>
            ...
        </xpath>

  The second type is a product section, which can be multiple or single choice, the shortcuts for which do NOT use the $ symbol. These sections consist of two parts: a header, with a title some other info and the minimization button– and the product section, which contains the list of products. All of this is handled again in views/quotesFrontend.xml, after the information section code.

file: views/Quote/quotesFrontend.xml (new header creation)

    <t t-if="line.name == '$block' or line.name == '$block+'">
		<tr class="quote-head">
			<td class="text-left">
				<span t-if="clang == 'en_CA' or clang == 'en_US'" class="cHead" style="padding-left: 20px !important;">Product</span>
				<span t-elif="clang == 'fr_CA'" class="cHead" style="padding-left: 20px !important;">Produit</span>
			</td>
			<td t-if="line.name == '$block+'" class="text-left">
				<span t-if="clang == 'en_CA' or clang == 'en_US'" class="cHead">Value</span>
				<span t-elif="clang == 'fr_CA'" class="cHead">Valeur</span>
			</td>
			<td t-else=""></td>
			<td />
			<td class="text-left">
				<span t-if="clang == 'en_CA' or clang == 'en_US'" class="cHead">Qty</span>
				<span t-elif="clang == 'fr_CA'" class="cHead">Qté</span>
			</td>
			<td class="text-left">
				<span t-if="clang == 'en_CA' or clang == 'en_US'" class="cHead">Price</span>
				<span t-elif="clang == 'fr_CA'" class="cHead">Prix</span>
			</td>
			<td>
				<span t-if="clang == 'en_CA' or clang == 'en_US'">Tax</span>
				<span t-elif="clang == 'fr_CA'">Taxes</span>
			</td>
			<td class="text-left">
				<span t-if="clang == 'en_CA' or clang == 'en_US'" class="cHead">Amount</span>
				<span t-elif="clang == 'fr_CA'" class="cHead">Montant</span>
			</td>
		</tr>
	</t>

file: views/Quote/quotesFrontend.xml (section minimizer)

    <xpath expr="//t[@t-if=&quot;line.display_type == 'line_section'&quot;]/td/span" position="replace">
	    <div style="width: 75%; float: left;">
		    <label t-attf-for="fold{{line}}{{line_index}}" style="display: inline-block; width: 100%; height: 100%;">
                <span t-if="line.hiddenSection == 'no'" class="quote-folding-arrow">&#215;</span>
			    <span t-else="" class="quote-folding-arrow">+</span>
				<t t-if="line.special == 'optional'">
				    <input t-if="line.selected == 'true'" class="optionalSectionCheckbox" type="checkbox" checked="true" />
					<input t-else="" class="optionalSectionCheckbox" type="checkbox" />
				</t>
				<span t-if="line.name.strip()[0] != '#'" t-field="line.name" />
				<span t-elif="line.name.strip()[0] == '#'">
					<t t-set="sname" t-value="line.name[1:].strip()" />
					<t t-call="proquotes.section_name_resolution" />
				</span>
			    <span class="line_id" t-attf-id="{{line}}" />
		    </label>
        </div>
    </xpath>

French/English translations in quotation sections are managed by the views/Other/section_name.xml file. These use the section name shortcuts to generate a name once the page is loaded that corresponds with the users' selected language.

  - Sales Quotes
  - Rental Quotes

Rental Quotes are a specific type of quote for renting a scanner or software rather than purchasing it. Because of this there are specific terms and conditions of rental quotes that differ from normal sales orders. These are generated in french or english depending on the customers language and all this is defined in views/Quote/rentalTerms.xml.

Rental Quotes also require 
    
  - Renewal Quotes

Renewal quotes are a specific type of quote for renewing a software license. Because of this there are specific information sections that correspond only to renewal quotes. The extra text and information for these renewal quotes is defined in views/Quote/renewalText.xml

### FRONTEND FUNCTIONAL
  
The frontend sections are minimizable and have products that can be selected or deselected by the user. 

### BACKEND FUNCTIONAL

All quotes, sales orders, and purchase orders have sections that can be built in the backend by a user. These sections can be generated and populated with products from scratch, or they can be named in the title as one of a specific set of keywords that will automatically populate them with products and information. The section also has the option to be single choice or multiple choice.



## SYNC Documentation

### Views

### Models

#### forward_sync/

googlesheetsAPI.py 

Different databases and google sheet IDs dependent on if the branch is the main one or a staging branch, and if it is a staging branch, depending on which developer is using it. New developers added manually. Different database IDs are also defined here.

        _master_database_template_id_dev_oli = ("...")
        _master_database_template_id_dev_zek = ("...")   
        _master_database_template_id_dev_bc = ("...")            
        
        # Return the proper GoogleSheet Template ID base on the environement
        if _db_name == _db_name_prod:
            _logger.info("Production")
            return _master_database_template_id_prod
        elif dev_oli in _db_name:
            _logger.info("Dev Oli")
            return _master_database_template_id_dev_oli
        elif dev_zek in _db_name:
            _logger.info("Dev Zek")
            return _master_database_template_id_dev_zek
        elif dev_braincrew in _db_name:
            _logger.info("Dev BrainCrew")
            return _master_database_template_id_dev_bc            
        else:
            _logger.info("Default Dev GS")
            return _master_database_template_id_prod

The function to access the google sheet (readonly) requires a password, spreadsheet ID and sheet number (tab of the google sheet to read)

	def getDoc(self, psw, spreadsheetID, sheet_num):
		scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
	
	        creds = sac.from_json_keyfile_dict(psw, scope)
	        client = gspread.authorize(creds)
	
	        doc = client.open_by_key(spreadsheetID)
	        return doc.get_worksheet(sheet_num).get_all_values()

pricelist.py


sync.py

class sync includes the following functions:

1. start_sync

First checks the password for accessing the GS is valid.

Second, puts all the data in the ODOO_SYNC_DATA tab of the google sheet into the variable sync_data.
the ODOO_SYNC_DATA tab contains the names of all the spreadsheets that are to be synced with the odoo database. 

a while loop goes through each line of data in the first google sheet listed in sync_data. Each line in this first GS has a valid term that if false stops the sync and moves to the next sheet.

2. is_password_format_good
3. getMasterDatabaseSheet (just pick a naming convention!!)
4. getSheetIndex
5. getSyncValues
6. syncFail
7. sendSyncReport
8. archive_product
9. getAllValueFromColumn
10. checkIfKeyExistInTwoDict
11. checkOdooSyncDataTab
12. getListSkuGS
13. getColumnIndex
14. getSkuToArchive
15. cleanSku
16. log_product_from_sale
17. searchQuotation
18. getProductsWithSameName
19. getSaleOrderByProductId
20. getProductIdBySku
21. cleanProductByName
22. addContact
23. cleanCCPUnsed
24. cleanSPLUnsed
25. migrateCCP
26. cleanIMD
27. setSeq
28. resetCleaningSeq
29. getCleaningIdNextId
30. incCleaningId
31. cleanOneSaleOrder
32. cleanSoleOrderLines



