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
- proportal
- proquotes
- sync


## ProPortal Documentation

The ProPortal module adds more functionality to quotes, invoices, and sales orders. I've divided these function into three main categories:

1. VISUAL ADDITIONS


All quotes now have a header and footer that can be changed depending on the region of the customer or salesperson. Employees can select each header and footer upon creation of the quote in a dropdown selection menu. 

The headers and footers are both stored as links to images or videos in our CDN. The fields for the selection menu are determined in models/footer_header.py, added to the backend quote creation menu in models/models.py, and their corresponding links are then fed into an image or video field in views/quotesFrontend.xml.


2. FUNCTIONAL FRONTEND ADDITIONS

3. FUNCTIONAL BACKEND ADDITIONS


Quote sections can now be added as groupings of various products with their own title. These sections can be generated from scratch and populated with products or a shortcut can be used by naming the title of a new section a keyword like $hardware, which will automatically fill in data and products. Each section has the ability on the frontend to be minimized or maximized by the user (function frontend additions) and can be set to a multiple-choice or single-choice section, allowing the customer to select the products they would like.

Section creation and section creation shortcuts are both necessary features. 




