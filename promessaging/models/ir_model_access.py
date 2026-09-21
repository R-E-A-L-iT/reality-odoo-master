from odoo import _, api, models, tools
from odoo.exceptions import AccessError

MODES = ("read", "write", "create", "unlink")


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    @tools.ormcache("subuser_id", "mode")
    def _promessaging_subuser_models(self, subuser_id, mode):
        """Models a sub-user's own permissions allow, for one mode."""
        assert mode in MODES, "Invalid access mode"
        subuser = self.env["promessaging.subuser"].sudo().browse(subuser_id)
        group_ids = tuple(subuser._effective_groups().ids) or (0,)
        self.env.cr.execute(
            """
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON m.id = a.model_id
             WHERE a.active = TRUE
               AND a.perm_{mode} = TRUE
               AND (a.group_id IS NULL OR a.group_id IN %s)
            """.format(mode=mode),
            [group_ids],
        )
        return {row[0] for row in self.env.cr.fetchall()}

    @api.model
    def check(self, model, mode="read", raise_exception=True):
        """On top of the account's own rights, hold an acting sub-user to its own.

        A sub-user can only ever do less than the account it runs under: this
        runs after Odoo's check, never instead of it.
        """
        result = super().check(model, mode=mode, raise_exception=raise_exception)
        if not result or self.env.su:
            return result

        subuser = self.env["promessaging.subuser"]._active_subuser()
        if not subuser or not subuser._effective_groups():
            return result
        if model in self._promessaging_subuser_models(subuser.id, mode):
            return result

        if raise_exception:
            raise AccessError(_(
                "%(subuser)s is not allowed to %(mode)s %(model)s records.\n\n"
                "This is a limit on the AI sub-user itself, not on the account it "
                "runs under. Change it on the sub-user's permissions.",
                subuser=subuser.sudo().name, mode=mode, model=model,
            ))
        return False
