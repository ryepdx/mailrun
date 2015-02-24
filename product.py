# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class product(osv.osv):
    _inherit = "product.product"

    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in a particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}

        if context.get('shop', False):
            warehouse_id = self.pool.get('sale.shop').read(
                cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id

        if context.get('warehouse', False):
            lot_id = self.pool.get('stock.warehouse').read(
                cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id

        location_ids = []
        
        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = self.pool.get('stock.location').search(
                    cr, uid, [('name', 'ilike', context['location'])], context=context)
            else:
                location_ids = context['location']

        if not location_ids:
            location_ids = self.get_location_ids(cr, uid, ids, context=context)

        old_warehouse = context.get('warehouse')
        old_shop = context.get('shop')
        old_location = context.get('location')
        old_compute_child = context.get('compute_child')

        if location_ids:
            context['warehouse'] = False
            context['shop'] = False
            context['location'] = location_ids
            context['compute_child'] = False

        # build the list of ids of children of the location given by id
        if context.get('compute_child', True):
            location_ids = self.pool.get('stock.location').search(cr, uid, [
                '|', ('id', 'in', location_ids or []), ('location_id', 'child_of', location_ids)
            ]) if location_ids else []

        if not location_ids:
            return {}.fromkeys(ids, 0.0)

        res = super(product, self).get_product_available(cr, uid, ids, context=context)

        context['warehouse'] = old_warehouse
        context['shop'] = old_shop
        context['location'] = old_location
        context['compute_child'] = old_compute_child

        return res

    def get_location_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        location_ids = []
        company_id = self.pool.get("res.users").browse(cr, uid, uid).company_id.id
        warehouse_obj = self.pool.get('stock.warehouse')
        wids = warehouse_obj.search(cr, uid, [('company_id', '=', company_id)], context=context)

        for w in warehouse_obj.browse(cr, SUPERUSER_ID, wids, context=context):
            location_ids += [w.lot_stock_id.id]

            if not context.get("no_warehouse_sharing"):
                location_ids += [warehouse_ids.lot_stock_id.id for warehouse_ids in w.shared_warehouse_ids]

        return location_ids

product()