# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class QuotationDocument(models.Model):
    """Extend the standard PDF-quote-builder document model so it can also hold
    our legacy "preview" headers/footers.

    Two classes of document now live on the same model:

    * ``report``  – the native Odoo behaviour: an uploaded PDF that is added as a
      page to the printed/PDF version of the quote.
    * ``preview`` – our custom behaviour: instead of a PDF, it stores a *link*
      (image or video URL) that is rendered on the online quote preview page.

    Preview documents have no attachment/PDF, so the native PDF-validity
    constraint is skipped for them and they are excluded from the native
    Headers/Footers selector on the sale order.
    """

    _inherit = "quotation.document"

    doc_class = fields.Selection(
        selection=[("report", "Report"), ("preview", "Preview")],
        string="Document Class",
        required=True,
        default="report",
        help="Report: an uploaded PDF added to the printed quote.\n"
             "Preview: a link (image/video URL) shown on the online quote preview.",
    )
    # Only used by "preview" documents (native "report" documents use the PDF).
    url = fields.Char(string="Resource URL")
    # Legacy per-company scoping for preview documents (the native model uses the
    # single company_id inherited from ir.attachment for report documents).
    company_ids = fields.Many2many(
        "res.company",
        "quotation_document_res_company_rel",
        "quotation_document_id",
        "res_company_id",
        string="Companies",
    )

    @api.constrains("datas")
    def _check_pdf_validity(self):
        # Preview documents carry a URL, not a PDF attachment – skip the native
        # PDF checks (which would choke on the empty ``datas``).
        report_docs = self.filtered(lambda d: d.doc_class != "preview")
        if report_docs:
            super(QuotationDocument, report_docs)._check_pdf_validity()

    @api.constrains("doc_class", "url", "document_type")
    def _check_preview_url(self):
        for rec in self:
            if rec.doc_class == "preview" and not rec.url:
                raise ValidationError(
                    _("A Preview header/footer requires a Resource URL.")
                )

    # ------------------------------------------------------------------
    # Legacy helpers ported from the old ``header.footer`` model. They map a
    # short code to a CDN url and return (creating if needed) the matching
    # preview document.
    # ------------------------------------------------------------------
    def _get_footer(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/footer/" + url + ".png"
        footers = self.env["quotation.document"].search(
            [
                ("url", "=", complete_url),
                ("doc_class", "=", "preview"),
                ("document_type", "=", "footer"),
            ]
        )
        if len(footers) == 1:
            return footers[0].id
        elif len(footers) == 0:
            return self.env["quotation.document"].create({
                "name": url,
                "url": complete_url,
                "doc_class": "preview",
                "document_type": "footer",
            })
        raise UserError("Invalid Match Count for URL: " + str(complete_url))

    def _get_header(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/header/" + url
        headers = self.env["quotation.document"].search(
            [
                ("url", "=", complete_url),
                ("doc_class", "=", "preview"),
                ("document_type", "=", "header"),
            ]
        )
        if len(headers) == 1:
            return headers[0].id
        elif len(headers) == 0:
            return self.env["quotation.document"].create({
                "name": url,
                "url": complete_url,
                "doc_class": "preview",
                "document_type": "header",
            })
        raise UserError("Invalid Match Count for URL: " + str(complete_url))
