from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    #def setUp(self):
    #    super(TestModuleDemo, self).setUp()
            
    def test_is_psw_empty(self):
        synce_model = self.env['sync.sync']

        result = synce_model.is_psw_empty(None)
        self.assertEqual(result, True)

        result = synce_model.is_psw_empty("password")
        self.assertEqual(result, False)


    def test_getMasterDatabaseSheet(self):
    #def getMasterDatabaseSheet(self, template_id, psw, index): 
        synce_model = self.env['sync.sync']

        template_id = synce_model._master_database_template_id
        psw = {
            "type": "service_account",
            "project_id": "odoo-sync-321221",
            "private_key_id": "df3d42f17e926d5bf4219044e5e8324c4b463a3b",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDrJcFuZCRT+MMH\nkVaEqqPOj2wuB6qE0M00ulWIatfYHIdXrU47ccoFePLJyOoB0mliiqybDU7t+T4j\nsRwcxPZx8SFD9RuAbIGZfVSlyho4ZaCkvNEZ8mLFdNCncxWag0HQ0x4Vd+I2OdqA\nFT/UQx+osBWwaI/A9z3zDckSHmFNPfzzIj7haR7CPP9HX/L8YldKziDbKyFUhm9L\nXLWCg8EvFOzDAKj8nAwTYbKw5xR8uX+vvLG9OyZJbtpKmaHku0NfAaQr6aeSLABZ\nrVxb4smCiVO9jrXa2lkLT+k45PWGbP5PCV8w/VTaM82n5ueDqy9VoVQKJoJKu7f8\nxSsJpPOPAgMBAAECggEABQ3ALP+w+i8H/gMlIV/LenaBpDGc/BLCvkXc7bwiHG5s\niDlcy5FD/r8dNLIBOX3MrwX89K4iCqJHMBwv1vxysXs1tFCxwR5T4LkdVxzTWG/y\ntmeqdMzNS6IZk+e4yKPWh8bpyBtV/MVciVErmIPCy+zQ4oQ0xrhpl+4taprFi5Pl\nbizhoybm/kg10zJ24vUzSkUkpt9FPR8RFyrIbOZ06MOBvW9kKF5+CrWtu3kveup5\nFlPti2+RLnzzH2WnLgGMnbtnNXFIjOBq1sVT3ES7DoZCFtcRf0jk1EnK+L6gtiuP\nfb2KoEozQfNmPHzdSRr8qvzuT6jwfvEAH1QQXHDzNQKBgQD5HM4/k0J6z3euo3dr\npHsuzl0WmjuRvqwdCi/bm0VxrAeKAms+INlrOybfW4rLwgi4gGXhm5RrK7PGlC/B\ngfEfK2fSzHEHhu2USt0FA15lEkapqPhzZmuqHXNI5bpYVeQfKodpSM3wpjaLrOk1\ne0DFoYizrnQZEPWlWgK8TAhpkwKBgQDxphtS/yv5yxyJi8X68+wzwpxPxYoIBE2y\nRNVR6xTnyAsFtHkjSoMH3LvKTxrcef6or77MnK2dwL1rb8CPHPRgfh3IIa0nPVKm\nAMnddmYpgQPwT3JNS71FY1fmHIgLGKzroQDCDAWrmtVULSL/AtKZU9b1fkaDDm0X\nwYhrMg8blQKBgClQarBGhu8BO3MeLy8N/1P665tVBu4b9kV2rAs6zCCXDEUKM6kB\nH63WCJNghjtWucWHnd31xH6lp9IWP3lTSJ8HvtdKCrDZ4ssGQ3OSZHRUvJ1kpZfV\n86Mp8TW0y9vcmtHEZuLCLU1s83zkt2SkRVDBgn9yPlTt6B99NxjtbzO7AoGBAL4f\nrcHoSEY5mxNRKIyg28eBp5BP4KEcGbFX3Oqd5g3S43EypFiy6FMIRawP/xdW2JkJ\n5TmBUEwc+CuOeldfNZqxv2bVsDF+WweG+UxIOmsPOfUZ3NmZ7KmqVt8StardWDfv\nrfP+l3uDz7Jx7OXs55uBTlBKcNnuQMD/IQEOGrrdAoGANq1bPWxLaTUctOY7uzEV\nUzxBZNrsL+YYyUVaKROBA/li3uhJQotMiXNg3q5zrHbCnVoZu3ccHGsmAswFZXa7\nOjOQmht/En8M8rm0jAHfDDNWsI1V1R1+9/dKu0RbJCwfQM6DvTmBBrlzOSkN3Em6\nZviQ/foMJ92emf4ynvj8Fv0=\n-----END PRIVATE KEY-----\n",
            "client_email": "odoo-sync@odoo-sync-321221.iam.gserviceaccount.com",
            "client_id": "110651019865056764435",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/odoo-sync%40odoo-sync-321221.iam.gserviceaccount.com"
        }

        index = 0

        result = synce_model.getMasterDatabaseSheet(None, None, None)
        self.assertEqual(len(result) > 0, False)

        
           