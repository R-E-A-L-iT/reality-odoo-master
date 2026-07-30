# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import models
from odoo.http import request
from odoo.addons.website.models.ir_http import ModelConverter as WebsiteModelConverter

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

_MULTI_LANG_SLUG_RE = r"(?:(\w{1,2}|\w[A-Za-z0-9-_؀-ۿ]+?))(?=$|\/|#|\?)"
_ARABIC_RE = re.compile(r'[؀-ۿݐ-ݿࢠ-ࣿ]')


# Model Converter Custom Class: resolves URL segments to records via the
# record's _seo_url_field before falling back to the standard name-id slug.
class ModelConverterCustom(WebsiteModelConverter):
    def __init__(self, url_map, model=False, domain='[]'):
        super().__init__(url_map, model, domain)
        self.regex = _MULTI_LANG_SLUG_RE

    def to_python(self, value):
        field = getattr(request.env[self.model], "_seo_url_field", None)
        if field and field in request.env[self.model]._fields:
            cur_lang = (request.context or {}).get("lang", "en_US")
            langs = [cur_lang] + [
                lang for lang, _ in request.env["res.lang"].sudo().get_installed()
                if lang != cur_lang
            ]
            for lang in langs:
                record = request.env[self.model].with_context(lang=lang).sudo().search(
                    [(field, "=", value)], limit=1
                )
                if record:
                    return record.with_context(_converter_value=value)
        return super().to_python(value)


# Custom Class Method Override: SEO URL Name Added
class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _slug(cls, value):
        field = getattr(value, "_seo_url_field", None)
        if field and isinstance(value, models.BaseModel) and hasattr(value, field):
            name = value[field]
            if name:
                return name
        return super()._slug(value)

    @classmethod
    def _slugify_one(cls, value, max_length=None):
        """
            Transform a string to a slug that can be used in a URL path.
            Adjusts handling of Arabic text to preserve it in slugs.
        """
        s = str(value)
        if slugify_lib:
            # There are 2 different libraries only python-slugify is supported
            try:
                return slugify_lib.slugify(s, max_length=max_length)
            except TypeError:
                pass
        if _ARABIC_RE.search(s):
            # Only normalize without stripping Arabic characters
            uni = unicodedata.normalize('NFKC', s)
            slug_str = re.sub(r'[\W_]', ' ', uni).strip().lower()
            slug_str = re.sub(r'[-\s]+', '-', slug_str)
            return slug_str[:max_length] if max_length else slug_str
        return super()._slugify_one(value, max_length=max_length)

    @classmethod
    def _get_converters(cls):
        return dict(super()._get_converters(), model=ModelConverterCustom)
