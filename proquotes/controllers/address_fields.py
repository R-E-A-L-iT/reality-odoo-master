# -*- coding: utf-8 -*-
"""Rules for the portal quote address create/update payloads.

None means the client did not send that key. An edit must leave the stored
value alone in that case. A string (including "") was submitted: required
fields reject a blank, and an explicit blank street2 clears the suite line.
"""

_TEXT_FIELDS = ("name", "street", "street2", "city", "zip")


def _submitted(data, key):
    return key in data and data[key] is not None


def _clean_text(value):
    return str(value).strip()


def _parse_m2o(value):
    text = str(value).strip()
    if text.isdigit():
        number = int(text)
        if number > 0:
            return number
    return False


def plan_address_write(
    submitted,
    existing=None,
    *,
    is_create,
    country_exists,
    country_has_states,
    state_matches_country,
    country_required=True,
):
    """Return {"missing": [...], "vals": {...}}.

    vals is empty when required fields are missing, so the caller does not
    write a partial address. Only keys the client actually sent appear in vals.
    """
    existing = existing or {}
    missing = []

    def effective_text(key):
        if _submitted(submitted, key):
            return _clean_text(submitted[key])
        if is_create:
            return ""
        return existing.get(key) or ""

    def effective_id(key, existing_key):
        if _submitted(submitted, key):
            return _parse_m2o(submitted[key])
        if is_create:
            return False
        try:
            value = int(existing.get(existing_key) or 0)
        except (TypeError, ValueError):
            return False
        return value if value > 0 else False

    street = effective_text("street")
    city = effective_text("city")
    zip_code = effective_text("zip")
    country_id = effective_id("country", "country_id")
    state_id = effective_id("state", "state_id")

    if not street:
        missing.append("street")
    if not city:
        missing.append("city")

    if country_required and not country_id:
        missing.append("country")
    elif country_id and not country_exists(country_id):
        missing.append("country")

    country_ok = "country" not in missing and bool(country_id)
    if country_ok and country_has_states(country_id):
        if not state_id or not state_matches_country(state_id, country_id):
            missing.append("state")
    elif country_ok and state_id and not state_matches_country(state_id, country_id):
        missing.append("state")

    if not zip_code:
        missing.append("zip")

    if missing:
        return {"missing": missing, "vals": {}}

    vals = {}
    for key in _TEXT_FIELDS:
        if _submitted(submitted, key):
            vals[key] = _clean_text(submitted[key])
    if _submitted(submitted, "country"):
        vals["country_id"] = country_id
    if _submitted(submitted, "state"):
        # Submitted blank on a country with no states clears a stale province.
        # A country that has states never gets here with a blank state.
        vals["state_id"] = state_id or False
    return {"missing": [], "vals": vals}
