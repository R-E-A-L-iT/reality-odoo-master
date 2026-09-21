{
    "name": "Summaries",
    "summary": "Daily summaries: a per-user to-do list, notes and performance graphs for every business day.",
    "description": """A rich daily note for each user and each business day.
Holds a checklist of objectives (each able to link to a document in the system),
free-form notes with images and markup, a progress bar over the day's objectives,
and interactive performance graphs based on the user's role.
Summaries Managers can view and edit everyone's summaries.""",
    "author": "Ezekiel J. deBlois",
    "license": "LGPL-3",
    "version": "17.0",
    "depends": ["base", "web"],
    "data": [
        "security/summaries_groups.xml",
        "security/ir.model.access.csv",
        "security/summaries_rules.xml",
        "data/ir_cron.xml",
        "views/summaries_views.xml",
        "views/summaries_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "summaries/static/src/**/*",
        ],
    },
    "installable": True,
    "application": True,
}
