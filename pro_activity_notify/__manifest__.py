# -*- coding: utf-8 -*-
{
    "name": "ProActivity Notify Preferences",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Let each user choose whether to receive emails for activities assigned to them",
    "description": """
Adds a per-user preference so internal users can opt out of the email
notification that Odoo sends whenever an activity is assigned to them.

By default the preference is enabled (existing behaviour: users are emailed).
When a user disables it, no assignment email/notification is sent to them; the
activity still appears in their Activities menu and systray as usual.
    """,
    "license": "LGPL-3",
    "author": "Ézékiel deBlois",
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_users_views.xml",
    ],
    "installable": True,
    "application": False,
}
