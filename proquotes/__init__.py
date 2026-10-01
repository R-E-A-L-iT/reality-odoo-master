# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import report
from . import wizard


def post_init_hook(env):
    """Link the US footer to company 3 when that company exists.

    Production uses res.company id 3 for the US company. Hardcoding that id in
    XML aborts a fresh install where the company has not been created yet.
    """
    company = env["res.company"].browse(3).exists()
    footer = env.ref("proquotes.footer_us", raise_if_not_found=False)
    if company and footer:
        footer.company_ids = [(4, company.id)]
