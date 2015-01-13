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
from collections import namedtuple
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler, SUPERUSER_ID

Mailrun = namedtuple("Mailrun", ["partner", "moves"])

class MailrunMove(object):
    def __init__(self, product_id, mailrun_destination, location_id, product_qty):
        self.product_id = product_id
        self.mailrun_destination = mailrun_destination
        self.location_id = location_id
        self.product_qty = product_qty

class mailrun(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(mailrun, self).__init__(cr, uid, name, context=context)
        user_pool = self.pool.get('res.users')

        date = context.get('date', time.strftime('%Y-%m-%d'))
        date_american = datetime.datetime.strptime(date, '%Y-%m-%d').strftime("%m/%d/%Y")
        curr_company = user_pool.browse(cr, uid, uid, context=context).company_id
        curr_address = curr_company.partner_id

        move_pool = self.pool.get('stock.move')
        moves = move_pool.browse(cr, SUPERUSER_ID,
            move_pool.search(cr, uid, [('mailrun_date', '=', date)])
        )

        if not moves:
            warehouse_pool = self.pool.get('stock.warehouse')
            mailrun_location_ids = [w.mailrun_output_id.id for w in warehouse_pool.browse(
                cr, uid, warehouse_pool.search(cr, uid, [('company_id', '=', curr_company.id)]))]
            moves = move_pool.browse(cr, SUPERUSER_ID, move_pool.search(
                cr, uid, [('mailrun_date', '=', None), ('location_dest_id', 'in', mailrun_location_ids)]
            ))
            move_pool.write(cr, uid, [m.id for m in moves], {'mailrun_date': date})

        mailruns = {}
        partners = {}

        for move in moves:
            move_key = '%s:%s:%s' % (move.product_id.id, move.location_id.id, move.mailrun_destination.id)
            partner_key = move.mailrun_destination.calculated_partner_id.id

            if partner_key not in mailruns:
                mailruns[partner_key] = {}
                partners[partner_key] = move.mailrun_destination.calculated_partner_id

            if move_key not in mailruns[partner_key]:
                mailruns[partner_key][move_key] = MailrunMove(
                    move.product_id, move.mailrun_destination, move.location_id, move.product_qty
                )
            else:
                mailruns[partner_key][move_key].product_qty += move.product_qty

        self.localcontext.update({
            "date": date_american,
            "mailruns": [Mailrun(partner, mailruns[key].values()) for key, partner in partners.items()]
        })


report_sxw.report_sxw(
    'report.mailrun','stock.move','addons/mailrun/report/mailrun.rml', parser=mailrun
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
