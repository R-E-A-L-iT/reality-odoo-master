
{
    'name': 'ProLeads',
    'author': 'Ezekiel J. deBlois',
    'version': '1.1',
    "license": "LGPL-3",
    'summary': 'Adds automation for lead registration',
    'description': ' ',
    'depends': ['base', 'crm'],
    "data": [
        "data/mail_template_data.xml",
        "views/res_users_form.xml",
        "views/crm_lead_form.xml"
    ],
    'installable': True,
    'application': True,
}