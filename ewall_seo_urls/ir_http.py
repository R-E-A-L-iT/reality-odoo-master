# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.http import request
import odoo.addons.http_routing.models.ir_http as ir_http_file
from odoo.addons.base.models.ir_http import RequestUID
from odoo.addons.http_routing.models.ir_http import _UNSLUG_RE, slug as slug_super
import re
import unicodedata
from odoo.addons.http_routing.models.ir_http import _UNSLUG_RE, slugify_one as slugify_one_super
# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None
from odoo.addons.website.models.ir_http import ModelConverter
import werkzeug.exceptions
from werkzeug.exceptions import HTTPException, NotFound
from odoo.tools import config, ustr, pycompat

# _UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|\/|#|\?)') # ORIGINAL 
_MILTI_LANG_SLUG_RE = r"(?:(\w{1,2}|\w[A-Za-z0-9-_\u0600-\u06FF]+?))(?=$|\/|#|\?)"

def slugify_one(s, max_length=0):
    """
        Transform a string to a slug that can be used in a URL path.
        Adjusts handling of Arabic text to preserve it in slugs.
        
        :param s: str
        :param max_length: int
        :rtype: str
    """
    s = ustr(s)
    if slugify_lib:
        # There are 2 different libraries only python-slugify is supported
        try:
            return slugify_lib.slugify(s, max_length=max_length)
        except TypeError:
            pass
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', s):
        # Only normalize without stripping Arabic characters
        uni = unicodedata.normalize('NFKC', s)
        slug_str = re.sub(r'[\W_]', ' ', uni).strip().lower()
        slug_str = re.sub(r'[-\s]+', '-', slug_str)
        return slug_str[:max_length] if max_length > 0 else slug_str
    else:
        return slugify_one_super(s, max_length)

# Default Slug Functionality Override
def slug(value):
    field = getattr(value, "_seo_url_field", None)
    if field and isinstance(value, models.BaseModel) and hasattr(value, field):
        name = value[field]
        if name:
            return name
    return slug_super(value)


ir_http_file.slug = slug
ir_http_file.slugify_one = slugify_one

# Model Converter Custom Class Method
class ModelConverterCustom(ModelConverter):
    def __init__(self, url_map, model=False, domain="[]"):
        super(ModelConverter, self).__init__(url_map, model)
        self.regex =  _MILTI_LANG_SLUG_RE


    def to_python(self, value):
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.cr, _uid, request.context)
        record_id = None
        field = getattr(request.registry[self.model], "_seo_url_field", None)
        if field and field in request.registry[self.model]._fields:
            cur_lang = (request.context or {}).get("lang", "en_US")
            langs = [cur_lang] + [
                lang
                for lang, _ in env["res.lang"].sudo().get_installed()
                if lang != cur_lang
            ]
            for lang in langs:
                res = (
                    env[self.model]
                    .with_context(lang=lang)
                    .sudo()
                    .search([(field, "=", value)])
                )
                if res:
                    record_id = res[0].id
                    break

        if record_id:
            return env[self.model].with_context(_converter_value=value).browse(record_id)

        # fallback to original implementation
        original_value = _UNSLUG_RE.match(value)
        if not original_value:
            raise werkzeug.exceptions.NotFound()
        self.regex = _UNSLUG_RE.pattern
        return super().to_python(value)

# Custom Class Method Converter Added
class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_converters(cls):
        res = super(IrHttp, cls)._get_converters()
        res["model"] = ModelConverterCustom
        return res
