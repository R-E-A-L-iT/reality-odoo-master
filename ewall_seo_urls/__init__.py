# -*- coding: utf-8 -*-

from . import seo_url
from . import models
from . import controllers

def post_load():
    from . import ir_http

