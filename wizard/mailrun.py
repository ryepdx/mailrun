import time
from calendar import monthrange
from datetime import date, timedelta
from openerp import SUPERUSER_ID
from openerp.osv import orm, fields

class wiz_mailrun(orm.TransientModel):
    _name = 'mailrun.wizard'

    def _get_dates(self, cr, uid, context=None):
        today = time.strftime('%Y-%m-%d')
        cr.execute('SELECT DISTINCT mailrun_date from stock_move '\
                   'WHERE mailrun_date IS NOT NULL AND mailrun_date != %s '\
                   'ORDER BY mailrun_date DESC LIMIT 10', [today]
        )
        dates = [t[0] for t in cr.fetchall()]
        return [(today, 'Today')] + [(d, d) for d in dates]

    _columns = {
        'date': fields.selection(_get_dates, 'Date', required=True, method=True, size=10)
    }

    def generate_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        data = self.browse(cr, uid, ids[0], context=context)
        context['date'] = data.date

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'mailrun',
            'context': context,
            'datas': {
                'model': 'ir.ui.view',
                'id': ids and ids[0] or False,
                'ids': ids,
                'report_type': 'pdf'
            },
            'nodestroy': False
        }

wiz_mailrun()