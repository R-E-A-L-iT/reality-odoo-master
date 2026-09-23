# -*- coding: utf-8 -*-
"""Error kinds used to decide how a failed event is retried."""


class SyncError(Exception):
    """Base class. ``kind`` is stored on the event."""
    kind = "business"


class SyncDependencyMissing(SyncError):
    """A referenced Odoo 17 record has no Odoo 19 counterpart yet.

    Retried (the event creating it may still be queued)."""
    kind = "dependency"

    def __init__(self, ref, message=None):
        self.ref = ref or {}
        super().__init__(message or "Missing %s %s (%s) in Odoo 19" % (
            self.ref.get("model"), self.ref.get("id"), self.ref.get("name")))


class SyncMasterDataMissing(SyncError):
    """Master data (tax, journal, account, pricelist, ...) not found.

    Never created automatically: an administrator must create or map it,
    then retry the event."""
    kind = "master_data"

    def __init__(self, ref):
        self.ref = ref or {}
        super().__init__("Master data %s '%s' (Odoo 17 id %s) not found in Odoo 19. "
                         "Create it or add a record mapping, then retry." % (
                             self.ref.get("model"), self.ref.get("name"), self.ref.get("id")))


class SyncTransientError(SyncError):
    """Network / availability problem: retried with backoff."""
    kind = "transient"


class SyncRemoteError(SyncError):
    """Odoo 17 answered with an error (authentication, access rights, ...)."""
    kind = "transient"
