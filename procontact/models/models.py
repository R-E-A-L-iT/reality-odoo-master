# -*- coding: utf-8 -*-

import ast
import base64
import difflib
import logging
import re
import unicodedata

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class individual(models.Model):
    _inherit = 'res.partner'

    linkedin_link = fields.Char(
        string="LinkedIn link"
    )

    is_customer = fields.Boolean(
        string="Is Customer?",
        default=True,
        help="Check this box if this contact is a customer."
    )

    has_had_contact = fields.Boolean(
        string="Has had contact",
        default=True,
        help="Whether we have had contact with this person/company."
    )

    first_name = fields.Char(string="First Name", compute="_compute_first_last_names", store=False)
    last_name = fields.Char(string="Last Name", compute="_compute_first_last_names", store=False)

    parent_company_id = fields.Many2one(
        comodel_name="res.partner",
        string="Parent Company",
        domain="[('is_company', '=', True), ('id', '!=', id)]",
        help="Select the parent company for this company contact."
    )

    # NEW: Branches list (companies that point to this company as parent)
    branch_company_ids = fields.One2many(
        comodel_name="res.partner",
        inverse_name="parent_company_id",
        string="Branches",
        domain=[('is_company', '=', True)],
        readonly=True,
        help="Companies that have this company set as their Parent Company."
    )

    def _compute_first_last_names(self):
        for rec in self:
            parts = (rec.name or "").strip().split()
            rec.first_name = parts[0] if parts else ''
            rec.last_name = parts[-1] if len(parts) > 1 else rec.first_name

    # ------------------------------------------------------------------
    # One-shot surveyor-contacts maintenance (called by an ir.cron).
    # ------------------------------------------------------------------
    # (email, target company name) pairs. Emails are normalised at use.
    _SURVEYOR_EMAIL_COMPANY = [
        ("abdelhafid.benlafqih@environnement.gouv.qc.ca", "Ministère de l'Environnement"),
        ("alain@bellemareag.com", "Bellemare et Associés"),
        ("alaindaze@dazeneveu.ca", "Dazé Neveu Arpenteurs-Géomètres"),
        ("athiffault@groupesr.ca", "Groupe SR Arpenteurs-Géomètres inc."),
        ("amasse@gbrsat.ca", "Groupe Barbe & Robidoux.SAT"),
        ("paradis.alexandre2@hydroquebec.com", "Hydro-Québec"),
        ("andre.roy@cegeplimoilou.ca", "Cégep Limoilou"),
        ("maroisa@abag.qc.ca", "Arseneault Bourbonnais inc., arpenteurs-géomètres"),
        ("barbara.gallant@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("benoit.dermine@montreal.ca", "Ville de Montréal"),
        ("benoit@bpeloquin.ca", "Benoît Péloquin Arpenteur-Géomètre inc."),
        ("billy.rioux@arpentage.com", "Giroux Arpentage (Groupe Giroux), arpenteurs-géomètres"),
        ("barbour@grondinag.com", "Grondin et associés, arpenteurs-géomètres Inc."),
        ("bruno.foster@groupecadoret.com", "Groupe Cadoret"),
        ("camille.ouellet-bernatchez@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("caroline.absi@atkinsrealis.com", "AtkinsRéalis"),
        ("carsenault@groupesr.ca", "Groupe SR Arpenteurs-Géomètres inc."),
        ("cedric.lariviere@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("chantal.arguin@groupetrifide.com", "Groupe Trifide inc."),
        ("c.arseneau@micheldube.com", "DUBÉ ARPENTEURS-GÉOMÈTRES INC."),
        ("c.beaudin@btag.ca", "Bérard Tremblay arpenteurs-géomètres inc."),
        ("dgaboury@groupegtg.ca", "Groupe GTG (Girard Tremblay Gilbert) arpenteurs-géomètres"),
        ("dtheriault@ecceterra.com", "Ecce Terra arpenteurs-géomètres"),
        ("danielle.latulippe@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("david@barilgeo.com", "Baril Géomatique inc."),
        ("dl.tremblay@dltarpenteur.com", "DLT Arpentage (Denis L. Tremblay)"),
        ("d.moreau@btag.ca", "Bérard Tremblay arpenteurs-géomètres inc."),
        ("dominique@malogingras.ca", "Malo Gingras arpenteurs-géomètres inc."),
        ("lapointe.doris@gatineau.ca", "Ville de Gatineau"),
        ("eric.groulx@canada.ca", "Gouvernement du Canada"),
        ("eroyer@ag-360.ca", "AG360 arpenteurs-géomètres"),
        ("felix@vertical-ag.com", "Vertical arpenteurs-géomètres"),
        ("francois.bernard@bromont.com", "Ville de Bromont"),
        ("francois.bigras@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("francois.gendron@picardetpicard.com", "Picard et Picard arpenteurs-géomètres"),
        ("f.labrecque@groupevrsb.com", "Groupe VRSB, arpenteurs-géomètres"),
        ("f.belleville@btag.ca", "Bérard Tremblay arpenteurs-géomètres inc."),
        ("fmessier@geolocation.ca", "Géolocation (Pagé-Leclair), société d'arpenteurs-géomètres"),
        ("fred@lortieag.com", "Lortie arpenteurs-géomètres"),
        ("f.painchaud@blpag.com", "Géomatique BLP arpenteurs-géomètres inc."),
        ("fvaillancourt@metrica.ag", "Métrica, arpenteurs-géomètres"),
        ("g.lapointe@mpmag.com", "MPMAG & Associés inc. (Boréal Arpenteurs-Géomètres)"),
        ("gsarancibia@outlook.com", "Gabriel Arancibia, a.-g., consultant"),
        ("joncas.gerard@cgocable.ca", "Gérard Joncas, arpenteur-géomètre"),
        ("gletourneau@rochetteetlahaie.ca", "Rochette et Lahaie arpenteurs-géomètres"),
        ("gustave.guilbert@sgts.ca", "Groupe SGTS, Gendron Lefebvre Arpenteurs-Géomètres"),
        ("gbanville@jpgrondin.com", "Grondin & Associés arpenteurs-géomètres inc."),
        ("habdou@arpenteurs.ca", "Vital Roy, arpenteurs-géomètres inc."),
        ("hubert.carpentier@asdag.ca", "Alary, St-Pierre & Durocher, arpenteurs-géomètres inc."),
        ("hlaferriere@arguin-ag.com", "Arguin et associés, arpenteurs-géomètres"),
        ("h.lefrancois@groupevrsb.com", "Groupe VRSB, arpenteurs-géomètres"),
        ("isabelle@bachandag.com", "Bachand et Associés inc."),
        ("ifilipovic@arpentagecds.com", "Arpentage Côte-du-Sud inc."),
        ("jdaniel@marcotte-ag.com", "Marcotte arpenteurs-géomètres"),
        ("j.drainville@mensores.ca", "Mensorès (expertise foncière)"),
        ("jnormand@chiassonthomas.com", "Chiasson & Thomas arpenteurs-géomètres"),
        ("jfaube@aubeag.com", "Aubé et Associés arpenteurs-géomètres inc."),
        ("jean.leboeuf@tpsgc-pwgsc.gc.ca", "Services publics et Approvisionnement Canada"),
        ("jean-francois.proulx@geoposition.ca", "Géoposition arpenteurs-géomètres inc."),
        ("jlfortin@arpenteurs.ca", "Vital Roy, arpenteurs-géomètres inc."),
        ("jean-michel.lavoie2@environnement.gouv.qc.ca", "Ministère de l'Environnement"),
        ("jean-sebastien.chaume@montreal.ca", "Ville de Montréal"),
        ("jricher@ctr-ag.com", "Caouette Thériault Renaud, arpenteurs-géomètres"),
        ("j.sirois-charron@btag.ca", "Bérard Tremblay arpenteurs-géomètres inc."),
        ("jonathan.calve@cansel.ca", "Cansel"),
        ("jonathan.roy@h4geo.com", "H4G Géomatique"),
        ("jonathan.hamel@carrierag.ca", "Carrier arpenteurs-géomètres"),
        ("jonathan.maltais@labergeguerin.ca", "Laberge Guérin (LGA) arpenteurs-géomètres"),
        ("jferland@groupesr.ca", "Groupe SR Arpenteurs-Géomètres inc."),
        ("laurendeauj@abag.qc.ca", "Arseneault Bourbonnais inc., arpenteurs-géomètres"),
        ("jlambertag@lsag-arpenteurs.com", "Leblanc Services d'Arpentage et Géomatique inc."),
        ("ange.amon@geoposition.ca", "Géoposition arpenteurs-géomètres inc."),
        ("knellis@ecceterra.com", "Ecce Terra arpenteurs-géomètres"),
        ("info@isabellearpenteurs.com", "Laurier Isabelle, arpenteur-géomètre"),
        ("larseneault@arpenteur-im.ca", "Arseneault Cyr, arpenteures-géomètres inc."),
        ("louis.daoust@horizonarpenteurs.com", "Horizon arpenteurs-géomètres"),
        ("lpfouquette@labre.qc.ca", "Labre et associés, arpenteurs-géomètres"),
        ("lbd@geosag.com", "Géosag, arpenteurs-géomètres (Taillon et Savard)"),
        ("luchebert@gagnonhebert.com", "Gagnon Hébert arpenteurs-géomètres"),
        ("luc.thibodeau@tpsgc.gc.ca", "Services publics et Approvisionnement Canada"),
        ("mdufour@ecceterra.com", "Ecce Terra arpenteurs-géomètres"),
        ("mjarry@bjgarpenteurs.com", "Groupe BJG Arpenteurs-Géomètres"),
        ("mlachapelle@geoterra.ca", "Geoterra arpenteurs-géomètres inc."),
        ("beauregard.marc-andre2@hydroquebec.com", "Hydro-Québec"),
        ("maboucher@ecceterra.com", "Ecce Terra arpenteurs-géomètres"),
        ("marcel.cadoret@groupecadoret.com", "Groupe Cadoret"),
        ("marie-eve.nadeau@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("roch.mathieu@videotron.ca", "Roch Mathieu, arpenteur-géomètre inc."),
        ("martin.bournival@environnement.gouv.qc.ca", "Ministère de l'Environnement"),
        ("martin.larocque@groupecivitas.com", "Groupe Civitas inc."),
        ("marysep@mp-ag.com", "Maryse Phaneuf, arpenteure-géomètre"),
        ("mvanasse@murrayvanasse.com", "Murray Vanasse arpenteurs-géomètres"),
        ("mafournier@arpentage.ca", "Nadeau, Fournier Arpenteurs-Géomètres inc."),
        ("m.daousthebert@groupevrsb.com", "Groupe VRSB, arpenteurs-géomètres"),
        ("mdrouin@ecceterra.com", "Ecce Terra arpenteurs-géomètres"),
        ("m.varin@arpentagemv.ca", "Arpentage MV inc."),
        ("maylis.casenave@sherbrooke.ca", "Ville de Sherbrooke"),
        ("michel.picard@picardetpicard.com", "Picard et Picard arpenteurs-géomètres"),
        ("lr_ag@ccapcable.com", "(à vérifier)"),
        ("mireille.ruest@tpsgc-pwgsc.gc.ca", "Services publics et Approvisionnement Canada"),
        ("nclauzon@denicourt.ca", "Denicourt arpenteurs-géomètres"),
        ("nathalie.bariteau@environnement.gouv.qc.ca", "Ministère de l'Environnement"),
        ("ngarneau@bjgarpenteurs.com", "Groupe BJG Arpenteurs-Géomètres"),
        ("nlevert@bellnet.ca", "Nathalie Levert, arpenteure-géomètre"),
        ("nicolas.archambault@llag.ca", "Lemieux Lalonde arpenteurs-géomètres inc."),
        ("nsheehy@ssarpenteurs.com", "Simard & Sheehy, arpenteurs-géomètres inc."),
        ("olivier@arpentageoutaouais.com", "Arpentage Outaouais"),
        ("olivier.pelletier@pcarpenteurs.ca", "Pelletier & Couillard, arpenteurs-géomètres"),
        ("pguilbault@pro-ag.qc.ca", "CRGH Arpenteurs-Géomètres inc."),
        ("patrick.descarreaux@descarreaux.com", "Descarreaux arpenteurs-géomètres"),
        ("paul@bpeloquin.ca", "Benoît Péloquin Arpenteur-Géomètre inc."),
        ("philippe.amyot@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("pbelanger@bjgarpenteurs.com", "Groupe BJG Arpenteurs-Géomètres"),
        ("philippe.cote@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("pdallaire@chiassonthomas.com", "Chiasson & Thomas arpenteurs-géomètres"),
        ("pierre@berubeag.ca", "Bérubé arpenteur-géomètre inc."),
        ("pierre.girard@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("placroix@denicourt.ca", "Denicourt arpenteurs-géomètres"),
        ("info@gasconag.com", "Gascon arpenteurs-géomètres"),
        ("pierre-luc@fauchercoulombe.com", "Faucher Coulombe arpenteurs-géomètres"),
        ("pc.beliveau@geolt.ca", "GéoLT arpenteur-géomètre inc."),
        ("pparchambault@agdelta.ca", "Delta arpenteurs-géomètres inc."),
        ("r.marcoux@lemieuxmarcoux.com", "Lemieux Marcoux arpenteurs-géomètres"),
        ("r2gendron@videotron.ca", "Réjean Gendron, arpenteur-géomètre"),
        ("rkatz@katz.qc.ca", "Katz arpenteurs-géomètres"),
        ("rlabelle@lplag.com", "Labelle Pagé-Labelle, arpenteurs-géomètres inc."),
        ("rodrigue.gagnon@ville.saguenay.qc.ca", "Ville de Saguenay"),
        ("roger.mcsween@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("rpoirier@labre.qc.ca", "Labre et associés, arpenteurs-géomètres"),
        ("slavoie@ctr-ag.com", "Caouette Thériault Renaud, arpenteurs-géomètres"),
        ("samuel@agdebeaumont.ca", "De Beaumont Arpenteurs-Géomètres"),
        ("alariese@arpentagemontreal.com", "ARPENTAGE MONTRÉAL INC."),
        ("srheault@denicourt.ca", "Denicourt arpenteurs-géomètres"),
        ("info@beausoleilmelancon.com", "Beausoleil Melançon arpenteurs-géomètres"),
        ("simoncarbonneau1@hotmail.com", "Simon Carbonneau, arpenteur-géomètre"),
        ("simon@arpentageoutaouais.com", "Arpentage Outaouais"),
        ("simon.gignac@montreal.ca", "Ville de Montréal"),
        ("simon.herbinia@ncc-ccn.ca", "Commission de la capitale nationale"),
        ("simon.jourdain@geoposition.ca", "Géoposition arpenteurs-géomètres inc."),
        ("samuel.charette-labbe@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("sophie@groupbelanger.com", "Groupe Bélanger inc."),
        ("sarsenault@arsenaultag.ca", "Arsenault Arpenteurs-géomètres inc."),
        ("stephane.synnott@rrcag.ca", "Roy, Roy & Connolly arpenteurs-géomètres-conseils inc."),
        ("steeve.beaumont@mffp.gouv.qc.ca", "Ministère des Forêts, de la Faune et des Parcs"),
        ("suran.bechir@montreal.ca", "Ville de Montréal"),
        ("sylvain@ayotteag.ca", "Ayotte arpenteurs-géomètres inc."),
        ("shetu@blondinag.com", "Blondin arpenteurs-géomètres"),
        ("s-mbelanger@bellnet.ca", "Sylvain-Marc Bélanger, arpenteur-géomètre"),
        ("sylviefilion@cgocable.ca", "Sylvie Filion, arpenteure-géomètre"),
        ("morin.tristan2@hydroquebec.com", "Hydro-Québec"),
        ("tseguin@rcgag.net", "Rado, Corbeil et Généreux, arpenteurs-géomètres inc."),
        ("veronique.armand@va-ag.ca", "Véronique Armand arpenteure-géomètre inc."),
        ("v.bouchard@micheldube.com", "DUBÉ ARPENTEURS-GÉOMÈTRES INC."),
        ("veronique.racine@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("vincent.patenaude@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("vincent.savard@mrnf.gouv.qc.ca", "Ministère des Ressources naturelles et des Forêts"),
        ("wladyslaw@bellnet.ca", "Wladyslaw Bielawski, arpenteur-géomètre"),
        ("ylemoignan@arpenta.ca", "Arpenta arpenteurs-géomètres"),
        ("archambault.yves@hydro.qc.ca", "Hydro-Québec"),
        ("yvonletourneauag@videotron.ca", "Yvon Létourneau, arpenteur-géomètre"),
        ("zachary.lauziere@sgts.ca", "Groupe SGTS, Gendron Lefebvre Arpenteurs-Géomètres"),
        ("bcouture@arsenaultag.ca", "Arsenault Arpenteurs-géomètres inc."),
        ("jocelyn.allaire@transports.gouv.qc.ca", "Ministère des Transports du Québec"),
        ("marc-andre.auger@longueuil.com", "Ville de Longueuil"),
        ("francois@baronag.ca", "Baron et Frères arpenteurs inc."),
        ("marie-eve@beaulieugeo.com", "Beaulieu Géoservices inc."),
        ("robert@bedardag.com", "Bédard Arpenteurs inc."),
    ]

    # Shared mailbox / ISP / webmail domains: "same domain" does NOT mean
    # "same company", so the domain-grouping step is skipped for these.
    _SURVEYOR_GENERIC_DOMAINS = {
        "videotron.ca", "bellnet.ca", "hotmail.com", "hotmail.ca", "gmail.com",
        "outlook.com", "live.com", "yahoo.com", "yahoo.ca", "sympatico.ca",
        "cgocable.ca", "ccapcable.com", "globetrotter.net", "icloud.com",
    }

    _SURVEYOR_FUZZY_THRESHOLD = 0.75

    @staticmethod
    def _surveyor_norm(text):
        # Lower-case, collapse whitespace, and fold accents so names written
        # with or without diacritics still compare equal.
        folded = unicodedata.normalize("NFKD", text or "")
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        return " ".join(folded.strip().lower().split())

    @staticmethod
    def _surveyor_email_domain(email):
        if not email or "@" not in email:
            return ""
        return email.split("@", 1)[-1].strip().lower()

    def _surveyor_company_of(self):
        """Company (is_company=True) this partner belongs to, else empty rs."""
        self.ensure_one()
        if self.parent_id and self.parent_id.is_company:
            return self.parent_id
        commercial = self.commercial_partner_id
        if commercial and commercial.is_company and commercial.id != self.id:
            return commercial
        return self.env["res.partner"].browse()

    def _cron_one_shot_surveyor_contacts(self):
        """One-shot maintenance: merge duplicate surveyor contacts, mark them
        as individuals with has_had_contact=False, then link each to an
        existing company (by shared e-mail domain, else by fuzzy name match).
        Contacts left without a company are logged for manual review."""
        Partner = self.env["res.partner"].with_context(active_test=False)
        MergeWizard = self.env["base.partner.merge.automatic.wizard"]

        target_company = {}
        for raw_email, company_name in self._SURVEYOR_EMAIL_COMPANY:
            key = self._surveyor_norm(raw_email)
            if key:
                target_company[key] = company_name
        targets = set(target_company)

        # --- Pass 1: locate + merge duplicates + set individual / flag. -----
        groups = {}
        for partner in Partner.search([("email", "!=", False)]):
            key = self._surveyor_norm(partner.email)
            if key in targets:
                groups.setdefault(key, Partner.browse())
                groups[key] |= partner

        merged_emails = 0
        survivors = {}
        for email, partners in groups.items():
            if len(partners) > 1:
                dst = partners.sorted("id")[0]
                try:
                    MergeWizard._merge(partners.ids, dst_partner=dst, extra_checks=False)
                    merged_emails += 1
                except Exception as exc:
                    _logger.warning("Merge failed for %s (%s records): %s", email, len(partners), exc)
                survivor = Partner.search([("email", "=ilike", email)])
            else:
                survivor = partners
            if survivor:
                survivor.write({"company_type": "person", "has_had_contact": False})
                survivors[email] = survivor

        # --- Pre-load company contacts once for the fuzzy match. ------------
        company_index = [
            (self._surveyor_norm(c.name), c)
            for c in Partner.search([("is_company", "=", True)])
            if c.name
        ]

        # --- Pass 2: company assignment for survivors with no company. ------
        assigned_by_domain = 0
        assigned_by_name = 0
        unresolved = []
        for email, survivor in survivors.items():
            contact = survivor[:1]
            if not contact or contact._surveyor_company_of():
                continue

            chosen = Partner.browse()

            # (a) Same e-mail domain -> reuse a peer's company.
            domain = self._surveyor_email_domain(contact.email)
            if domain and domain not in self._SURVEYOR_GENERIC_DOMAINS:
                peers = Partner.search([
                    ("email", "ilike", "@" + domain),
                    ("id", "!=", contact.id),
                ])
                for peer in peers:
                    if self._surveyor_email_domain(peer.email) != domain:
                        continue
                    peer_company = peer._surveyor_company_of()
                    if peer_company:
                        chosen = peer_company
                        break
                if chosen:
                    assigned_by_domain += 1

            # (b) Fuzzy-match the target company name against companies.
            if not chosen:
                wanted = self._surveyor_norm(target_company.get(email, ""))
                if wanted and not wanted.startswith("(a verifier"):
                    best_ratio, best_rec = 0.0, Partner.browse()
                    for cand_name, cand_rec in company_index:
                        ratio = difflib.SequenceMatcher(None, wanted, cand_name).ratio()
                        if ratio > best_ratio:
                            best_ratio, best_rec = ratio, cand_rec
                    if best_rec and best_ratio >= self._SURVEYOR_FUZZY_THRESHOLD:
                        chosen = best_rec
                        assigned_by_name += 1

            if chosen:
                contact.write({"parent_id": chosen.id})
            else:
                unresolved.append((contact.email, contact.name or "", target_company.get(email, "")))

        # --- Reporting. -----------------------------------------------------
        missing = sorted(targets - set(groups))
        _logger.info(
            "One-shot surveyor contact update: %s target email(s); merged duplicates "
            "for %s email(s); %s survivor(s) processed; companies linked -> %s by "
            "shared domain, %s by fuzzy name; %s email(s) had no matching contact; "
            "%s contact(s) left WITHOUT a company.",
            len(targets), merged_emails, len(survivors),
            assigned_by_domain, assigned_by_name, len(missing), len(unresolved),
        )
        if missing:
            _logger.info("Emails with no matching contact: %s", ", ".join(missing))
        if unresolved:
            _logger.info("Contacts still WITHOUT a company (manual review needed):")
            for email, name, wanted in unresolved:
                _logger.info("  - %s | %s | wanted company: %s", email, name, wanted)
        return True
