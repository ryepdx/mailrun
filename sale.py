import hashlib, itertools
from copy import copy
from collections import OrderedDict
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc, SUPERUSER_ID

class sale_order(osv.Model):
    _inherit = 'sale.order'

    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        location_pool = self.pool.get("stock.location")
        location_id = order.shop_id.warehouse_id.lot_stock_id.id

        inventory_pool = self.pool.get('stock.inventory.line')
        location_ids = [int(l.id) for l in set(itertools.chain.from_iterable(
            [l.parent_location_ids + [l] for l in [i.location_id for i in inventory_pool.browse(
                cr, uid, inventory_pool.search(cr, uid, [('product_id', '=', line.product_id.id)])
            )]]
        ))]

        if location_id not in location_ids:
            potential_locations = [order.shop_id.warehouse_id.lot_stock_id]
        else:
            potential_locations = location_pool.browse(cr, uid, location_ids)

        if potential_locations:
            location_id = sorted(
                potential_locations, key=lambda loc: location_pool.location_weight(
                    cr, uid, loc, line.product_id,
                    preferred_locations=[line.order_id.shop_id.warehouse_id.lot_input_id]
                ), reverse=True
            )[0].id

        return {
            'name': line.name,
            'origin': order.name,
            'date_planned': date_planned,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                    or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'location_id': location_id,
            'procure_method': line.type,
            'move_id': move_id,
            'company_id': order.company_id.id,
            'note': line.name,
        }

    def _prepare_mailrun_procurement(self, cr, uid, order, procurement, context=None):
        location = self.pool.get("stock.location").browse(cr, uid, procurement['location_id'])

        if location.calculated_company_id.id == order.company_id.id:
            return None

        mailrun_procurement = copy(procurement)
        mailrun_procurement['name'] += " (Mailrun)"
        return mailrun_procurement

    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        location_pool = self.pool.get("stock.location")
        location = order.shop_id.warehouse_id.lot_stock_id
        output_id = order.shop_id.warehouse_id.lot_output_id.id

        inventory_pool = self.pool.get('stock.inventory.line')
        location_ids = [int(l.id) for l in set(itertools.chain.from_iterable(
            [l.parent_location_ids + [l] for l in [i.location_id for i in inventory_pool.browse(
                cr, uid, inventory_pool.search(cr, uid, [('product_id', '=', line.product_id.id)])
            )]]
        ))]

        if location.id not in location_ids:
            location = order.shop_id.warehouse_id.lot_input_id
            warehouse_pool = self.pool.get("stock.warehouse")
            warehouse = warehouse_pool.browse(cr, SUPERUSER_ID, order.shop_id.warehouse_id.id, context=context)
            potential_locations = []

            for w in warehouse.shared_warehouse_ids:
                intersection = [l for l in w.lot_stock_id.parent_location_ids if l.id in location_ids]
                if w.lot_stock_id.id in location_ids or intersection:
                    potential_locations.append((w.lot_stock_id, w.lot_output_id))
        else:
            potential_locations = [(l, order.shop_id.warehouse_id.lot_output_id)
                                   for l in location_pool.browse(cr, SUPERUSER_ID, location_ids)
            ]

        if potential_locations:
            location, output_id = sorted(
                potential_locations, key=lambda l: location_pool.location_weight(cr, uid, l[0], line.product_id,
                                                                                 preferred_locations=[location])
            )[-1]
            output_id = output_id.id

        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location.id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
        }

    def _prepare_mailrun_out_move(self, cr, uid, order, move, context=None):
        location = self.pool.get("stock.location").browse(cr, uid, move['location_id'])

        if location.calculated_company_id.id == order.company_id.id:
            return None

        mailrun_move = copy(move)
        warehouse_pool = self.pool.get('stock.warehouse')
        warehouse = warehouse_pool.browse(cr, SUPERUSER_ID, warehouse_pool.search(cr, SUPERUSER_ID, [
            ('lot_input_id', 'in', ([pl.id for pl in location.parent_location_ids] + [location.id]))
        ]))[0]

        if location.calculated_company_id.id == order.company_id.id \
                or (location.partner_id and location.partner_id.id == location.calculated_partner_id.id) \
                or not warehouse:
            return None

        mailrun_move['location_dest_id'] = warehouse.mailrun_output_id.id
        mailrun_move['company_id'] = warehouse.company_id.id
        mailrun_move['mailrun_destination'] = location.id

        return mailrun_move

    def _prepare_mailrun_in_move(self, cr, uid, order, move, context=None):
        location = self.pool.get("stock.location").browse(cr, uid, move['location_id'])

        if location.calculated_company_id.id == order.company_id.id \
                or location.partner_id.id == location.calculated_partner_id.id:
            return None

        mailrun_move = copy(move)

        mailrun_move['location_id'] = order.shop_id.warehouse_id.mailrun_input_id.id
        mailrun_move['location_dest_id'] = order.shop_id.warehouse_id.lot_stock_id.id
        mailrun_move['company_id'] = order.company_id.id

        return mailrun_move

    def _prepare_mailrun_in_picking(self, cr, uid, order, in_move, context=None):
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'type': 'in',
            'state': 'auto',
            'move_type': order.picking_policy,
            'partner_id': order.partner_shipping_id.id,
            'note': "Mailrun",
            'invoice_state': 'none',
            'company_id': in_move['company_id'],
        }

    def _prepare_mailrun_out_picking(self, cr, uid, order, out_move, context=None):
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'partner_id': order.partner_shipping_id.id,
            'note': "Mailrun",
            'invoice_state': 'none',
            'company_id': out_move['company_id'],
        }


    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sales order to which the order lines belong
        :param list(browse_record) order_lines: sales order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []
        mailrun_out_picking_ids = {}
        mailrun_in_picking_id = None

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.type in ('product', 'consu'):
                    if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))

                    move = self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context)
                    mailrun_out_move = self._prepare_mailrun_out_move(cr, uid, order, move, context=context)

                    if mailrun_out_move:
                        if not mailrun_out_picking_ids.get(mailrun_out_move['company_id']):
                            mailrun_out_picking = self._prepare_mailrun_out_picking(cr, uid, order, mailrun_out_move, context=context)
                            mailrun_out_picking_ids[mailrun_out_move['company_id']] = \
                                picking_obj.create(cr, SUPERUSER_ID, mailrun_out_picking)

                        mailrun_out_move['picking_id'] = mailrun_out_picking_ids[mailrun_out_move['company_id']]
                        move_obj.create(cr, SUPERUSER_ID, mailrun_out_move)

                    mailrun_in_move = self._prepare_mailrun_in_move(cr, uid, order, move, context=context)

                    if mailrun_in_move:
                        if not mailrun_in_picking_id:
                            mailrun_in_picking = self._prepare_mailrun_in_picking(cr, uid, order, mailrun_in_move, context=context)
                            mailrun_in_picking_id = picking_obj.create(cr, uid, mailrun_in_picking)

                        mailrun_in_move['picking_id'] = mailrun_in_picking_id
                        move_obj.create(cr, SUPERUSER_ID, mailrun_in_move)

                        move['location_id'] = order.shop_id.warehouse_id.lot_stock_id.id
                        move['location_dest_id'] = order.shop_id.warehouse_id.lot_output_id.id
                        move['mailrun_required'] = True

                    move_id = move_obj.create(cr, uid, move)

                else:
                    # a service has no stock move
                    move_id = False

                if mailrun_out_picking_ids:
                    picking_obj.action_confirm(cr, SUPERUSER_ID, mailrun_out_picking_ids.values(), context=context)

                if mailrun_in_picking_id:
                    picking_obj.action_confirm(cr, uid, [mailrun_in_picking_id], context=context)

                procurement = self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context)
                mailrun_procurement = self._prepare_mailrun_procurement(cr, uid, order, procurement, context=context)

                if mailrun_procurement:
                    procurement_obj.create(cr, SUPERUSER_ID, mailrun_procurement)
                    procurement['location'] = order.shop_id.warehouse_id.mailrun_input_id

                proc_id = procurement_obj.create(cr, uid, procurement)
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")

        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}

        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True


sale_order()


