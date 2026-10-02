# Pro Upgrade Testkit

**Install on OriginCopy / staging only. Never install this module on production.**

`pro_upgrade_testkit` is a small Odoo 19 helper for R-E-A-L.iT upgrade testing. It does **not** clone real customer documents. It rebuilds a deterministic, Enginelly-tagged sales and rental suite through the ORM so Ezekiel can compare the same processes after an Odoo 19 upgrade.

## Install (odoo.sh OriginCopy)

1. Deploy this branch onto the **OriginCopy** database (staging), not production.
2. Update the Apps list and install **Pro Upgrade Testkit**.
3. Confirm `proquotes`, Sales, Rental, Inventory, and Invoicing are already present (this module depends on them).

The module is not auto-installed and is not required on production.

## How to run Rebuild

Internal sales users can open:

**Sales → Enginelly Test → Rebuild Enginelly test suite**

Click **Rebuild Enginelly test suite**. Each run writes a `pro.upgrade.test.run` record with PASS / FAIL / SKIP lines, an HTML report, and a chatter summary. Open **Sales → Enginelly Test → Test Runs** to compare runs.

## What gets created

The suite looks up partner **R-E-A-L.iT Test Company** and quotation templates by name (never by hardcoded IDs). Missing partner/templates/products are reported as FAIL or SKIP and do not crash the rest of the run.

| Step | Expected document | Typical state |
|---|---|---|
| Cancel prior | Existing `[ENGINELLY-TESTKIT]` SOs (and related draft/posted unpaid invoices / open pickings) | Cancelled |
| Sales Blank | Quote from template `Sales Blank` | Draft |
| SALES - RTC360 | Quote from `SALES - RTC360` | Draft, template optional / single-choice left as-is when proquotes fields exist |
| Minimal sale | Blank template + 1–2 simple products (service / non-stock preferred) | Confirmed |
| Invoice | Invoice from the minimal sale | Posted when invoicing is possible |
| Delivery | Picking from the minimal sale | Validated when a picking exists (SKIP for service-only) |
| Rental Blank | Quote from `Rental Blank` with a 7-day rental window | Draft |
| Rental process | `RENTAL - RTC360`, or rental blank + a `rent_ok` product | Confirmed when safe |
| Rental pickup | `action_open_pickup` (proquotes) / picking validate | FAIL is recorded; the suite continues |
| Renewal Auto | Quote from `Renewal Auto` if the template exists | Draft, otherwise SKIP |

Created orders use customer reference **`[ENGINELLY-TESTKIT] Enginelly test`** plus the same token in the order note.

## Idempotency strategy

Before creating anything, the kit searches `sale.order` for `client_order_ref` or `note` containing **`[ENGINELLY-TESTKIT]`**.

For each match that is not already cancelled it will, per document and inside a savepoint:

1. Reset-to-draft and cancel related invoices that are not paid.
2. Cancel related pickings that are not done.
3. Cancel the sale order (`action_cancel`).

Paid invoices and done pickings are left in place and reported. Documents are **not unlinked**, so cancelled history remains for audit. Re-runs therefore replace the *open* suite instead of stacking infinite draft/open SO/invoices.

## Mapping results to upgrade testing

Use the run report as the upgrade checklist:

- **PASS** — that process still completes on OriginCopy Odoo 19 (quote template apply, confirm, invoice post, delivery, rental confirm, pickup).
- **SKIP** — a named template, partner, or product was missing, or the step does not apply (e.g. no picking on a service order). Fix the missing master data and rebuild if that path matters.
- **FAIL** — the process raised. The error on the run line is the upgrade regression to reproduce (taxes, stock, rental pickup, kit explosion, etc.).

Compare `amount_total` and document counts across runs. Draft quotes (Blank / RTC360 / Renewal Auto) are for visual/PDF/portal checks; the confirmed sale and rental documents are for process checks.

## Out of scope (v1)

- Portal browser automation / JS tours
- Cloning production customer documents
- Changing proquotes behaviour
- Production secrets or machine-specific hacks
