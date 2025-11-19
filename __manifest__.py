{
    'name': 'Disc.com Purchase Notifier',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Notifies users on disc.com after Odoo purchase',
    'description': """
        Monitors Odoo sales; registers users on disc.com; sends notification emails.
    """,
    'author': 'Your Company Name',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'sale_management', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/disc_config_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
