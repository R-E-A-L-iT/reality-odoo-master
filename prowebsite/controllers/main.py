# -*- coding: utf-8 -*-
import base64
import re

from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

# Customer-facing pricelists are named EXACTLY by these flag emojis.
CAD_PRICELIST_NAME = '🇨🇦'
USD_PRICELIST_NAME = '🇺🇸'

# Public "notify me" mailing lists this endpoint is allowed to subscribe
# visitors to, keyed by the `data-list-key` the page passes in (never a raw
# mailing.list id — see notify_signup below). Add one entry per new product
# that needs a pre-launch interest list.
NOTIFY_SIGNUP_LISTS = {
    'omni360': 21,
}

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class ProwebsiteController(http.Controller):

    @http.route(
        '/omnigo/sync_pricelist',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def sync_pricelist(self, **kw):
        """Report the resolved pricelist and align the cart to it.

        The OmniGO page renders its price server-side (QWeb) and updates on a
        full reload, so the pricelist is resolved entirely by
        proproduct.get_current_pricelist (region cookie -> geo-IP fallback).
        This handler must NOT mutate the session; it only reports the resolved
        pricelist (so the JS can show the currency badge) and aligns any
        existing cart order before the following /shop/cart/update_json.
        """
        pricelist = request.website.get_current_pricelist()

        try:
            order = request.website.sale_get_order(force_create=False)
            if order and order.pricelist_id.id != pricelist.id:
                _logger.info(
                    "[omnigo] Updating cart %s pricelist %s → %s",
                    order.name, order.pricelist_id.display_name, pricelist.display_name,
                )
                order.sudo().write({'pricelist_id': pricelist.id})
                try:
                    order.sudo()._recompute_prices()
                except AttributeError:
                    order.sudo()._recompute_all_prices()
        except Exception as e:
            _logger.warning("[omnigo] Could not update cart pricelist: %s", e)

        pl_sudo = pricelist.sudo()
        return {
            'pricelist_id': pricelist.id,
            'pricelist_name': pl_sudo.display_name,
            'currency': pl_sudo.currency_id.name,
        }

    # ------------------------------------------------------------------
    #  Derek's Red Book — capture a valuation request as a CRM opportunity
    # ------------------------------------------------------------------
    def _drb_resolve_team(self):
        """The website sales team (its members get the round-robin lead)."""
        website = request.website.sudo()
        team = False
        # Preferred: the website's configured default sales team (website_crm).
        if 'crm_default_team_id' in website._fields and website.crm_default_team_id:
            team = website.crm_default_team_id
        Team = request.env['crm.team'].sudo()
        if not team:
            team = Team.search([('name', 'ilike', 'website')], limit=1)
        if not team:
            team = Team.search([], order='id', limit=1)
        return team

    def _drb_pick_salesperson(self, team):
        """Round-robin: the team member currently carrying the fewest leads."""
        website = request.website.sudo()
        members = team.member_ids if team else request.env['res.users']
        if members:
            Lead = request.env['crm.lead'].sudo()
            return min(members, key=lambda u: Lead.search_count([('user_id', '=', u.id)]))
        if 'crm_default_user_id' in website._fields and website.crm_default_user_id:
            return website.crm_default_user_id
        return team.user_id if team and team.user_id else request.env['res.users']

    @http.route(
        '/dereks_red_book/submit',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def dereks_red_book_submit(self, **kw):
        """Create a CRM opportunity from a Derek's Red Book valuation."""
        def yesno(v):
            return ('Oui' if v else 'Non') if kw.get('lang', '').startswith('fr') else ('Yes' if v else 'No')

        email = (kw.get('email') or '').strip()
        if not email:
            return {'success': False, 'error': 'missing_email'}

        model_label = (kw.get('model_label') or kw.get('model_key') or 'Scanner').strip()
        serial = (kw.get('serial') or '').strip()
        currency = (kw.get('currency') or '').strip()

        def money(v):
            try:
                return '{} {:,.0f}'.format(currency, float(v))
            except (TypeError, ValueError):
                return str(v or '')

        description = (
            "<p><b>Derek's Red Book valuation request</b></p>"
            "<ul>"
            "<li>Scanner: %s</li>"
            "<li>Serial #: %s</li>"
            "<li>Original purchase date: %s</li>"
            "<li>Age: %s</li>"
            "<li>Currency: %s</li>"
            "<li>Estimated current market value: %s</li>"
            "<li>Trade-in value: %s</li>"
            "<li>Buyback (store credit): %s</li>"
            "<li>Cash offer: %s</li>"
            "<li>Active warranty/CCP: %s &nbsp; Calibration cert: %s &nbsp; Accessories intact: %s</li>"
            "</ul>"
        ) % (
            model_label, serial or '-', kw.get('purchase_date') or '-', kw.get('age') or '-',
            currency or '-', money(kw.get('market_value')), money(kw.get('trade_in')),
            money(kw.get('store_credit')), money(kw.get('cash')),
            yesno(kw.get('warranty')), yesno(kw.get('calibration')), yesno(kw.get('accessories')),
        )

        try:
            team = self._drb_resolve_team()
            user = self._drb_pick_salesperson(team)
        except Exception as e:
            _logger.warning("[dereks_red_book] team/salesperson resolution failed: %s", e)
            team = request.env['crm.team']
            user = request.env['res.users']

        vals = {
            'name': "Derek's Red Book — %s%s" % (model_label, ' (S/N %s)' % serial if serial else ''),
            'type': 'opportunity',
            'contact_name': (kw.get('full_name') or '').strip() or False,
            'partner_name': (kw.get('company') or '').strip() or False,
            'email_from': email,
            'phone': (kw.get('phone') or '').strip() or False,
            'description': description,
            'team_id': team.id if team else False,
            'user_id': user.id if user else False,
        }
        try:
            vals['expected_revenue'] = float(kw.get('cash'))
        except (TypeError, ValueError):
            pass

        try:
            lead = request.env['crm.lead'].sudo().create(vals)
        except Exception as e:
            _logger.exception("[dereks_red_book] lead creation failed: %s", e)
            return {'success': False, 'error': 'create_failed'}

        if not team:
            _logger.warning("[dereks_red_book] lead %s created with no sales team resolved", lead.id)

        # Remember which leads this visitor created, so the follow-up PDF upload can
        # only attach to its own lead (not an arbitrary guessed id).
        created = list(request.session.get('drb_created_leads') or [])
        created.append(lead.id)
        request.session['drb_created_leads'] = created

        return {'success': True, 'lead_id': lead.id}

    @http.route(
        '/dereks_red_book/attach',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def dereks_red_book_attach(self, **kw):
        """Attach the client-rendered PDF report to its CRM opportunity."""
        try:
            lead_id = int(kw.get('lead_id') or 0)
        except (TypeError, ValueError):
            return {'success': False, 'error': 'bad_lead_id'}
        pdf_b64 = kw.get('pdf_base64') or ''
        filename = (kw.get('filename') or "Dereks-Red-Book.pdf").strip()
        if not lead_id or not pdf_b64:
            return {'success': False, 'error': 'missing_data'}

        # Only allow attaching to a lead created by this same browser session.
        if lead_id not in (request.session.get('drb_created_leads') or []):
            return {'success': False, 'error': 'not_authorized'}

        try:
            data = base64.b64decode(pdf_b64)
        except Exception:
            return {'success': False, 'error': 'bad_pdf'}
        if not data[:5].startswith(b'%PDF'):
            return {'success': False, 'error': 'not_a_pdf'}
        if len(data) > 15 * 1024 * 1024:      # 15 MB guard
            return {'success': False, 'error': 'too_large'}

        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists():
            return {'success': False, 'error': 'no_lead'}

        attachment = request.env['ir.attachment'].sudo().create({
            'name': filename,
            'datas': pdf_b64,
            'type': 'binary',
            'mimetype': 'application/pdf',
            'res_model': 'crm.lead',
            'res_id': lead.id,
        })
        try:
            lead.message_post(
                body="Derek's Red Book evaluation report attached.",
                attachment_ids=[attachment.id],
            )
        except Exception as e:
            _logger.warning("[dereks_red_book] could not post PDF to chatter: %s", e)
        return {'success': True, 'attachment_id': attachment.id}

    # ------------------------------------------------------------------
    #  RTC demo request — capture a demo booking as a CRM opportunity
    # ------------------------------------------------------------------
    def _sales_team(self):
        """The 'Sales' sales team (its members get the round-robin demo lead).

        Resolved by name so a site-owner rename doesn't silently misroute:
        exact 'Sales' first, then a fuzzy match, then the first team as a
        last resort (mirrors _drb_resolve_team's defensiveness).
        """
        Team = request.env['crm.team'].sudo()
        team = Team.search([('name', '=', 'Sales')], limit=1)
        if not team:
            team = Team.search([('name', 'ilike', 'sales')], limit=1)
        if not team:
            team = Team.search([], order='id', limit=1)
        return team

    @http.route(
        '/rtc_demo/submit',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def rtc_demo_submit(self, **kw):
        """Create a CRM opportunity from an RTC demo request and assign it
        round-robin to a member of the Sales sales team."""
        email = (kw.get('email') or '').strip()
        if not email or not _EMAIL_RE.match(email):
            return {'success': False, 'error': 'invalid_email'}

        full_name = (kw.get('full_name') or '').strip()
        company = (kw.get('company') or '').strip()
        phone = (kw.get('phone') or '').strip()
        week = (kw.get('week') or '').strip()
        location = (kw.get('location') or '').strip()
        product = (kw.get('product') or 'RTC').strip()
        notes = (kw.get('notes') or '').strip()

        description = (
            "<p><b>RTC demo request</b></p>"
            "<ul>"
            "<li>Preferred week: %s</li>"
            "<li>Location: %s</li>"
            "<li>Product of interest: %s</li>"
            "<li>Company: %s</li>"
            "<li>Phone: %s</li>"
            "<li>Email: %s</li>"
            "%s"
            "</ul>"
        ) % (
            week or '-', location or '-', product or '-',
            company or '-', phone or '-', email,
            ('<li>Notes: %s</li>' % notes) if notes else '',
        )

        try:
            team = self._sales_team()
            user = self._drb_pick_salesperson(team)
        except Exception as e:
            _logger.warning("[rtc_demo] team/salesperson resolution failed: %s", e)
            team = request.env['crm.team']
            user = request.env['res.users']

        title = 'RTC Demo Request — %s' % (company or full_name or email)
        if location:
            title += ' (%s)' % location

        vals = {
            'name': title,
            'type': 'opportunity',
            'contact_name': full_name or False,
            'partner_name': company or False,
            'email_from': email,
            'phone': phone or False,
            'description': description,
            'team_id': team.id if team else False,
            'user_id': user.id if user else False,
        }

        try:
            lead = request.env['crm.lead'].sudo().create(vals)
        except Exception as e:
            _logger.exception("[rtc_demo] lead creation failed: %s", e)
            return {'success': False, 'error': 'create_failed'}

        if not team:
            _logger.warning("[rtc_demo] lead %s created with no sales team resolved", lead.id)

        return {'success': True, 'lead_id': lead.id}

    @http.route(
        '/omnigo/get_pricelists',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def get_pricelists(self, **kw):
        """Return the CA / US pricelists for the header currency switcher.

        Resolved by exact flag-emoji name (matching proproduct/models/website.py)
        and marked active against the visitor's current region (cookie or geo-IP).
        """
        website = request.website
        try:
            current_region = website.proproduct_region()  # 'US' / 'CA'
        except Exception:
            current_region = None

        Pricelist = request.env['product.pricelist'].sudo()
        website_domain = ['|', ('website_id', '=', False), ('website_id', '=', website.id)]

        result = []
        for region, name, currency in [
            ('CA', CAD_PRICELIST_NAME, 'CAD'),
            ('US', USD_PRICELIST_NAME, 'USD'),
        ]:
            pl = Pricelist.search([('name', '=', name)] + website_domain, limit=1)
            if not pl:
                continue
            result.append({
                'id':       pl.id,
                'label':    region,        # 'US' / 'CA' — the pl_region cookie value
                'flag':     name,          # the flag emoji itself
                'currency': currency,
                'active':   region == current_region,
            })
        return result

    @http.route(
        '/prowebsite/notify_signup',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def notify_signup(self, **kw):
        """Subscribe a visitor to a pre-launch product-interest mailing list.

        `list_key` must match an entry in NOTIFY_SIGNUP_LISTS — the client
        never supplies a raw mailing.list id, so this endpoint can't be used
        to subscribe contacts to arbitrary (e.g. internal) lists.
        """
        list_key = (kw.get('list_key') or '').strip()
        list_id = NOTIFY_SIGNUP_LISTS.get(list_key)
        if not list_id:
            return {'success': False, 'error': 'invalid_list'}

        email = (kw.get('email') or '').strip()
        if not email or not _EMAIL_RE.match(email):
            return {'success': False, 'error': 'invalid_email'}

        first_name = (kw.get('first_name') or '').strip()
        last_name = (kw.get('last_name') or '').strip()
        name = ('%s %s' % (first_name, last_name)).strip() or email

        mailing_list = request.env['mailing.list'].sudo().browse(list_id)
        if not mailing_list.exists():
            _logger.warning("[notify_signup] configured list_id %s (key=%s) no longer exists", list_id, list_key)
            return {'success': False, 'error': 'invalid_list'}

        MailingContact = request.env['mailing.contact'].sudo()
        contact = MailingContact.search([('email', '=', email)], limit=1)
        if contact:
            contact.write({'name': name})
        else:
            contact = MailingContact.create({'name': name, 'email': email})

        # Force a fresh, active subscription. The join model backing list_ids
        # has been renamed across Odoo versions (mailing.contact.subscription
        # / mailing.subscription, with differing field names), so rather than
        # querying it directly we only touch the stable public API: unlink
        # first (clears any earlier opt_out on this list), then link — a
        # freshly (re)created subscription row is opted-in by default.
        if list_id in contact.list_ids.ids:
            contact.write({'list_ids': [(3, list_id)]})
        contact.write({'list_ids': [(4, list_id)]})

        return {'success': True}
