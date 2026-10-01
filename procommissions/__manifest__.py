{
    'name': 'ProCommissions',
    'version': "19.0.1.0.0",
    'summary': 'Module to manage commission reports',
    'category': 'Hidden',
    'author': 'Ezekiel J. deBlois',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        # Action must exist before the menuitem that references it.
        'views/commissions_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
}