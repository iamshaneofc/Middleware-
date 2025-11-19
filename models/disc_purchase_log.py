from odoo import models, fields, api
import requests
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class DiscPurchaseLog(models.Model):
    _name = 'disc.purchase.log'
    _description = 'Disc.com Purchase Notification Log'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, index=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_name = fields.Char(string='Customer Name')
    customer_email = fields.Char(string='Customer Email')
    customer_phone = fields.Char(string='Phone Number')
    
    # Assessment details
    assessment_name = fields.Char(string='Assessment Name')
    assessment_product_id = fields.Many2one('product.product', string='Assessment Product')
    
    # Purchase details
    purchase_date = fields.Datetime(string='Purchase Date', required=True, default=fields.Datetime.now)
    amount_total = fields.Float(string='Total Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ], string='Payment Status', default='pending')
    
    # Disc.com registration details
    disc_registration_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Registration Status', default='not_sent')
    disc_user_id = fields.Char(string='Disc.com User ID')
    disc_response = fields.Text(string='API Response')
    
    # Email notification
    email_sent = fields.Boolean(string='Email Sent', default=False)
    email_sent_date = fields.Datetime(string='Email Sent Date')
    
    def send_to_disc_com(self):
        """Send registration data to disc.com"""
        self.ensure_one()
        
        # Get API configuration
        config = self.env['ir.config_parameter'].sudo()
        disc_api_url = config.get_param('disc.api.url', '')
        disc_api_key = config.get_param('disc.api.key', '')
        
        if not disc_api_url:
            _logger.error('Disc.com API URL not configured')
            self.disc_registration_status = 'failed'
            return False
        
        # Prepare payload
        payload = {
            'email': self.customer_email,
            'name': self.customer_name,
            'phone': self.customer_phone,
            'order_reference': self.name,
            'assessment_name': self.assessment_name,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'amount': self.amount_total,
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        if disc_api_key:
            headers['Authorization'] = f'Bearer {disc_api_key}'
        
        try:
            _logger.info(f'Sending registration to disc.com for order {self.name}')
            response = requests.post(
                disc_api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            self.disc_response = json.dumps(response.json(), indent=2)
            
            if response.status_code == 200 or response.status_code == 201:
                response_data = response.json()
                self.disc_user_id = response_data.get('user_id', '')
                self.disc_registration_status = 'sent'
                _logger.info(f'Successfully registered user on disc.com: {self.customer_email}')
                return True
            else:
                self.disc_registration_status = 'failed'
                _logger.error(f'Failed to register on disc.com: {response.status_code}')
                return False
                
        except Exception as e:
            _logger.error(f'Error sending to disc.com: {str(e)}')
            self.disc_response = str(e)
            self.disc_registration_status = 'failed'
            return False
    
    def send_notification_email(self):
        """Send email notification to customer"""
        self.ensure_one()
        
        template = self.env.ref('disc_purchase_notifier.email_template_disc_registration', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)
            self.email_sent = True
            self.email_sent_date = fields.Datetime.now()
            _logger.info(f'Notification email sent to {self.customer_email}')
        else:
            _logger.warning('Email template not found')


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    disc_purchase_log_ids = fields.One2many('disc.purchase.log', 'sale_order_id', string='Disc Purchase Logs')
    
    def action_confirm(self):
        """Override to create disc purchase log when order is confirmed and paid"""
        result = super(SaleOrder, self).action_confirm()
        
        for order in self:
            # Check if payment is confirmed (you may need to adjust this based on your payment flow)
            if order.invoice_status == 'invoiced' or order.state == 'sale':
                order._create_disc_purchase_log()
        
        return result
    
    def _create_disc_purchase_log(self):
        """Create purchase log and trigger disc.com registration"""
        self.ensure_one()
        
        # Check if already logged
        if self.disc_purchase_log_ids:
            _logger.info(f'Disc purchase log already exists for order {self.name}')
            return
        
        # Get assessment product (assuming you have a specific product category or field)
        assessment_product = self.order_line.filtered(
            lambda l: l.product_id.categ_id.name == 'Assessment' or 'assessment' in l.product_id.name.lower()
        ).mapped('product_id')[:1]
        
        # Create log entry
        log_vals = {
            'name': self.name,
            'sale_order_id': self.id,
            'customer_id': self.partner_id.id,
            'customer_name': self.partner_id.name,
            'customer_email': self.partner_id.email,
            'customer_phone': self.partner_id.phone or self.partner_id.mobile,
            'assessment_name': assessment_product.name if assessment_product else '',
            'assessment_product_id': assessment_product.id if assessment_product else False,
            'purchase_date': fields.Datetime.now(),
            'amount_total': self.amount_total,
            'currency_id': self.currency_id.id,
            'payment_status': 'paid',
        }
        
        log = self.env['disc.purchase.log'].create(log_vals)
        
        # Send to disc.com
        if log.send_to_disc_com():
            # Send notification email
            log.send_notification_email()
    
    def write(self, vals):
        """Monitor payment status changes"""
        result = super(SaleOrder, self).write(vals)
        
        # If payment status changes to paid, trigger disc.com registration
        if 'invoice_status' in vals or 'state' in vals:
            for order in self:
                if order.state == 'sale' and not order.disc_purchase_log_ids:
                    order._create_disc_purchase_log()
        
        return result