from odoo import http
from odoo.http import request
from odoo.addons.project.controllers.portal import CustomerPortal as ProjectPortal

class CustomerPortal(ProjectPortal):

    def _project_portal_domain(self):
        partner = request.env.user.partner_id
        commercial = partner.commercial_partner_id
        partner_ids = [commercial.id] + commercial.child_ids.ids

        # Count as visible if the user (or their company) is a follower or a collaborator
        return ['|',
                    ('message_partner_ids', 'child_of', commercial.id),
                    ('collaborator_ids', 'in', partner_ids)
               ]

    def _prepare_portal_layout_values(self):
        vals = super()._prepare_portal_layout_values()
        Project = request.env['project.project'].sudo()
        vals['project_count'] = Project.search_count(self._project_portal_domain())
        return vals

    @http.route(['/my/projects'], type='http', auth='user', website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, **kw):
        request.update_context(project_portal_domain=self._project_portal_domain())
        return super().portal_my_projects(page=page, date_begin=date_begin, date_end=date_end, **kw)
