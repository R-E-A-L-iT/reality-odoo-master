# -*- coding: utf-8 -*-
import re
from datetime import datetime
import dateutil.parser

# 1. Add to report function

# 2. Throw error function

# 3. Normalization functions

def normalize_char(value):
    if value is None:
        return ''
    return str(value).strip()

def normalize_float(value):
    if value is None or str(value).strip() == '':
        return 0.0
    try:
        return float(re.sub(r'[^\d\.-]', '', str(value)))
    except ValueError:
        return 0.0

def normalize_integer(value):
    if value is None or str(value).strip() == '':
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0

def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    str_val = str(value).strip().lower()
    truthy = {'true', '1', 'yes', 'y', '✓', 'on'}
    falsy = {'false', '0', 'no', 'n', '✗', 'off'}

    if str_val in truthy:
        return True
    if str_val in falsy:
        return False
    return False

def normalize_date(value):
    if not value or not str(value).strip():
        return None
    try:
        # assuming canadian dating convention
        return dateutil.parser.parse(str(value), dayfirst=True, fuzzy=True)
    except (ValueError, TypeError):
        return None
