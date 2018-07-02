# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    This module copyright (C) 2016 hulshof#    #
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

from openerp import models, fields, api, _
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.queue_job.exception import FailedJobError

class claim(models.Model):
    _name = "claim"
    _inherit = ['mail.thread']
    _description = "Claim"
    _order = "id desc"
    _track = {
        'Teruggaaf': {
        },
    }

    @api.one
    @api.depends('claim_line.amount_nett', 'claim_line.amount_tax', 'claim_line.vat', 'claim_line.energy_tax_e',
                 'claim_line.durable_tax_g', 'claim_line.energy_tax_g', 'claim_line.durable_tax_e','claim_line.amount_total',
                 'tax_return_line.amount_tax_return_total',
                 'cost_line.amount_cost', 'payment_line.amount_payment'
                 )
    def _compute_amount(self):

        vat = sum(line.vat for line in self.claim_line)
        energy_tax_e = sum(line.energy_tax_e for line in self.claim_line)
        durable_tax_e = sum(line.durable_tax_e for line in self.claim_line)
        energy_tax_g = sum(line.energy_tax_g for line in self.claim_line)
        durable_tax_g = sum(line.durable_tax_g for line in self.claim_line)
        self.amount_nett = sum(line.amount_nett for line in self.claim_line)
        self.amount_vat = vat if vat > 0 else 0
        self.amount_energy_tax_e = energy_tax_e if energy_tax_e > 0 else 0
        self.amount_durable_tax_e = durable_tax_e if durable_tax_e > 0 else 0
        self.amount_energy_tax_g = energy_tax_g if energy_tax_g > 0 else 0
        self.amount_durable_tax_g = durable_tax_g if durable_tax_g > 0 else 0
        self.amount_tax_claim = self.amount_vat + self.amount_energy_tax_e + self.amount_durable_tax_e + \
                self.amount_energy_tax_g + self.amount_durable_tax_g
        self.amount_tax_orig = sum(line.amount_tax for line in self.claim_line)
        self.amount_cost = sum(line.amount_cost for line in self.cost_line)
        self.amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
        amount_tax_return_ee = sum(line.energy_tax_e_return for line in self.tax_return_line)
        amount_tax_return_de = sum(line.durable_tax_e_return for line in self.tax_return_line)
        amount_tax_return_eg = sum(line.energy_tax_g_return for line in self.tax_return_line)
        amount_tax_return_dg = sum(line.durable_tax_g_return for line in self.tax_return_line)
        amount_tax_return_vat = sum(line.vat_return for line in self.tax_return_line)
        amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
