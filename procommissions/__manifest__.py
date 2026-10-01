{
    'name': 'ProCommissions',
    'version': "19.0.1.0.0",
    'summary': 'Module to manage commission reports',
    'category': 'Hidden',
    'author': 'Ezekiel J. deBlois',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/commissions_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
}