### R-E-A-L.iT ODOO EXTENSIONS DOCUMENTATIOn

### Modules:

- ba_customer_portal_extension
- ba_odoo_debranding | Removes Odoo branding from various places where it was visible in the frontend
- ba_realit_staging_ribbon | Adds a ribbon when in a staging branch to remind the developer that all actions are non-permanent
- ba_website_product_country_wise

- proCRMCustom
- problog
- procontact
- proleads
- proportal | [Jump](#proportal-documentation)
- proquotes
- sync


## ProPortal Documentation

The ProPortal module adds more functionality to quotes, invoices, and sales orders. I've divided these function into three main categories:

1. VISUAL ADDITIONS


All quotes now have a header and footer that can be changed depending on the region of the customer or salesperson. Employees can select each header and footer upon creation of the quote in a dropdown selection menu. 

The headers and footers are both stored as links to images or videos in our CDN. The fields for the selection menu are determined in models/footer_header.py, added to the backend quote creation menu in models/models.py, and their corresponding links are then fed into an image or video field in views/quotesFrontend.xml.


2. FUNCTIONAL FRONTEND ADDITIONS

Quotes can now be divided into sections (functional backend additions) and these sections can be minimized or maximized by the user by clicking a button. They can also have a default value. The folding section functionality is all found in /static/JS/fold.js.

Quote sections come in two types. 
  The first type is an information section, which uses the $ symbol at the beginning of it's shortcuts, and is not part of the product list in the quote but only provides more information. The section names are checked and then substituted with the appropriate content in views/quotesFrontend.xml. All the shortcuts for information sections (which must generate in the correct language) are: $hardware, $software, $subscription, $rental_pricenote, $rental_address, and $rental_info.
  The second type is a product section, which can be multiple or single choice, the shortcuts for which do NOT use the $ symbol. These sections consist of two parts: a header, with a title some other info and the minimization button– and the product section, which contains the list of products. All of this is handled again in views/quotesFrontend.xml, after the information section code.

French/English translations in quotation sections are managed by the views/Other/section_name.xml file. These use the section name shortcuts to generate a name once the page is loaded that corresponds with the users' selected language.


3. FUNCTIONAL BACKEND ADDITIONS


Quote sections can now be added as groupings of various products with their own title. These sections can be generated from scratch and populated with products or a shortcut can be used by naming the title of a new section a keyword like $hardware, which will automatically fill in data and products. Each section has the ability on the frontend to be minimized or maximized by the user (function frontend additions) and can be set to a multiple-choice or single-choice section, allowing the customer to select the products they would like.

Section creation and section creation shortcuts are both necessary features. [UNSURE WHERE BACKEND FIELDS ADDED FOR SECTION CREATION]




