# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time, datetime
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler

class picking_list(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking_list, self).__init__(cr, uid, name, context=context)
        company = self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id
        
        self.localcontext.update({
            'time': time,
            'company': company,
            'mailrunMoves': lambda moves: [m for m in moves if m.mailrun_required],
            'localMoves': lambda moves: [m for m in moves if not m.mailrun_required],
            'ship_type': self._get_ship_type,
        })

        picking_pool = self.pool.get('stock.picking.out')
        sale_pool = self.pool.get('sale.order')
        # Update picking list hashes as necessary.
        for picking in picking_pool.browse(cr, uid, context['active_ids']):
            picking_list_hash = sale_pool.generate_picking_list_hash(picking.sale_id)

            if picking_list_hash != picking.sale_id.picking_list_hash:
                sale_pool.write(cr, uid, picking.sale_id.id, {
                    "picking_list_version": picking.sale_id.picking_list_version + 1,
                    "picking_list_hash": picking_list_hash
                })

        picking_pool.write(cr, uid, context['active_ids'], {
            "picking_printed": datetime.datetime.now()
        })
        picking_pool.write(cr, uid, context['active_ids'], {
            "picking_printed": datetime.datetime.now()
        })
 
    def _get_ship_type(self, number):
        ship_priority = str(number)
        if not ship_priority:
            ship_type = ''
        elif ship_priority[0] == '6':
            ship_type = 'Ground'
        elif ship_priority[0] == '3':
            ship_type = 'VIP'
        elif ship_priority[0] == '1':
            ship_type = 'RUSH'
        elif ship_priority[0] == '2':
            ship_type = 'Amazon' 
        elif ship_priority[0] == '4':
            ship_type = 'Canada'
        elif ship_priority[0] == '5':
            ship_type = 'International'
        else:
            ship_type = ''
        return ship_type     
report_sxw.report_sxw(
    'report.mailrun.picking.list','stock.picking','addons/mailrun/report/picking_list.rml', parser=picking_list
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
