{
    'name': 'Project Task Stage Customization',
    'version': '17.0.1',
    'category': 'Project',
    'summary': 'Customize project task stages: rename In Progress to Not Started and create new In Progress stage',
    'description': """
        This module customizes the project task stages by:
        - Renaming the existing "In Progress" stage to "Not Started"
        - Creating a new "In Progress" stage with purple color
        - Adding "Changes Requested" stage with orange color
        - Adding "Approved" stage with green color
        - JavaScript integration for proper color display in Kanban view
    """,
    'author': '',
    'depends': ['project', 'web'],
    'data': [
        "views/filter_inherit.xml",
    ],
    'assets': {
        'web.assets_backend': [
             ("remove", "project/static/src/components/project_task_state_selection/project_task_state_selection.js"),
              # 'project_task_stage_customization/static/src/components/project_task_state_selection/project_task_state_selection.js',
             'project_task_stage_customization/static/src/components/project_task_state_selection/project_task_state_selection.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}