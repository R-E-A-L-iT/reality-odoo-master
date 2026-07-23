# Odoo 19 migration: temporarily disabled so the store checkout uses the default
# Odoo 19 delivery flow. These add per-product carrier routes (/shop/update_carrier_for_line,
# /shop/rate_carrier_for_line) and override the delivery/checkout controllers.
# Re-enable once the per-product delivery UI is rebuilt for v19.
# from . import main
# from . import delivery
