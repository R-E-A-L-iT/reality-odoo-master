# -*- coding: utf-8 -*-
"""Re-apply the first SEO batch whenever prowebsite moves to 0.2.

Staging rebuilds start from a fresh production database, where this module
is still the previous version, so Odoo runs this script on every such upgrade.
"""


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    from odoo.addons.prowebsite.seo_migrate import migrate_seo_batch1

    env = api.Environment(cr, SUPERUSER_ID, {})
    migrate_seo_batch1(env)
