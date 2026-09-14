{
    "name": "ProMessaging",
    "summary": "Control which internal users can send messages to followers from the chatter.",
    "description": """Adds a "Can Send Messages" checkbox on internal users (checked by default).
Unchecked users can still log notes and mention internal users, but cannot send
messages or emails from any document.""",
    "author": "Ezekiel J. deBlois",
    "license": "LGPL-3",
    "version": "17.0",
    "depends": ["mail", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "promessaging/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
