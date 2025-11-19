{
    'name': 'Disc.com Purchase Notifier',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Middleware to notify users on disc.com after purchase',
    'description': """
        This module automatically:
        - Monitors sale orders in Odoo
        - Registers users on disc.com when payment is confirmed
        - Sends notification emails with login credentials
    """,
    'author': 'Your Name',
    'depends': ['sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/disc_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}