from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.project.controllers.portal import CustomerPortal as ProjectPortal


def _project_collab_domain_for_user(user):
    partner = user.partner_id
    commercial = partner.commercial_partner_id
    partner_ids = [commercial.id] + commercial.child_ids.ids

    Project = request.env["project.project"]
    f1 = ('message_partner_ids', 'child_of', commercial.id)
    f2 = ('partner_id', 'child_of', commercial.id)
    if 'collaborator_ids' in Project._fields:
        f3 = ('collaborator_ids', 'in', partner_ids)
    elif 'collaborator_user_ids' in Project._fields:
        f3 = ('collaborator_user_ids', 'in', user.id)
    else:
        f3 = ('id', '=', 0)
    return ['|','|', f1, f2, f3]

def _task_access_domain_for_user(user):
    partner = user.partner_id
    commercial = partner.commercial_partner_id
    partner_ids = [commercial.id] + commercial.child_ids.ids
    proj_fields = request.env['project.project']._fields

    cond1 = ('project_id.message_partner_ids', 'child_of', commercial.id)   # follower of project
    cond2 = ('message_partner_ids', 'child_of', commercial.id)              # follower of task
    if 'collaborator_ids' in proj_fields:                                   # collaborators as partners
        cond3 = ('project_id.collaborator_ids', 'in', partner_ids)
    elif 'collaborator_user_ids' in proj_fields:                            # collaborators as users
        cond3 = ('project_id.collaborator_user_ids', 'in', user.id)
    else:
        cond3 = ('id', '=', 0)

    return ['|', '|', cond1, cond2, cond3]

class CustomerPortal(ProjectPortal):

    @http.route(
        ["/my/project/<int:project_id>", "/my/projects/<int:project_id>"],
        type="http", auth="user", website=True)
    def portal_my_project(self, project_id, access_token=None, page=1, sortby=None, **kw):
        Project = request.env["project.project"].sudo()
        # Allow if (a) access_token is present OR (b) collaborator/follower/customer
        allowed = bool(access_token)
        if not allowed:
            dom = ['&', ('id', '=', project_id)] + _project_collab_domain_for_user(request.env.user)
            allowed = bool(Project.search_count(dom))
        if not allowed:
            return request.redirect("/my")

        project = Project.browse(project_id)

        # Tasks listing (basic parity with Odoo’s defaults)
        Task = request.env["project.task"].sudo()
        searchbar_sortings = {
            "date": {"label": "Newest", "order": "create_date desc"},
            "name": {"label": "Name", "order": "name asc"},
        }
        sortby = sortby if sortby in searchbar_sortings else "date"
        order = searchbar_sortings[sortby]["order"]

        items_per_page = getattr(self, "_items_per_page", 20)
        task_domain = [('project_id', '=', project_id)]
        task_count = Task.search_count(task_domain)
        pager = portal_pager(
            url=f"/my/project/{project_id}",
            url_args={"sortby": sortby},
            total=task_count,
            page=page,
            step=items_per_page,
        )
        tasks = Task.search(task_domain, order=order, limit=items_per_page, offset=pager["offset"])

        values = self._prepare_portal_layout_values()
        values.update({
            "project": project,
            "tasks": tasks,
            "pager": pager,
            "page_name": "project",
            "default_url": f"/my/project/{project_id}",
            "searchbar_sortings": searchbar_sortings,
            "sortby": sortby,
        })
        # stock template for project detail:
        return request.render("project.portal_my_project", values)

    @http.route(
        ["/my/task/<int:task_id>",
         "/my/tasks/<int:task_id>",
         "/my/project/<int:project_id>/task/<int:task_id>"],
        type="http", auth="user", website=True)
    def portal_my_task(self, task_id, project_id=None, access_token=None, **kw):
        Task = request.env['project.task'].sudo()

        allowed = bool(access_token)
        if not allowed:
            dom = ['&', ('id', '=', task_id)] + _task_access_domain_for_user(request.env.user)
            allowed = bool(Task.search_count(dom))

        if not allowed:
            return request.redirect("/my")

        task = Task.browse(task_id)
        values = self._prepare_portal_layout_values()
        values.update({
            "task": task,
            "page_name": "task",
            "default_url": f"/my/task/{task_id}",
        })
        # stock template id for a single task in portal:
        return request.render("project.portal_my_task", values)

    # Count for the portal tiles/navbar
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "project_count" in counters:
            Project = request.env["project.project"].sudo()
            dom = _project_collab_domain_for_user(request.env.user)
            values["project_count"] = Project.search_count(dom)
        return values

    # List page: /my/projects
    @http.route(["/my/projects"], type="http", auth="user", website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        searchbar_sortings = {
            "date": {"label": "Newest", "order": "create_date desc"},
            "name": {"label": "Name", "order": "name asc"},
        }
        if not sortby or sortby not in searchbar_sortings:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        dom = _project_collab_domain_for_user(request.env.user)

        if date_begin and date_end:
            dom = ['&', ('create_date', '>=', date_begin), ('create_date', '<=', date_end)] + dom

        Project = request.env["project.project"].sudo()

        # Use the controller's standard page size (same as core controllers)
        items_per_page = getattr(self, "_items_per_page", 20)

        project_count = Project.search_count(dom)
        pager = portal_pager(
            url="/my/projects",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=project_count,
            page=page,
            step=items_per_page,          # pass the step here
        )

        projects = Project.search(dom, order=order, limit=items_per_page, offset=pager["offset"])

        values = self._prepare_portal_layout_values()
        values.update({
            "projects": projects,
            "page_name": "project",
            "pager": pager,
            "default_url": "/my/projects",
            "searchbar_sortings": searchbar_sortings,
            "sortby": sortby,
            "project_count": project_count,
            "date_begin": date_begin,
            "date_end": date_end,
        })
        return request.render("project.portal_my_projects", values)
