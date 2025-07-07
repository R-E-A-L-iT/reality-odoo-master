
{
    'name': 'ProLeads',
    'author': 'Ezekiel J. deBlois',
    'version': '1.2',
    "license": "LGPL-3",
    'summary': 'Adds features and automation for leads in odoo.',
    'description': """Features added by this module:
    1. More opportunity fields
    2. Visible stages for leads
    3. Automation of lead registration with Leica
    4. More features for generating leads from website visits
    5. etc...
    """,
    'depends': ['base', 'crm'],
    "data": [
        "views/leadsBackend.xml",
        "views/website_visitor_views.xml",
        "views/crm_reveal_views.xml",
    ],
    'installable': True,
    'application': True,
}