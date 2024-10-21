{
    'name': 'ProCommissions',
    'version': '1.0',
    'summary': 'Module to manage commission reports',
    'category': 'Hidden',
    'author': 'Ezekiel J. deBlois',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/commissions_views.xml',
    ],
    'application': True,
    'installable': True,
}