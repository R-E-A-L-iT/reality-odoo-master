{
    "name": "ProCRMCustom",
    "summary": "Modifying CRM to support custom need.",
    "description": """Module that support 
        -Opportunity Status
        -Opportunity SN
    """,
    "author": "Olivier Cote",
    "license": "LGPL-3",
    "version": "0.003",
    "depends": ["base", "crm"],
    "data": [
        "views/crm_opportinuity_custom.xml"
    ],
    "installable": True,
    "application": True,
}
