# ba_upgrade_sync (Odoo 19: receive + transform + replay)

Upgrade-testing sync: users work in **Odoo 17**, and this module replays their
business actions in **Odoo 19** (OriginCopy / staging only).

```
Odoo 17 (Accounting branch, ba_upgrade_sync 17.0)      Odoo 19 (OriginCopy, this module)
  user action -> upgrade.sync.event (same txn)  <-- pull (HTTPS JSON-RPC, read-only API key)
                                                      -> mapping -> transform -> ORM business method
                                                      -> result + Odoo 17/19 comparison
```

## Setup
1. **Odoo 17**
   - Install `ba_upgrade_sync` (17.0) from the Accounting branch.
   - Create a technical user in the group *Upgrade Sync Reader* and give it an API key.
   - Enable capture under *Settings > Technical > Upgrade Sync > Configuration*.
2. **Odoo 19**
   - Install this module.
   - In *Upgrade Sync > Configuration*, set the Odoo 17 URL, database and login, and the
     *Snapshot cutoff* (the date the Odoo 19 database was copied).
   - Provide the API key through the `UPGRADE_SYNC_API_KEY` environment variable or **Set API key**.
3. Click **Test Connection**, then **Fetch Now** and **Process Now**. Dry run is on by default,
   so nothing is kept; check the events.
4. Turn dry run off. When the results look right, turn on **Auto sync** and activate the
   scheduled action *Upgrade Sync: fetch and replay Odoo 17 events*. Staging databases are
   neutralized, which disables crons.

## Event lifecycle
`pending -> processing -> success | dry_run_ok | waiting (retry with backoff) | failed | skipped`

- **Order**: events of the same document (`root_key`, such as a sales order and its invoices)
  are replayed strictly in Odoo 17 order. Other documents are not blocked.
- **Missing dependency**: the event waits while the event that creates the dependency is
  still queued. That waiting does not use up attempts.
- **Missing master data** (tax, journal, account, pricelist, ...): the event fails and nothing
  is created. Create the record or add a *Record Mapping*, then click **Retry**.
- **Network / Odoo 17 down**: fetching stops and the cursor stays where it is. Replay errors
  are retried at most *Max attempts* times.
- **Duplicates**: the event UUID is unique, and the handlers are idempotent through mappings.

## Extending (custom modules)
- New event: inherit `upgrade.sync.handler` and add `_handle_<type_with_underscores>`.
  On Odoo 17, call `env["upgrade.sync.event"]._enqueue("<type>", records)`.
- Version differences: inherit `upgrade.sync.transformer`.
- Record matching: inherit `upgrade.sync.resolver` (`_match_by_keys`, `_target_model`).

## Tests
`odoo-bin -d <throwaway_db> -i ba_upgrade_sync --test-tags /ba_upgrade_sync --stop-after-init`
