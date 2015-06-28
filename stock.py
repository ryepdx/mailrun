#  -*- coding: utf-8 -*-
# 
# 
#     OpenERP, Open Source Management Solution
#     Copyright (C) 2014 RyePDX LLC (<http://www.ryepdx.com>)
#     Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
# 
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>
##############################################################################

from collections import OrderedDict
from itertools import ifilter
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields

class stock_move(osv.osv):
    _inherit = 'stock.move'

    def _mailrun_destination(self, cr, uid, ids, field_name, args, context=None):
        return dict([
            (m.id, m.picking_id.sale_id.shop_id.warehouse_id.lot_stock_id)
            for m in self.browse(cr, uid, ids, context=context)
        ])

    _columns = {
        'mailrun_required': fields.boolean(string="Mailrun Required"),
        'mailrun_date': fields.date("Mailrun Date"),
        'mailrun_destination': fields.many2one('stock.location', "Mailrun Destination")
    }

stock_move()


class stock_location(osv.osv):
    _inherit = 'stock.location'
    _location_weights = OrderedDict([
        ('addresses_match', 1),
        ('matches_warehouse_stock_location', 2),
        ('in_stock', 4)
    ])

    def _parent_location_ids(self, cr, uid, ids, field_name, args, include_self=False, context=None):
        res = {}
        for location in self.browse(cr, uid, ids, context=context):
            curr_location = location
            res[location.id] = []

            if include_self:
                res[location.id] = [location.id]

            while curr_location.location_id:
                res[location.id].append(curr_location.location_id.id)
                curr_location = curr_location.location_id

        return res

    def _calculate_partner_id(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        parents = self._parent_location_ids(cr, uid, ids, field_name, args, include_self=True, context=context)

        for location_id in ids:
            res[location_id] = next(
                ifilter(None, [l.partner_id.id for l in self.pool.get('stock.location').browse(
                    cr, SUPERUSER_ID, parents[location_id]) if l.partner_id]), None)

        return res

    def _calculate_company_id(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        parents = self._parent_location_ids(cr, uid, ids, field_name, args, include_self=True, context=context)

        for location_id in ids:
            res[location_id] = next(
                ifilter(None, [l.company_id.id for l in self.pool.get('stock.location').browse(
                    cr, SUPERUSER_ID, parents[location_id]) if l.company_id]), None
            )

        return res

    def location_weight(self, cr, uid, location, product, preferred_locations=[], context={}):
        weight = 0
        location = self.pool.get("stock.location").browse(cr, uid, location.id)
        location_partner_ids = [l.partner_id.id for l in preferred_locations if l.partner_id]

        if location.partner_id.id in location_partner_ids:
            weight += self._location_weights['addresses_match']

        if location.id in [l.id for l in preferred_locations]:
            weight += self._location_weights['matches_warehouse_stock_location']

        default_context = {
            'states': ('done', 'confirmed'), 'what': ('in', 'out'), 'location': location.id,
            'no_warehouse_sharing': True, 'compute_child': False
        }
        default_context.update(context)
        in_stock = self.pool.get("product.product")\
            .get_product_available(cr, uid, [product.id], context=default_context)

        if in_stock.get(product.id, 0) > 0:
            weight += self._location_weights['in_stock']

        return weight

    _columns = {
        'parent_location_ids': fields.function(
            _parent_location_ids, type='one2many', readonly=True, relation='stock.location', string="Parent Locations",
            method=True
        ),
        'calculated_partner_id': fields.function(
            _calculate_partner_id, type='many2one', readonly=True, relation='res.partner', string="Address", method=True
        ),
        'calculated_company_id': fields.function(
            _calculate_company_id, type='many2one', readonly=True, relation="res.company", string="Company", method=True
        ),

    }

stock_location()


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"

    _columns = {
        'warehouse_group_id': fields.many2one('mailrun.warehouse.group', 'Warehouse Mailrun Group', required=True),
        'mailrun_output_id': fields.many2one('stock.location', 'Mailrun Output', required=True),
        'mailrun_input_id': fields.many2one('stock.location', 'Mailrun Input', required=True),
        'partner_id': fields.many2one('res.partner', 'Address', required=True),
        'shared_warehouse_ids': fields.related(
            'warehouse_group_id', 'warehouse_ids', type='one2many', relation='stock.warehouse',
            string="Shared Warehouses", store=False
        )
    }

stock_warehouse()


class mailrun_warehouse_group(osv.osv):
    _name = "mailrun.warehouse.group"
    _columns = {
        'name': fields.char('Name', size=32),
        'warehouse_ids': fields.one2many('stock.warehouse', 'warehouse_group_id', string="Warehouses")
    }

mailrun_warehouse_group()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
