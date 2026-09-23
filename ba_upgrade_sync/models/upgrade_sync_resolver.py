# -*- coding: utf-8 -*-
"""Resolve Odoo 17 references to Odoo 19 records.

A reference is ``{"model", "id", "name", "create_date", "keys": {...}}`` built
by the Odoo 17 serializer. Resolution order:

1. the mapping table (``upgrade.sync.mapping``);
2. the same id, accepted only when the fingerprint matches (creation date or
   name): the Odoo 19 database is an upgraded copy of Odoo 17;
3. business keys (email, default code, tax name + amount, journal code, ...);
4. otherwise :class:`SyncMasterDataMissing` for master data (never created) or
   :class:`SyncDependencyMissing` for business documents.

Extend with ``_inherit = "upgrade.sync.resolver"``: override
``_target_model`` for renamed models and ``_match_by_keys`` for custom models.
"""
from odoo import api, fields, models

from .exceptions import SyncDependencyMissing, SyncMasterDataMissing

# Never created by the sync: must exist in Odoo 19 (or be mapped manually).
MASTER_DATA_MODELS = {
    "res.company", "res.users", "res.currency", "res.country", "res.country.state",
    "account.tax", "account.journal", "account.account", "account.fiscal.position",
    "account.payment.term", "product.pricelist", "uom.uom", "crm.team", "crm.stage",
    "crm.lost.reason", "stock.warehouse", "stock.location", "product.category",
    "sale.order.template", "res.partner.category", "crm.tag", "res.lang",
}

# Odoo 17 model -> Odoo 19 model when renamed (none in the MVP scope).
MODEL_RENAMES = {}


