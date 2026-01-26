# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EnvioPackage(models.Model):
    _name = "envio.package"
    _description = "Envio Package"
    _order = "last_event_at desc, id desc"

    # Core identifiers
    name = fields.Char(string="Name")
    envio_external_id = fields.Char(string="Envio ID", index=True, required=True)
    tracking_number = fields.Char(string="Tracking Number", index=True)

    # Status / timestamps
    status = fields.Char(string="Status", index=True)
    last_event_at = fields.Datetime(string="Last Event At", index=True)

    # Optional logistics fields (adjust mapping to match Envio)
    origin = fields.Char(string="Origin")
    destination = fields.Char(string="Destination")

    # Optional device/telemetry (adjust mapping to match Envio)
    device_id = fields.Char(string="Device ID", index=True)
    battery_percent = fields.Float(string="Battery %", default=False)
    temperature_c = fields.Float(string="Temperature (°C)")
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))

    # Debug / traceability
    raw_json = fields.Text(string="Raw JSON", readonly=True)

    # updatedable settings
    inspection_date = fields.Datetime(string="Inspection Date")
    update_frequency_seconds = fields.Integer(string="Update Frequency (seconds)")

    UPDATE_FREQ_OPTIONS = [
        ("30", "30 seconds"),
        ("300", "5 minutes"),
        ("600", "10 minutes"),
        ("1200", "20 minutes"),
        ("1800", "30 minutes"),
        ("3600", "1 hour"),
        ("7200", "2 hours"),
        ("14400", "4 hours"),
        ("21600", "6 hours"),
        ("43200", "12 hours"),
        ("86400", "1 day"),
    ]

    update_frequency_option = fields.Selection(
        selection=UPDATE_FREQ_OPTIONS,
        string="Device Update Frequency",
        compute="_compute_update_frequency_option",
        inverse="_inverse_update_frequency_option",
        store=False,
    )

    # Optional label image to send to Envio
    label_image = fields.Binary(string="Label Image")
    label_image_filename = fields.Char(string="Label Image Filename")

    _sql_constraints = [
        ("envio_external_id_uniq", "unique(envio_external_id)", "Envio ID must be unique."),
    ]

    lot_id = fields.Many2one(
        "stock.lot",
        string="Serial / Lot",
        compute="_compute_lot_id",
        inverse="_inverse_lot_id",
        store=False,
    )

    @api.depends("update_frequency_seconds")
    def _compute_update_frequency_option(self):
        for rec in self:
            rec.update_frequency_option = str(rec.update_frequency_seconds) if rec.update_frequency_seconds else False

    def _inverse_update_frequency_option(self):
        for rec in self:
            rec.update_frequency_seconds = int(rec.update_frequency_option) if rec.update_frequency_option else 0

    def _compute_lot_id(self):
        # Find the lot that points to this envio.package (many2one stored on stock.lot)
        Lots = self.env["stock.lot"].sudo()
        for rec in self:
            lot = Lots.search([("envio_package_id", "=", rec.id)], limit=1)
            rec.lot_id = lot

    def _inverse_lot_id(self):
        # When user sets lot_id on envio.package, write the foreign key on stock.lot
        for rec in self:
            # Clear old link(s)
            old_lots = self.env["stock.lot"].search([("envio_package_id", "=", rec.id)])
            if old_lots:
                old_lots.write({"envio_package_id": False})

            # Set new link
            if rec.lot_id:
                rec.lot_id.write({"envio_package_id": rec.id})

    # -------------------------
    # Public entrypoints
    # -------------------------
    def action_sync_envio_packages(self):
        """
        Pull packages from Envio and upsert into Odoo.
        Endpoint + field mapping are intentionally conservative placeholders.
        """
        base_url, token, header_mode = self._get_envio_config()
        if not base_url or not token:
            raise UserError(_("Please configure Envio API Base URL and API Token/Key in Settings."))

        endpoint = f"{base_url.rstrip('/')}/api/v1/devices"

        headers = self._build_auth_headers(token, header_mode)
        timeout = 30

        _logger.info("Envio sync starting. GET %s", endpoint)
        try:
            resp = requests.get(endpoint, headers=headers, timeout=timeout)
        except Exception as e:
            raise UserError(_("Envio request failed: %s") % (e,))

        if resp.status_code >= 400:
            raise UserError(_("Envio API error %s: %s") % (resp.status_code, resp.text[:500]))

        try:
            payload = resp.json()
        except Exception:
            raise UserError(_("Envio response was not valid JSON: %s") % (resp.text[:500],))

        # Handle common API shapes:
        # - payload is a list: [...]
        # - payload is a dict with "data": [...]
        # - payload is a dict with "results": [...]
        records = None
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = payload.get("data") or payload.get("results") or payload.get("items")
        if not isinstance(records, list):
            raise UserError(_(
                "Unexpected Envio response shape. Expected a list or a dict containing data/results/items.\n"
                "Got keys: %s"
            ) % (list(payload.keys()) if isinstance(payload, dict) else type(payload)))

        upserts = 0
        for rec in records:
            if not isinstance(rec, dict):
                continue

            # ⚠️ IMPORTANT: adjust these keys to match Envio fields
            external_id = str(rec.get("id") or rec.get("packageId") or rec.get("package_id") or "")
            if not external_id:
                # Can't upsert without stable ID
                continue

            vals = self._map_envio_package(rec)
            vals["envio_external_id"] = external_id
            vals["raw_json"] = json.dumps(rec, ensure_ascii=False)

            existing = self.search([("envio_external_id", "=", external_id)], limit=1)
            if existing:
                existing.with_context(envio_no_push=True).write(vals)
            else:
                self.with_context(envio_no_push=True).create(vals)
            upserts += 1

        _logger.info("Envio sync done. Upserted: %s", upserts)
        return True

    # -------------------------
    # Helpers
    # -------------------------
    @api.model
    def _get_envio_config(self):
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("envio_connector.base_url", default="").strip()
        token = ICP.get_param("envio_connector.api_token", default="").strip()
        header_mode = ICP.get_param("envio_connector.header_mode", default="bearer").strip()
        return base_url, token, header_mode

    @api.model
    def _build_auth_headers(self, token, header_mode):
        """
        header_mode:
          - bearer: Authorization: Bearer <token>
          - authorization: Authorization: <token>   (if Envio already gives full value)
          - x_api_key: X-API-Key: <token>
        """
        headers = {"Accept": "application/json"}

        mode = (header_mode or "bearer").lower().strip()
        if mode == "x_api_key":
            headers["X-API-Key"] = token
        elif mode == "authorization":
            headers["Authorization"] = token
        else:
            # default bearer
            if token.lower().startswith("bearer "):
                headers["Authorization"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"

        return headers

    @api.model
    def _parse_dt(self, value):
        """
        Best-effort parse for ISO strings or epoch seconds.
        Adjust once you know Envio's exact format.
        """
        if not value:
            return False
        if isinstance(value, (int, float)):
            try:
                return fields.Datetime.to_string(datetime.utcfromtimestamp(value))
            except Exception:
                return False
        if isinstance(value, str):
            # Odoo can often parse ISO8601 directly via fields.Datetime.from_string if normalized,
            # but we keep it simple and store as-is when possible.
            try:
                # Try Odoo parsing
                return fields.Datetime.to_string(fields.Datetime.from_string(value))
            except Exception:
                # Try common ISO format trimming
                try:
                    v = value.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(v)
                    return fields.Datetime.to_string(dt)
                except Exception:
                    return False
        return False

    @api.model
    def get_map_points(self):
        """Return map markers for devices that have a location."""
        recs = self.search([
            ("latitude", "!=", False),
            ("longitude", "!=", False),
        ])

        points = []
        for r in recs:
            points.append({
                "id": r.id,
                "name": r.name or r.envio_external_id,
                "status": r.status,
                "battery_percent": r.battery_percent,
                "last_event_at": fields.Datetime.to_string(r.last_event_at) if r.last_event_at else False,
                "lat": r.latitude,
                "lng": r.longitude,
            })
        return points


    @api.model
    def _map_envio_package(self, rec):
        """
        Map Envio record -> Odoo fields.
        ⚠️ Replace keys here once you know Envio's exact payload.
        """
        # Guess common keys
        tracking = rec.get("trackingNumber") or rec.get("tracking_number") or rec.get("reference")
        status = rec.get("status") or rec.get("state")
        name = rec.get("name") or tracking or rec.get("label") or rec.get("reference")

        # Location
        lat = rec.get("lat") or rec.get("latitude")
        lng = rec.get("lng") or rec.get("lon") or rec.get("longitude")

        # Telemetry
        temp = rec.get("temperatureC") or rec.get("temperature_c") or rec.get("tempC") or rec.get("temperature")
        batt = rec.get("batteryLevel")
        if batt is None:
            batt = rec.get("batteryPercent") or rec.get("battery_percent") or rec.get("battery")


        # Timestamps
        last_ts = rec.get("lastEventAt") or rec.get("last_event_at") or rec.get("updatedAt") or rec.get("updated_at")

        # Origin/destination
        origin = rec.get("origin") or rec.get("from")
        dest = rec.get("destination") or rec.get("to")

        device_id = rec.get("deviceId") or rec.get("device_id") or rec.get("artacId") or rec.get("artac_id")

        def _to_float_or_false(v):
            try:
                if v in (None, "", False):
                    return False
                return float(v)
            except Exception:
                return False

        return {
            "name": name,
            "tracking_number": tracking,
            "status": status,
            "last_event_at": self._parse_dt(last_ts),
            "origin": origin if isinstance(origin, str) else (origin.get("name") if isinstance(origin, dict) else False),
            "destination": dest if isinstance(dest, str) else (dest.get("name") if isinstance(dest, dict) else False),
            "device_id": str(device_id) if device_id else False,
            "battery_percent": float(batt) if batt not in (None, "", False) else 0.0,
            "temperature_c": float(temp) if temp not in (None, "") else 0.0,
            "latitude": _to_float_or_false(lat),
            "longitude": _to_float_or_false(lng),
        }

    def action_push_envio_update(self):
        """Push editable fields to Envio via PUT /api/v1/devices/{id}."""
        for rec in self:
            base_url, token, header_mode = rec._get_envio_config()
            if not base_url or not token:
                raise UserError(_("Please configure Envio API Base URL and API Token/Key in Settings."))

            if not rec.envio_external_id:
                raise UserError(_("This record has no Envio ID to update."))

            endpoint = f"{base_url.rstrip('/')}/api/v1/devices/{rec.envio_external_id}"

            headers = rec._build_auth_headers(token, header_mode)
            # Envio is strict sometimes—set both
            headers["Accept"] = "*/*"
            headers["Content-Type"] = "application/json"

            payload = rec._build_envio_update_payload()

            _logger.info("Envio update. PUT %s payload=%s", endpoint, payload)

            try:
                resp = requests.put(endpoint, headers=headers, json=payload, timeout=30)
            except Exception as e:
                raise UserError(_("Envio request failed: %s") % (e,))

            if resp.status_code >= 400:
                raise UserError(_("Envio API error %s: %s") % (resp.status_code, resp.text[:800]))

            # If Envio returns device details JSON, store it and optionally update some fields
            try:
                data = resp.json()
            except Exception:
                data = None

            if isinstance(data, dict):
                rec.with_context(envio_no_push=True).write({
                    "raw_json": json.dumps(data, ensure_ascii=False),
                })
                rec.with_context(envio_no_push=True)._apply_envio_device_details(data)

        return True

    def _build_envio_update_payload(self):
        """Build the JSON payload expected by Envio PUT /api/v1/devices/{id}."""
        self.ensure_one()

        payload = {}

        # Only send keys that are set (avoid resetting values unintentionally)
        if self.update_frequency_seconds is not None:
            payload["updateFrequencyInSeconds"] = int(self.update_frequency_seconds)

        if self.inspection_date:
            # Envio sample shows ISO string; use Odoo's datetime -> ISO
            # Odoo stores naive UTC by default; send as Zulu-ish ISO.
            dt = fields.Datetime.to_datetime(self.inspection_date)
            payload["inspectionDate"] = dt.isoformat().replace("+00:00", "Z")

        # Optional base64Image object (only if image present)
        if self.label_image:
            # Odoo binary fields are base64-encoded strings already
            filename = self.label_image_filename or "label.jpg"
            payload["base64Image"] = {
                "data": self.label_image,      # already base64 string
                "filename": filename,
            }

        if not payload:
            raise UserError(_("Nothing to update. Set at least one update field first."))

        return payload

    def _apply_envio_device_details(self, data):
        """Update a few fields from Envio device detail response (optional)."""
        self.ensure_one()

        # You can expand this later, but keep it safe/minimal.
        if "name" in data and data["name"]:
            self.name = data["name"]
        if "status" in data:
            self.status = data.get("status") or self.status

        if "updateFrequencyInSeconds" in data and data["updateFrequencyInSeconds"] is not None:
            self.update_frequency_seconds = int(data["updateFrequencyInSeconds"])

        if "inspectionDate" in data and data["inspectionDate"]:
            self.inspection_date = self._parse_dt(data["inspectionDate"])

    def write(self, vals):
        # Fields that should trigger a push when edited
        push_fields = {
            "update_frequency_seconds",
            "inspection_date",
            "label_image",
            "label_image_filename",
            # If you ever make name editable and want it pushed, include "name"
        }

        should_push = bool(push_fields.intersection(vals.keys()))
        res = super().write(vals)

        # Avoid pushing during sync/import/internal updates
        if should_push and not self.env.context.get("envio_no_push"):
            # Push per-record so the error message points to the failing device
            for rec in self:
                if rec.envio_external_id:
                    rec.action_push_envio_update()

        return res

