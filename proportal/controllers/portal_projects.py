from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.project.controllers.portal import CustomerPortal as ProjectPortal

# allow invited collaborators to see projects in the portal
def _project_collab_domain_for_user(user):
    partner = user.partner_id
    commercial = partner.commercial_partner_id
    partner_ids = [commercial.id] + commercial.child_ids.ids

    Project = request.env["project.project"]
    fields = Project.fields_get(keys=["collaborator_ids", "collaborator_user_ids"])

    dom = ['|', '|',
           ('message_partner_ids', 'child_of', commercial.id),
           ('partner_id', 'child_of', commercial.id),
           ('id', '=', 0)]

    if "collaborator_ids" in fields:
        dom[-3:] = [('collaborator_ids', 'in', partner_ids)]
    elif "collaborator_user_ids" in fields:
        dom[-3:] = [('collaborator_user_ids', 'in', user.id)]
    else:
        dom[-3:] = [('id', '=', 0)]

    return dom


class CustomerPortal(ProjectPortal):

    # --- Count for the portal navbar / tiles ---
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "project_count" in counters:
            Project = request.env["project.project"].sudo()
            dom = _project_collab_domain_for_user(request.env.user)
            values["project_count"] = Project.search_count(dom)
        return values

    @http.route(["/my/projects"], type="http", auth="user", website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        # Sorting (match Odoo’s defaults)
        searchbar_sortings = {
            "date": {"label": "Newest", "order": "create_date desc"},
            "name": {"label": "Name", "order": "name asc"},
        }
        if not sortby or sortby not in searchbar_sortings:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # Domain including collaborators
        dom = _project_collab_domain_for_user(request.env.user)

        Project = request.env["project.project"].sudo()

        # Date filter (keep parity with upstream behavior)
        if date_begin and date_end:
            dom = ['&', ('create_date', '>=', date_begin), ('create_date', '<=', date_end)] + dom

        # Pager
        project_count = Project.search_count(dom)
        pager = portal_pager(
            url="/my/projects",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=project_count,
            page=page,
            step=20,
        )

        projects = Project.search(dom, order=order, limit=pager["step"], offset=pager["offset"])

        values = self._prepare_portal_layout_values()
        values.update({
            "projects": projects,
            "page_name": "project",
            "pager": pager,
            "default_url": "/my/projects",
            "searchbar_sortings": searchbar_sortings,
            "sortby": sortby,
            "project_count": project_count,  # keep templates happy
            "date_begin": date_begin,
            "date_end": date_end,
        })
        return request.render("project.portal_my_projects", values)