class UpgradeSyncResolver(models.AbstractModel):
    _name = "upgrade.sync.resolver"
    _description = "Upgrade Sync Reference Resolver"

    @api.model
    def _target_model(self, source_model):
        return MODEL_RENAMES.get(source_model, source_model)

    @api.model
    def _is_master_data(self, target_model):
        return target_model in MASTER_DATA_MODELS

    # ------------------------------------------------------------------
    @api.model
    def _resolve(self, ref, required=True):
        """Return the Odoo 19 record for ``ref`` (empty recordset/None if not
        found and not required)."""
        if not ref:
            return None
        Mapping = self.env["upgrade.sync.mapping"]
        target_model = self._target_model(ref["model"])
        if target_model not in self.env:
            raise SyncMasterDataMissing(ref)
        Model = self.env[target_model].sudo().with_context(active_test=False)

        record = Mapping._lookup(ref["model"], ref["id"])
        if record:
            return record

        record = self._match_by_seed_id(Model, ref)
        if record:
            Mapping._set(ref["model"], ref["id"], record, "seed_id", ref.get("name"))
            return record

        record = self._match_by_keys(Model, ref)
        if record:
            Mapping._set(ref["model"], ref["id"], record, "business_key", ref.get("name"))
            return record

        record = self._create_from_ref(Model, ref)
        if record:
            Mapping._set(ref["model"], ref["id"], record, "created_from_ref", ref.get("name"))
            return record

        if not required:
            return Model.browse()
        if self._is_master_data(target_model):
            raise SyncMasterDataMissing(ref)
        raise SyncDependencyMissing(ref)

    @api.model
    def _resolve_many(self, refs, required=True):
        records = None
        for ref in refs or []:
            record = self._resolve(ref, required=required)
            if record:
                records = record if records is None else records | record
        return records

    @api.model
    def _ids(self, refs, required=True):
        records = self._resolve_many(refs, required=required)
        return records.ids if records else []

    @api.model
    def _id(self, ref, required=True):
        record = self._resolve(ref, required=required)
        return record.id if record else False

    # ------------------------------------------------------------------
    # Matching strategies
    # ------------------------------------------------------------------
    @api.model
    def _match_by_seed_id(self, Model, ref):
        config = self.env["upgrade.sync.config"]._get_config()
        source_create = ref.get("create_date")
        if config.snapshot_cutoff and source_create:
            if fields.Datetime.to_datetime(source_create.replace("T", " ")[:19]) > config.snapshot_cutoff:
                # created in Odoo 17 after the copy: same id is a different record
                return None
        record = Model.browse(ref["id"]).exists()
        if record and self._fingerprint_matches(record, ref):
            return record
        return None

    @api.model
    def _fingerprint_matches(self, record, ref):
        """Same id is only trusted when it is visibly the same record."""
        source_create = (ref.get("create_date") or "").replace("T", " ")[:19]
        if source_create and record.create_date and \
                fields.Datetime.to_string(record.create_date)[:19] == source_create:
            return True
        if ref.get("name") and _norm(record.display_name) == _norm(ref["name"]):
            return True
        key_name = (ref.get("keys") or {}).get("name")
        return bool(key_name) and isinstance(record._fields.get("name"), fields.Char) \
            and _norm(record.name) == _norm(key_name)

    @api.model
    def _match_by_keys(self, Model, ref):
        keys = ref.get("keys") or {}
        model = Model._name
        domains = []
        if model == "res.partner":
            if keys.get("email"):
                domains.append([("email", "=ilike", keys["email"]), ("is_company", "=", bool(keys.get("is_company")))])
            if keys.get("vat"):
                domains.append([("vat", "=", keys["vat"])])
            if keys.get("ref"):
                domains.append([("ref", "=", keys["ref"])])
        elif model in ("product.product", "product.template"):
            if keys.get("default_code"):
                domains.append([("default_code", "=", keys["default_code"])])
            if keys.get("barcode"):
                domains.append([("barcode", "=", keys["barcode"])])
            if keys.get("name"):
                domains.append([("name", "=", keys["name"])])
        elif model == "account.tax":
            domains.append([
                ("name", "=", keys.get("name")),
                ("type_tax_use", "=", keys.get("type_tax_use")),
                ("amount", "=", keys.get("amount")),
                ("company_id.name", "=", keys.get("company")),
            ])
        elif model == "account.journal":
            domains.append([("code", "=", keys.get("code")), ("company_id.name", "=", keys.get("company"))])
        elif model == "account.account":
            company = self.env["res.company"].sudo().search([("name", "=", keys.get("company"))], limit=1)
            if company:
                record = Model.with_company(company).search(
                    [("code", "=", keys.get("code")), ("company_ids", "in", company.ids)], limit=2)
                return record if len(record) == 1 else None
        elif model == "res.users":
            domains.append([("login", "=", keys.get("login"))])
        elif model == "res.country":
            domains.append([("code", "=", keys.get("code"))])
        elif model == "res.country.state":
            domains.append([("code", "=", keys.get("code")), ("country_id.code", "=", keys.get("country_code"))])
        elif model == "res.currency":
            domains.append([("name", "=", keys.get("name"))])
        elif model == "uom.uom":
            domains.append([("name", "=", keys.get("name"))])
        elif model == "product.category":
            domains.append([("complete_name", "=", keys.get("complete_name"))])
        elif "name" in Model._fields and ref.get("name") and model not in (
                "sale.order", "sale.order.line", "account.move", "account.move.line", "crm.lead"):
            # documents are never matched by name: their numbering may differ
            domains.append([("name", "=", keys.get("name") or ref.get("name"))])
        for domain in domains:
            if any(leaf[2] is None or leaf[2] == "" for leaf in domain):
                continue
            records = Model.search(domain, limit=2)
            if len(records) == 1:
                return records
        return None

    @api.model
    def _create_from_ref(self, Model, ref):
        """Create a minimal contact for an unknown partner reference, when
        allowed and when no queued event would create it with full data."""
        if Model._name != "res.partner":
            return None
        config = self.env["upgrade.sync.config"]._get_config()
        if not config.create_missing_partners:
            return None
        if self.env["upgrade.sync.event"]._pending_event_for(ref):
            return None
        keys = ref.get("keys") or {}
        vals = {
            "name": keys.get("name") or ref.get("name"),
            "email": keys.get("email") or False,
            "vat": keys.get("vat") or False,
            "ref": keys.get("ref") or False,
            "is_company": bool(keys.get("is_company")),
        }
        if keys.get("parent_id"):
            parent = self.env["upgrade.sync.mapping"]._lookup("res.partner", keys["parent_id"])
            vals["parent_id"] = parent.id if parent else False
        return Model.create(vals)


def _norm(value):
    return " ".join((value or "").split()).casefold()
