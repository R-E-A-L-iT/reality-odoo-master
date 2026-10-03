# -*- coding: utf-8 -*-
"""Portal rental calendar dates.

Portal date inputs are calendar days (``YYYY-MM-DD``), not instants.
sale_renting stores ``rental_start_date`` / ``rental_return_date`` as naive
UTC datetimes and the backend widget shows them in the user's timezone.

New portal saves store local midnight in the company timezone, converted to
UTC, and the portal renders that instant back to the same calendar day. That
is the same direction sale_renting / website_sale_renting use (local → UTC on
write, UTC → local on display) so a Toronto backend user and the portal show
the same day.

Older portal saves stored the typed day as midnight UTC. In a timezone behind
UTC that instant is the previous evening, so converting it for display would
move the customer-visible day. Those values (time exactly 00:00:00) keep the
UTC calendar day on the portal. Nothing is rewritten until the customer saves
again, and saving the same days stores local midnight without changing the
day count used for pricing.
"""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MESSAGES = {
    "order": {
        "fr": "La date de début de location doit être antérieure ou égale à la date de fin de location.",
        "en": "The rental start date must be on or before the rental end date.",
    },
    "invalid": {
        "fr": "Veuillez saisir une date de début et une date de fin de location valides.",
        "en": "Enter a valid rental start date and a valid rental end date.",
    },
    "missing_sign": {
        "fr": "Veuillez choisir une date de début et une date de fin de location avant de signer.",
        "en": "Please choose both rental start and end dates before signing.",
    },
    "save": {
        "fr": "Les dates de location ne peuvent pas être enregistrées. Veuillez réessayer.",
        "en": "The rental dates could not be saved. Please try again.",
    },
    "locked": {
        "fr": "Ces dates de location ne peuvent plus être modifiées.",
        "en": "These rental dates can no longer be changed.",
    },
    "stale_total": {
        "fr": "Le total a été mis à jour pour ces dates. Veuillez le vérifier et signer de nouveau.",
        "en": "The total has been updated for these dates. Please review it and sign again.",
    },
}


def rental_dates_editable(state, locked=False):
    """Portal rental dates may be saved only on an unlocked draft or sent quote.

    Confirmed, done, and cancelled orders are not editable. Odoo's ``locked``
    flag blocks a draft or sent quote the same way.
    """
    if locked:
        return False
    return state in ("draft", "sent")


def signature_default_name(partner_name, user_name=None, user_is_public=None):
    """Name pre-filled on Accept & Sign.

    Standard sale portal uses the order customer (``sale.order.partner_id.name``).
    The website public user is named ``Public user for ...``, and Auto
    signature rejects that string. A logged-in portal user signs as the
    order customer as well: ``user_name`` and ``user_is_public`` do not
    change the result.
    """
    del user_name, user_is_public
    if not partner_name:
        return ""
    return str(partner_name).strip()


def normalize_lang_code(lang):
    """Accept a lang code, an Odoo ``res.lang`` record, or empty."""
    if not lang:
        return "en_US"
    code = getattr(lang, "code", None)
    if code:
        return code
    if isinstance(lang, str):
        return lang
    return "en_US"


def rental_message(key, lang="en_US"):
    entry = MESSAGES.get(key) or MESSAGES["save"]
    code = normalize_lang_code(lang).lower()
    if code.startswith("fr"):
        return entry["fr"]
    return entry["en"]


def is_valid_tz_name(name):
    if not name or not isinstance(name, str):
        return False
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False
    return True


def choose_tz_name(candidates):
    """First usable timezone name, otherwise UTC."""
    for name in candidates:
        if is_valid_tz_name(name):
            return name
    return "UTC"


def parse_portal_date(value):
    """Return a ``date`` when ``value`` is a real ``YYYY-MM-DD`` day."""
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_portal_rental_pair(start_value, end_value):
    """``None`` when both dates are complete and start <= end.

    ``invalid`` covers missing or malformed values. ``order`` means both
    parsed and the start day is after the end day. Nothing should be written
    in either case.
    """
    start = parse_portal_date((start_value or "").strip() if isinstance(start_value, str) else "")
    end = parse_portal_date((end_value or "").strip() if isinstance(end_value, str) else "")
    if not start or not end:
        return "invalid"
    if start > end:
        return "order"
    return None


def local_midnight_to_utc(date_str, tz_name):
    """Calendar day at 00:00 in ``tz_name``, as a naive UTC datetime."""
    day = parse_portal_date(date_str)
    if not day:
        raise ValueError("Invalid portal rental date %r" % date_str)
    tz = ZoneInfo(choose_tz_name([tz_name]))
    local = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def _as_naive_datetime(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        text = dt.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:26], fmt)
            except ValueError:
                continue
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    return None


def is_legacy_midnight_utc(dt):
    """True for portal rows saved as ``YYYY-MM-DD`` at 00:00:00 UTC."""
    naive = _as_naive_datetime(dt)
    if not naive:
        return False
    return naive.hour == 0 and naive.minute == 0 and naive.second == 0 and naive.microsecond == 0


