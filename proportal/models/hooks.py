# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Rule = env['ir.rule'].sudo()
    task_model = env['ir.model']._get('project.task')
    portal_group = env.ref('base.group_portal')

    # Detect collaborator field on project
    proj_model = env['project.project']
    if 'collaborator_ids' in proj_model._fields:
        collab_cond = "('project_id.collaborator_ids','child_of', user.partner_id.commercial_partner_id.id)"
    elif 'collaborator_user_ids' in proj_model._fields:
        collab_cond = "('project_id.collaborator_user_ids','in', user.id)"
    else:
        collab_cond = "('id','=',0)"  # no collab field -> no-op

    # Read access if:
    #   - project OR task is followed by the user/company, OR
    #   - project customer is their company, OR
    #   - user is collaborator of the project
    domain = (
        "['|','|','|',"
        "('project_id.message_partner_ids','child_of', user.partner_id.commercial_partner_id.id),"
        "('message_partner_ids','child_of', user.partner_id.commercial_partner_id.id),"
        "('project_id.partner_id','child_of', user.partner_id.commercial_partner_id.id),"
        f"{collab_cond}"
        "]"
    )

    vals = {
        'name': 'Portal: collaborators can read tasks',
        'model_id': task_model.id,
        'groups': [(6, 0, [portal_group.id])],
        'perm_read': True, 'perm_write': False, 'perm_unlink': False, 'perm_create': False,
        'domain_force': domain,
        'active': True,
    }

    existing = Rule.search([
        ('model_id', '=', task_model.id),
        ('groups', 'in', portal_group.id),
        ('name', '=', vals['name']),
    ], limit=1)
    if existing:
        existing.write(vals)
    else:
        Rule.create(vals)