#        self.amount_total = sum(line.amount_total for line in self.claim_line)
        self.amount_payment = sum(line.amount_payment for line in self.payment_line)
        self.nett_tax_total = self.amount_tax_orig + self.amount_nett
        self.grand_total = self.amount_tax_orig + self.amount_cost + self.amount_nett

        part_paid = self.amount_payment - self.amount_cost
        if part_paid <= 0:
            self.amount_payment_cum = 0
        else:
            self.amount_payment_cum = part_paid

        if self.nett_tax_total > 0 and part_paid >= 0:
            part = part_paid / self.nett_tax_total
            part = part if part <= 1 else 1
        else:
            part = 0
        self.amount_nett_cum = self.amount_nett * part

        self.amount_vat_cum = self.amount_vat * (1 - part) - amount_tax_return_vat
        self.amount_energy_tax_e_cum = self.amount_energy_tax_e * (1 - part) - amount_tax_return_ee
        self.amount_durable_tax_e_cum = self.amount_durable_tax_e * (1 - part) - amount_tax_return_de
        self.amount_energy_tax_g_cum = self.amount_energy_tax_g * (1 - part) - amount_tax_return_eg
        self.amount_durable_tax_g_cum = self.amount_durable_tax_g * (1 - part) - amount_tax_return_dg
        self.amount_tax_return_cum = self.amount_vat_cum + self.amount_energy_tax_e_cum + self.amount_durable_tax_e_cum + \
                                     self.amount_energy_tax_g_cum + self.amount_durable_tax_g_cum
        self.amount_tax_cum = self.amount_tax_claim * (1 - part) - amount_tax_return
        self.nett_tax_total_cum = self.nett_tax_total + self.amount_tax_cum
        self.grand_total_cum = self.grand_total - self.amount_payment
        # even kijken wat dit moet worden
        self.amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
        self.amount_tax = self.amount_tax_claim - self.amount_tax_return

    @api.one
    @api.depends('claim_line.due_date'
                 )
    def _compute_last_date(self):
        last_date = []
        for line in self.claim_line:
            last_date.append(line.due_date)
            self.last_line_date = max(last_date) if len(last_date) > 0 else False


    name = fields.Char(
        string=_("Name"),
        required=False,
        translate=True,
        readonly=False,
        size=64,
    )
    batchcode = fields.Char(
        string=_("Afstemcode"),
        required=True,
        translate=False,
        readonly=False,
        size=64
    )
    claim_date = fields.Date(
        string=_("Batch Date"),
        required=True,
        translate=False,
        readonly=True,
    )
    last_line_date = fields.Date(
        string='Last Line Date',
        store=True,
        readonly=True,
        compute='_compute_last_date'
    )
    claim_line = fields.One2many('claim.line', 'claim_id',
        string=_("Claim Line"),
        required=False,
        translate=False,
        readonly=False,
        copy=True
    )
    cost_line = fields.One2many('cost.line', 'claim_id',
        string=_("Cost Lines"),
        required=False,
        translate=False,
        readonly=False,
        copy=True,
        track_visibility='onchange',

    )
    tax_return_line = fields.One2many('tax.return.line', 'claim_id',
        string=_("Tax Return Line"),
        required=False,
        translate=False,
        readonly=False,
        copy=True,
        track_visibility = 'onchange',
    )
    payment_line = fields.One2many('payment.line', 'claim_id',
        string=_("Payment Line"),
        required=False,
        translate=False,
        readonly=False,
        copy=True,
        track_visibility='onchange',
    )
    zpartner = fields.Char(
        string=_("Debtor"),
        required=True,
        translate=False,
        readonly=False,
        size=64,
    )
    partnersrt = fields.Selection([
            ('CM','Consument'),
            ('KZM','Kein Zakelijk'),
        ],
        string='Debtor Type',
        required=True,
        translate=False,
        readonly=False
    )
    contrrek = fields.Char(
        string=_("Contract"),
        required=True,
        translate=False,
        readonly=False,
        size=64,
    )
    tax_return_sent = fields.Boolean(
        string=_("Teruggaaf"),
        #readonly=True,
        default=False,
        copy=False,
        help="It indicates that the tax return has been sent.",
        track_visibility = 'onchange',
        )
    bankruptcy = fields.Boolean(
        string=_("Faillissement"),
        # readonly=True,
        default=False,
        copy=False,
        help="It indicates that the debtor is in bankruptcy.",
        track_visibility='onchange',
    )
    wsnp = fields.Boolean(
        string=_("WSNP"),
        # readonly=True,
        default=False,
        copy=False,
        help="It indicates that the debtor is in WSNP.",
        track_visibility='onchange',
    )
    sued = fields.Boolean(
        string=_("Dagvaarding"),
        # readonly=True,
        default=False,
        copy=False,
        help="It indicates that the debtor has been sued.",
        track_visibility='onchange',
    )
    discharge = fields.Boolean(
        string=_("Finale Kwijting"),
        # readonly=True,
        default=False,
        copy=False,
        help="It indicates that agreement with the debtor has been reached with discharge.",
        track_visibility='onchange',
    )
    comment = fields.Text('Additional Information'
        )
    amount_nett = fields.Float(
        string='Nett Claim Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax_orig = fields.Float(
        string='Tax Amount Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax_claim = fields.Float(
        string='Tax Claim Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_vat = fields.Float(
        string='VAT Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_energy_tax_e = fields.Float(
        string='Energy Tax E Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_energy_tax_g = fields.Float(
        string='Energy Tax G Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_durable_tax_e = fields.Float(
        string='Durable Tax E Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_durable_tax_g = fields.Float(
        string='Durable Tax G Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_total = fields.Float(
        string='Claim Original Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    nett_tax_total = fields.Float(
        string='Nett plus Tax Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    grand_total = fields.Float(
        string='Claim Grand Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax_return = fields.Float(
        string='Tax Return',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax = fields.Float(
        string='Tax Total',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_cost = fields.Float(
        string='Collection Cost',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_payment = fields.Float(
        string='Payment',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_nett_cum = fields.Float(
        string='Nett Claim Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax_orig_cum = fields.Float(
        string='Tax Claim Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_vat_cum = fields.Float(
        string='VAT Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_energy_tax_e_cum = fields.Float(
        string='Energy Tax E Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_energy_tax_g_cum = fields.Float(
        string='Energy Tax G Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_durable_tax_e_cum = fields.Float(
        string='Durable Tax E Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_durable_tax_g_cum = fields.Float(
        string='Durable Tax G Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_total_cum = fields.Float(
        string='Claim Original Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    nett_tax_total_cum = fields.Float(
        string='Nett plus Tax Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    grand_total_cum = fields.Float(
        string='Claim Grand Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount'
    )
    amount_tax_return_cum = fields.Float(
        string='Tax Return Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility = 'always',
    )
    amount_tax_cum = fields.Float(
        string='Tax Total Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='always',
    )
    amount_cost_cum = fields.Float(
        string='Collection Cost Cum',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='always',
    )
    amount_payment_cum = fields.Float(
        string='Payment',
        digits=dp.get_precision('claim'),
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='always',
    )

    @job
    @api.multi
    def generate_tax_split_lines_jq(self, declaration, eta, size):
        chunk = False
        for claim in self:
            chunk = claim if not chunk else chunk | claim
            if len(chunk) < size:
                continue
            chunk.with_delay(eta=eta).generate_tax_lines_from_claim(declaration)
            chunk = False
                lines = recordset.filtered(lambda r: r.order_id.partner_invoice_id.id == partner.id)
                if len(lines) > size:
                    published_customer = lines.filtered('order_id.published_customer').mapped(
                        'order_id.published_customer')
                    for pb in published_customer:
                        claimlinespb = lines.filtered(lambda r: r.order_id.published_customer.id == pb.id)
                        chunk = linespb if not chunk else chunk | linespb
                        if len(chunk) < size:
                            continue
                        self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)
                        chunk = False
                    remaining_lines = lines.filtered(lambda r: not r.order_id.published_customer)
                    chunk = remaining_lines if not chunk else chunk | remaining_lines
                    self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)
                else:
                    chunk = lines if not chunk else chunk | lines
                    if len(chunk) < size:
                        continue
                    self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)
                    chunk = False
            if chunk:
                self.with_delay(eta=eta).make_invoices_job_queue(inv_date, post_date, chunk)

    @job
    @api.multi
    def generate_tax_lines_from_claim(self, declaration):
        context = self._context
        cutoff_type = context.get('cutoff', False)
        for claim in self:
            if cutoff_type == 'last_line':
                claim.make_tax_line_from_claim(declaration)
            else:
                claim.make_tax_line_from_claim_lines(declaration)

    @api.multi
    def make_tax_line_from_claim(self, declaration):
        self.ensure_one()
        if self.amount_tax_cum == 0:
            return
        vals = {
            'claim_id': self.id,
            'declaration_id': declaration.id,
            'date_tax_request': declaration.date_tax_request,
            'energy_tax_e_return': self.amount_energy_tax_e_cum,
            'energy_tax_g_return': self.amount_energy_tax_g_cum,
            'vat_return': self.amount_vat_cum,
            'durable_tax_e_return': self.amount_durable_tax_e_cum,
            'durable_tax_g_return': self.amount_durable_tax_g_cum,
            'docsoort': 'TR' if self.amount_tax_cum >= 0 else 'TD'
        }
        return self.env['tax.return.line'].create(vals)

    @api.multi
    def make_tax_line_from_claim_lines(self, declaration):
        self.ensure_one()
        if self.last_line_date <= declaration.to_invoice_date:
            self.make_tax_line_from_claim(declaration)
        else:
            claim_lines = self.env['claim.line'].search(
                [('due_date', '<=', declaration.to_invoice_date), ('claim_id', '=', self.id)])
            vals = self.compute_amount(claim_lines)
            vals['declaration_id'] = declaration.id
            vals['date_tax_request'] = declaration.date_tax_request
            self.env['tax.return.line'].create(vals)
        return True

    def compute_amount(self, claim_line):

        vat = sum(line.vat for line in claim_line)
        energy_tax_e = sum(line.energy_tax_e for line in claim_line)
        durable_tax_e = sum(line.durable_tax_e for line in claim_line)
        energy_tax_g = sum(line.energy_tax_g for line in claim_line)
        durable_tax_g = sum(line.durable_tax_g for line in claim_line)
        var_amount_nett = sum(line.amount_nett for line in claim_line)
        var_amount_vat = vat if vat > 0 else 0
        var_amount_energy_tax_e = energy_tax_e if energy_tax_e > 0 else 0
        var_amount_durable_tax_e = durable_tax_e if durable_tax_e > 0 else 0
        var_amount_energy_tax_g = energy_tax_g if energy_tax_g > 0 else 0
        var_amount_durable_tax_g = durable_tax_g if durable_tax_g > 0 else 0
        var_amount_tax_claim = var_amount_vat + var_amount_energy_tax_e + var_amount_durable_tax_e + \
                               var_amount_energy_tax_g + var_amount_durable_tax_g
        var_amount_tax_orig = sum(line.amount_tax for line in claim_line)
        var_amount_cost = sum(line.amount_cost for line in self.cost_line)
        var_amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
        amount_tax_return_ee = sum(line.energy_tax_e_return for line in self.tax_return_line)
        amount_tax_return_de = sum(line.durable_tax_e_return for line in self.tax_return_line)
        amount_tax_return_eg = sum(line.energy_tax_g_return for line in self.tax_return_line)
        amount_tax_return_dg = sum(line.durable_tax_g_return for line in self.tax_return_line)
        amount_tax_return_vat = sum(line.vat_return for line in self.tax_return_line)
        amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
        #        self.amount_total = sum(line.amount_total for line in self.claim_line)
        var_amount_payment = sum(line.amount_payment for line in self.payment_line)
        var_nett_tax_total = var_amount_tax_orig + var_amount_nett
        var_grand_total = var_amount_tax_orig + var_amount_cost + var_amount_nett

        part_paid = var_amount_payment - var_amount_cost
        if part_paid <= 0:
            var_amount_payment_cum = 0
        else:
            var_amount_payment_cum = part_paid

        if var_nett_tax_total > 0 and part_paid >= 0:
            part = part_paid * var_nett_tax_total / self.nett_tax_total
            part = part if part <= 1 else 1
        else:
            part = 0
        var_amount_nett_cum = var_amount_nett * part

        var_amount_vat_cum = var_amount_vat * (1 - part) - amount_tax_return_vat
        var_amount_energy_tax_e_cum = var_amount_energy_tax_e * (1 - part) - amount_tax_return_ee
        var_amount_durable_tax_e_cum = var_amount_durable_tax_e * (1 - part) - amount_tax_return_de
        var_amount_energy_tax_g_cum = var_amount_energy_tax_g * (1 - part) - amount_tax_return_eg
        var_amount_durable_tax_g_cum = var_amount_durable_tax_g * (1 - part) - amount_tax_return_dg
        var_amount_tax_return_cum = var_amount_vat_cum + var_amount_energy_tax_e_cum + var_amount_durable_tax_e_cum + \
                                    var_amount_energy_tax_g_cum + var_amount_durable_tax_g_cum
        var_amount_tax_cum = var_amount_tax_claim * (1 - part) - amount_tax_return
        var_nett_tax_total_cum = var_nett_tax_total + var_amount_tax_cum
        var_grand_total_cum = var_grand_total - var_amount_payment
        # even kijken wat dit moet worden
        var_amount_tax_return = sum(line.amount_tax_return_total for line in self.tax_return_line)
        var_amount_tax = var_amount_tax_claim - var_amount_tax_return
        vals = {
            'claim_id': self.id,
            'energy_tax_e_return': var_amount_energy_tax_e_cum,
            'energy_tax_g_return': var_amount_energy_tax_g_cum,
            'vat_return': var_amount_vat_cum,
            'durable_tax_e_return': var_amount_durable_tax_e_cum,
            'durable_tax_g_return': var_amount_durable_tax_g_cum,
            'docsoort': 'TR' if var_amount_tax_cum >= 0 else 'TD'
        }
        return vals