def portal_calendar_date(dt, tz_name):
    """``YYYY-MM-DD`` to show in the portal date input.

    Midnight-UTC values keep their UTC calendar day (legacy portal saves, and
    companies whose timezone is UTC). Every other instant is converted into
    ``tz_name`` so the portal day matches the backend widget.
    """
    naive = _as_naive_datetime(dt)
    if not naive:
        return ""
    if is_legacy_midnight_utc(naive):
        return naive.strftime("%Y-%m-%d")
    tz = ZoneInfo(choose_tz_name([tz_name]))
    local = naive.replace(tzinfo=timezone.utc).astimezone(tz)
    return local.strftime("%Y-%m-%d")


def rental_calendar_days(start_dt, end_dt):
    """Day count used by duration and the custom rental price.

    Matches ``SaleOrder._compute_duration`` and ``_get_pricelist_price``:
    the difference of the stored UTC calendar dates, minimum 1 when both
    ends are set. For a portal save both instants are local midnight, and
    in American timezones that UTC date is the customer calendar day, so
    the count matches the dates shown on the quote.
    """
    start = _as_naive_datetime(start_dt)
    end = _as_naive_datetime(end_dt)
    if not start or not end:
        return 0
    return max(1, (end.date() - start.date()).days)


def paid_rental_days(cal_days):
    """Paid-day multiplier. Must match quote_preview.xml and sale_renting.py."""
    if not cal_days or cal_days <= 0:
        return 0
    full_months = cal_days // 30
    remaining = cal_days % 30
    full_weeks = remaining // 7
    extra_days = remaining % 7
    remainder_paid = min((full_weeks * 4) + min(extra_days, 4), 12)
    return (full_months * 12) + remainder_paid


def posted_sign_block_key(is_rental, start_value, end_value):
    """Message key for dates sent with Accept & Sign, or ``None``.

    Non-rental quotes are ignored. ``None`` for both values means the client
    did not send dates (older pages, or a quote with the inputs disabled),
    so the stored period is checked separately. A rental that does send a
    missing or invalid pair is blocked even when an older period is still
    stored, because clearing an input does not write that empty value.
    """
    if not is_rental:
        return None
    if start_value is None and end_value is None:
        return None
    start = start_value.strip() if isinstance(start_value, str) else ""
    end = end_value.strip() if isinstance(end_value, str) else ""
    if not start or not end:
        return "missing_sign"
    reason = validate_portal_rental_pair(start, end)
    if reason == "order":
        return "order"
    if reason:
        return "invalid"
    return None


def rental_confirm_needs_restore(
    signed_start,
    signed_end,
    signed_total,
    confirmed_start,
    confirmed_end,
    confirmed_total,
    rounding=0.01,
):
    """True when confirmation moved the period or the total that was signed.

    Confirmation may write line dates and reprice. The stored result has to
    stay on the period and total that were already saved.
    """
    if signed_start != confirmed_start or signed_end != confirmed_end:
        return True
    if signed_total is None or confirmed_total is None:
        return signed_total != confirmed_total
    return abs(float(signed_total) - float(confirmed_total)) >= float(rounding)


def accept_amount_mismatch(displayed, stored_total, changed, rounding=0.01):
    """True when Accept & Sign must stop so the customer can review the total.

    A portal accept that stores the rental dates can reprice the order in
    that same request. The amount on screen is whatever the page sent.
    Signing is refused when this request changed the period or the total
    and the page did not send the new total, and when a sent amount does
    not match the total now stored. An unchanged order with no amount sent
    (an older page) may continue.
    """
    missing = displayed is None or (isinstance(displayed, str) and not displayed.strip())
    if missing:
        return bool(changed)
    try:
        shown = float(displayed)
    except (TypeError, ValueError):
        return True
    if stored_total is None:
        return True
    return abs(shown - float(stored_total)) >= float(rounding)


def signed_rental_period_after_confirm(signed, confirmed, rounding=0.01):
    """Period and total to keep after confirmation.

    ``signed`` is what the customer signed. ``confirmed`` is what
    ``action_confirm`` left on the order. When confirm moved either date
    or the total, the signed values are the ones that stay.
    """
    if rental_confirm_needs_restore(
        signed.get("rental_start_date"),
        signed.get("rental_return_date"),
        signed.get("amount_total"),
        confirmed.get("rental_start_date"),
        confirmed.get("rental_return_date"),
        confirmed.get("amount_total"),
        rounding,
    ):
        return {
            "rental_start_date": signed.get("rental_start_date"),
            "rental_return_date": signed.get("rental_return_date"),
            "amount_total": signed.get("amount_total"),
        }
    return {
        "rental_start_date": confirmed.get("rental_start_date"),
        "rental_return_date": confirmed.get("rental_return_date"),
        "amount_total": confirmed.get("amount_total"),
    }


def sign_block_reason(is_rental, start_dt, end_dt):
    """Why Accept & Sign must stop before writing a signature.

    ``None`` when the order is not a rental, or the stored period is usable.
    """
    if not is_rental:
        return None
    if not start_dt or not end_dt:
        return "missing_sign"
    start = _as_naive_datetime(start_dt)
    end = _as_naive_datetime(end_dt)
    if not start or not end or start > end:
        return "order"
    return None
