# -*- coding: utf-8 -*-

# Unique search token so rebuild can find prior kit documents without matching
# unrelated "test" quotes. Shown in client_order_ref and the order note.
TAG_REF = "[ENGINELLY-TESTKIT]"
TAG_LABEL = "Enginelly test"

PARTNER_NAME = "R-E-A-L.iT Test Company"

TEMPLATE_SALES_BLANK = ["Sales Blank"]
TEMPLATE_SALES_RTC360 = ["SALES - RTC360", "Sales - RTC360"]
TEMPLATE_RENTAL_BLANK = ["Rental Blank"]
TEMPLATE_RENTAL_RTC360 = ["RENTAL - RTC360", "Rental - RTC360"]
TEMPLATE_RENEWAL_AUTO = ["Renewal Auto"]

# Fixed 7-day rental window (duration is what must stay comparable run-to-run).
RENTAL_DURATION_DAYS = 7
