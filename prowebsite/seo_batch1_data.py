# -*- coding: utf-8 -*-
"""Public SEO copy for the first batch.

Titles, descriptions and robots rules are the website text. No analytics
figures belong in this module.
"""

# Main rental-hub title (not the brand-suffix alternative).
PAGE_META = {
    '/rental/scanners': {
        'en_US': (
            'Leica Scanner Rentals: RTC360, BLK360, BLK2GO & BLK ARC',
            'Rent Leica LiDAR laser scanners from REALiT: RTC360, BLK360, BLK2GO and BLK ARC. '
            'Short or long-term rentals, fully calibrated and ready to go. Get a quote.',
        ),
        'fr_CA': (
            'Location de scanners Leica : RTC360, BLK360, BLK2GO, BLK ARC',
            'Louez des scanners LiDAR Leica chez REALiT : RTC360, BLK360, BLK2GO et BLK ARC. '
            'Location courte ou longue durée, équipement calibré. Demandez un devis.',
        ),
        'es': (
            'Alquiler de escáneres Leica: RTC360, BLK360, BLK2GO, BLK ARC',
            'Alquile escáneres LiDAR Leica en REALiT: RTC360, BLK360, BLK2GO y BLK ARC. '
            'Alquiler a corto o largo plazo, equipos calibrados. Solicite una cotización.',
        ),
    },
    '/rental/scanners/blkarc': {
        'en_US': (
            'Leica BLK ARC Rentals | Robotic LiDAR Scanner | REALiT',
            'Rent the Leica BLK ARC autonomous LiDAR scanner for robotic and mobile scanning. '
            'Short or long-term rentals with accessories and software. Get a quote.',
        ),
        'fr_CA': (
            'Location Leica BLK ARC | Scanner LiDAR robotisé | REALiT',
            'Louez le scanner LiDAR autonome Leica BLK ARC pour la numérisation robotisée et mobile. '
            'Location courte ou longue durée, avec accessoires. Demandez un devis.',
        ),
        'es': (
            'Alquiler Leica BLK ARC | Escáner LiDAR robótico | REALiT',
            'Alquile el escáner LiDAR autónomo Leica BLK ARC para escaneo robótico y móvil. '
            'Alquiler a corto o largo plazo, con accesorios. Solicite una cotización.',
        ),
    },
}

# Custom block only. website.robots already prints "User-agent: *" and "Sitemap:".
ROBOTS_TXT = """\
Disallow: /website/info
Disallow: /shop/set_pricelist
Disallow: /shop/cart
Disallow: /shop/checkout
Disallow: /web/login
Disallow: /web/signup
Disallow: /web/reset_password
Disallow: /my/
Allow: /social_instagram/
"""

# Empty website.page records. Controller junk is removed in the sitemap filter.
UNINDEXED_URLS = ('/dev', '/cont', '/telechargement')

YEAR_OLD = 'equipment since 2022'
YEAR_NEW = 'equipment since 2020'
ARK_OLD = 'BLK ARK'
ARK_NEW = 'BLK ARC'

WEBSITE_ID = 1
