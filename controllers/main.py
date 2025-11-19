from odoo import http
from odoo.http import request
import json

class AssessmentPurchaseController(http.Controller):
    
    @http.route('/assessment/purchase/export/<int:purchase_id>', 
                type='http', auth='user')
    def export_json(self, purchase_id, **kwargs):
        """Export assessment purchase as JSON file"""
        purchase = request.env['assessment.purchase'].browse(purchase_id)
        
        if not purchase.exists():
            return request.not_found()
        
        filename = f'assessment_purchase_{purchase.name}.json'
        
        return request.make_response(
            purchase.purchase_data_json,
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )