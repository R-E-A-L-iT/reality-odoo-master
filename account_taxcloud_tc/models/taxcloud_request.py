import hashlib
import logging
import re

import requests

from odoo import fields, modules, api
from odoo.tools import LazyTranslate
from odoo.tools.zeep import Client
from odoo.tools.zeep.exceptions import Fault
from odoo.exceptions import UserError, ValidationError

_lt = LazyTranslate(__name__)

_logger = logging.getLogger(__name__)


class TaxCloudRequest:
    """Low-level object intended to interface Odoo recordsets with TaxCloud,
    through appropriate SOAP requests"""

    BASE_URL = "https://api.v3.taxcloud.com/tax"
    VERIFY_URL = "https://api.v3.taxcloud.com/tax/verify-address"

    def __init__(self, env, api_id, api_key, api_version='v3'):
        self.env = env
        self.api_key = api_key
        self.api_version = api_version

        if self.api_version == 'v3':
            self.connection_id = api_id  # V3 uses 'connectionId'
            self.api_login_id = None
        else:
            self.api_login_id = api_id   # V1 uses 'apiLoginId'
            self.connection_id = None
        self.ExemptionCertificate = None

        wsdl_path = (
            modules.get_module_path("account_taxcloud_tc") + "/api/taxcloud.wsdl"
        )
        self.client = Client("file:///%s" % wsdl_path)
        self.factory = self.client.type_factory("ns0")

        self.headers = {
            'X-API-KEY': self.api_key.strip(),
            "Content-Type": "application/json",
        }

    def verify_address(self, partner):
        if self.api_version == 'v3':
            return self._verify_address_v3(partner)
        else:
            return self._verify_address_v1(partner)
    # ------------------------------------------------------------
    # ✅ VERIFY ADDRESS - REST V3 IMPLEMENTATION
    # ------------------------------------------------------------

    def _verify_address_v3(self, partner):
        zip_code = (partner.zip or "").strip()

        # ✅ CLEAN INVALID ZIP VALUES
        if "-" in zip_code:
            zip_code = zip_code.split("-")[0]  # Keep only 5-digit ZIP

        payload = {
            "line1": partner.street or "",
            "line2": partner.street2 or "",
            "city": partner.city or "",
            "state": partner.state_id.code or "",
            "zip": zip_code,   # ✅ ONLY 5-digit ZIP
        }

        response = requests.post(
            self.VERIFY_URL,
            json=payload,
            headers=self.headers,
            timeout=30,
        )

        data = response.json()

        # ✅ HANDLE VALIDATION FAILURE
        if response.status_code == 422:
            error = data.get("errors", [{}])[0].get("message", "Invalid address")
            raise ValidationError(f"TaxCloud Address Validation Failed: {error}")

        if response.status_code != 200:
            raise ValidationError(
                f"TaxCloud Verify Address Error: {response.status_code} - {data}"
            )
        return data
    def _verify_address_v1(self, partner):
        zip_match = re.match(r"^\D*(\d{5})\D*(\d{4})?", partner.zip or "")
        zips = list(zip_match.groups()) if zip_match else []
        address_to_verify = {
            "apiLoginID": self.api_login_id,
            "apiKey": self.api_key,
            "Address1": partner.street or "",
            "Address2": partner.street2 or "",
            "City": partner.city,
            "State": partner.state_id.code,
            "Zip5": zips.pop(0) if zips else "",
            "Zip4": zips.pop(0) if zips else "",
        }
        res = requests.post(
            "https://api.taxcloud.com/1.0/TaxCloud/VerifyAddress",
            data=address_to_verify,
            timeout=60,
        ).json()
        if int(res.get("ErrNumber", False)):
            # If VerifyAddress fails, use Lookup with the initial address
            _logger.info(
                "Could not verify address for partner #%s"
                " using taxcloud; using unverified address instead",
                partner.id,
            )
            res.update(address_to_verify)
        return res

    # ------------------------------------------------------------
    # LOCATION SETTERS (UNCHANGED API FLOW)
    # ------------------------------------------------------------

    def set_location_origin_detail(self, shipper):
        address = self.verify_address(shipper)
        if self.api_version == 'v3':
            self.origin = {
                "line1": address.get("line1"),
                "line2": address.get("line2"),
                "city": address.get("city"),
                "state": address.get("state"),
                "zip": address.get("zip"),
            }
        else:
            self.origin = self.factory.Address()
            self.origin.Address1 = address["Address1"] or ""
            self.origin.Address2 = address["Address2"] or ""
            self.origin.City = address["City"]
            self.origin.State = address["State"]
            self.origin.Zip5 = address["Zip5"]
            self.origin.Zip4 = address["Zip4"]



    def set_location_destination_detail(self, recipient_partner):
        address = self.verify_address(recipient_partner)
        if self.api_version == 'v3':
            self.destination = {
                "line1": address.get("line1"),
                "line2": address.get("line2"),
                "city": address.get("city"),
                "state": address.get("state"),
                "zip": address.get("zip"),
            }
        else:
            self.destination = self.factory.Address()
            self.destination.Address1 = address["Address1"] or ""
            self.destination.Address2 = address["Address2"] or ""
            self.destination.City = address["City"]
            self.destination.State = address["State"]
            self.destination.Zip5 = address["Zip5"]
            self.destination.Zip4 = address["Zip4"]

    # ------------------------------------------------------------
    # SINGLE ITEM MODE
    # ------------------------------------------------------------

    def set_items_detail(self, product_id, tic_code):
        if self.api_version == 'v3':
            self.cart_items = [{
                "index": 0,
                "itemId": str(product_id),
                "price": 100,
                "quantity": 1,
                "tic": tic_code if tic_code else 0
            }]
        else:
            self.cart_items = self.factory.ArrayOfCartItem()
            self.cart_item = self.factory.CartItem()
            self.cart_item.Index = 1
            self.cart_item.ItemID = product_id
            if tic_code:
                self.cart_item.TIC = tic_code
            self.cart_item.Price = 100
            self.cart_item.Qty = 1
            self.cart_items.CartItem = [self.cart_item]


    # ------------------------------------------------------------
    # INVOICE MODE
    # ------------------------------------------------------------

    def set_invoice_items_detail(self, invoice):
        self.customer_id = invoice.partner_id.id
        self.taxcloud_date = invoice.get_taxcloud_reporting_date()
        self.cart_id = invoice._get_taxcloud_orderid()
        if self.api_version == 'v3':
            self.cart_items = self._process_lines(invoice.invoice_line_ids)
        else:
            self.cart_items = self.factory.ArrayOfCartItem()
            self.cart_items.CartItem = self._process_lines(invoice.invoice_line_ids)

    def _process_lines(self, lines):
        cart_items = []

        for index, line in enumerate(
            lines.filtered(
                lambda l: not (l.display_type in ('line_note', 'line_section') or l.is_downpayment)
            )
        ):
            qty = line._get_qty()
            if line._get_taxcloud_price() >= 0.0 and qty >= 0.0:

                skip_zero_orders = False
                if "is_skip_zero_orders" in line.env.company._fields:
                    skip_zero_orders = line.env.company.is_skip_zero_orders
                skip_zero_invoice = line.env.company.is_skip_zero_invoice

                if not line.price_subtotal and (
                    ((skip_zero_orders) and line._name == "sale.order.line")
                    or ((skip_zero_invoice) and line._name == "account.move.line")
                ):
                    continue

                price_unit = line._get_taxcloud_price() * (
                    1 - (line.discount or 0.0) / 100.0
                )

                tic_category = (
                    line.product_id.tic_category_id
                    or line.product_id.categ_id.tic_category_id
                    or line.company_id.tic_category_id
                    or line.env.company.tic_category_id
                )

                tic_code = tic_category.code if tic_category else 0

                if self.api_version == 'v3':
                    cart_items.append({
                        "index": index,
                        "itemId": str(line.product_id.id),
                        "price": price_unit,
                        "quantity": qty,
                        "tic": int(tic_code),
                    })
                else:
                    # V1 (SOAP) Logic
                    cart_item = self.factory.CartItem()
                    cart_item.Index = index
                    cart_item.ItemID = line.product_id.id
                    if tic_code:
                        cart_item.TIC = tic_code
                    cart_item.Price = price_unit
                    cart_item.Qty = qty
                    cart_items.append(cart_item)

        return cart_items

    def get_all_taxes_values(self):
        if self.api_version == 'v3':
            return self._get_all_taxes_values_v3()
        else:
            return self._get_all_taxes_values_v1()

    # ------------------------------------------------------------
    # ✅ REST V3 TAX CALCULATION (CONNECTION BASED)
    # ------------------------------------------------------------

    def _get_all_taxes_values_v3(self):
        customer_id = getattr(self, "customer_id", "NoCustomerID")

        if not self.connection_id or not self.api_key:
            return {"error_message": "Missing TaxCloud connectionId or API key"}

        if not self.cart_items:
            return {"error_message": "No Cart Items"}

        currency = self.env.context.get("currency") or self.env.company.currency_id

        url = f"{self.BASE_URL}/connections/{self.connection_id}/carts"

        cart_item_data = {
            "currency": {"currencyCode": currency.name},
            "customerId": str(customer_id),
            "destination": self.destination,
            "origin": self.origin,
            "lineItems": self.cart_items,
        }
        if getattr(self, 'ExemptionCertificate', False):
            cart_item_data["exemption"] = {
                "exemptionId": self.ExemptionCertificate
            }

        payload = {
            "items": [cart_item_data]
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=60,
            )
            data = {
                "api_login": self.connection_id,
                "api_url":url,
                "currency": {"currencyCode": currency.name},
                "customerId": str(customer_id),
                "destination": self.destination,
                "origin": self.origin,
                "lineItems": self.cart_items,
            }
            result = response.json()
            module_path = self.__class__.__module__
            self._log_taxcloud_request(data, result, module_path)

        except requests.exceptions.RequestException as e:
            return {"error_message": str(e)}

        # ---- CLEAN TAX MAPPING ----
        tax_values = {}
        cart_id = None
        items = result.get("items", [])
        if items:
            line_items = items[0].get("lineItems", [])
            cart_id = items[0].get("cartId")
            for line in line_items:
                index = line.get("index")
                tax_amount = (line.get("tax") or {}).get("amount", 0.0)
                if index is not None:
                    tax_values[index] = tax_amount

        return {
            "response": result,
            "values": tax_values,
            "cart_id": cart_id,
        }

    def _get_all_taxes_values_v1(self):
        customer_id = (
            hasattr(self, "customer_id") and self.customer_id or "NoCustomerID"
        )
        cart_id = hasattr(self, "cart_id") and self.cart_id or "NoCartID"
        _logger.info(
            "fetching tax values for cart %s (customer: %s)", cart_id, customer_id
        )
        formatted_response = {}
        if not self.api_login_id or not self.api_key:
            formatted_response["error_message"] = _lt(
                "Please configure taxcloud credentials on the current company "
                "or use a different fiscal position"
            )
            return formatted_response
        if len(self.cart_items.CartItem) == 0:
            formatted_response["error_message"] = "No Cart Items"
            return formatted_response

        try:
            response = self.client.service.LookupForDate(
                self.api_login_id,
                self.api_key,
                customer_id,
                cart_id,
                self.cart_items,
                self.origin,
                self.destination,
                False,  # deliveredBySeller
                self.ExemptionCertificate,  # exemptCert
                self.taxcloud_date,  # useDate
            )
            data = {
                'api_login': self.api_login_id,
                'cart_id': cart_id,
                'cart_items': self.cart_items,
                'customer_id': customer_id,
                'destination': self.destination,
                'hash': self.hash,
                'origin': self.origin,
                'taxcloud_date': self.taxcloud_date,
            }
            # Log Taxcloud API request and response
            module_path = self.__class__.__module__
            self._log_taxcloud_request(data, response, module_path)

            formatted_response["response"] = response
            if response.ResponseType == "OK":
                formatted_response["values"] = {}
                if (
                    response.CartItemsResponse
                    and response.CartItemsResponse.CartItemResponse
                ):
                    for item in response.CartItemsResponse.CartItemResponse:
                        index = item.CartItemIndex
                        tax_amount = item.TaxAmount
                        formatted_response["values"][index] = tax_amount
            elif response.ResponseType == "Error":
                formatted_response["error_message"] = response.Messages.ResponseMessage[
                    0
                ].Message
        except Fault as fault:
            formatted_response["error_message"] = fault.message
        except OSError:
            formatted_response["error_message"] = "TaxCloud Server Not Found"
        return formatted_response

    def _log_taxcloud_request(self, data, response, module_path):
        """Log TaxCloud request/response in a separate transaction."""
        with self.env.registry.cursor() as cr:
            try:
                env_new = api.Environment(cr, self.env.uid, self.env.context)
                env_new["taxcloud.log"].sudo().create({
                    "taxcloud_request": data,
                    "taxcloud_response": response,
                    "create_date_time": fields.Datetime.now(),
                    "taxcloud_type": "sale" if any(m in module_path for m in ["sale_account_taxcloud_tc", "sale_loyalty_taxcloud_delivery_tc"]) else "invoice",
                })
                cr.commit()
            except Exception as e:
                _logger.warning("Failed to log TaxCloud request/response: %s", e)
                cr.rollback()

    # Get TIC category on synchronize.
    def get_tic_category(self):
        """Routes the TIC sync request based on the API version."""
        if self.api_version == 'v3':
            return self._get_tic_category_v3()
        else:
            return self._get_tic_category_v1()

    def _get_tic_category_v1(self):
        formatted_response = {}
        try:
            self.response = self.client.service.GetTICs(self.api_login_id, self.api_key)
            if self.response.ResponseType == "OK":
                formatted_response["data"] = self.response.TICs.TIC
            elif self.response.ResponseType == "Error":
                formatted_response[
                    "error_message"
                ] = self.response.Messages.ResponseMessage[0].Message
        except Fault as fault:
            formatted_response["error_message"] = fault.message
        except OSError:
            formatted_response["error_message"] = "TaxCloud Server Not Found"

        return formatted_response

    def _get_tic_category_v3(self):
        """V3 REST Brute-Force method with Cursor Pagination to fetch all TICs."""
        formatted_response = {}
        all_tics = {}

        url = f"{self.BASE_URL}/tic/search"
        search_characters = "abcdefghijklmnopqrstuvwxyz"
        try:
            for char in search_characters:
                cursor = None

                while True:
                    payload = {
                        "query": char,
                        "limit": 100
                    }
                    if cursor:
                        payload["cursor"] = cursor

                    response = requests.post(url, json=payload, headers=self.headers, timeout=15)

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])

                        for item in results:
                            tic_code = item.get('ticId')
                            description = item.get('description', '')

                            if tic_code is not None:
                                all_tics[tic_code] = description

                        cursor = data.get('nextCursor')
                        if not cursor:
                            break
                    else:
                        _logger.warning(
                            "TaxCloud V3 TIC search failed for query '%s'. Code: %s, Error: %s",
                            char, response.status_code, response.text
                        )
                        break

            if 0 not in all_tics and '0' not in all_tics:
                all_tics[0] = 'Uncategorized'

            formatted_response["data"] = [
                {"TICID": k, "Description": v} for k, v in all_tics.items()
            ]

        except requests.exceptions.RequestException as e:
            formatted_response["error_message"] = f"TaxCloud Connection Error: {str(e)}"

        return formatted_response

        # new code(need to review the authentication)
        # url = f"https://api.v3.taxcloud.com/mgmt/connections/{self.connection_id}/products"
        # response = requests.get(url, headers=self.headers)
        # response = response.json()
        # return response

    def get_taxcloud_authorize_with_capture(self, invoice, order_id, reporting_date):
        if self.api_version == 'v3':
            return self._authorize_v3(invoice, order_id, reporting_date)
        else:
            return self._authorize_v1(invoice, order_id, reporting_date)

    def _authorize_v3(self, invoice, order_id, reporting_date):
        url = f"{self.BASE_URL}/connections/{self.connection_id}/carts/orders"
        payload = {
            "cartId": invoice.taxcloud_cart_id,
            "orderId": order_id,
            "completed": True
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            data ={
                "api_login": self.connection_id,
                "api_url":url,
                "cartId": invoice.taxcloud_cart_id,
                "orderId": order_id,
                "completed": True,
            }
            response = response.json()
            module_path = self.__class__.__module__
            self._log_taxcloud_request(data, response, module_path)
            return response
        except requests.exceptions.RequestException as e:
            return {"error_message": str(e)}

    def _authorize_v1(self, invoice, order_id, reporting_date):
        formatted_response = {}
        try:
            response = self.client.service.AuthorizedWithCapture(
                self.api_login_id,
                self.api_key,
                self.customer_id,
                self.cart_id,
                order_id,
                reporting_date,  # DateAuthorized
                reporting_date,  # DateCaptured
            )
            if response.ResponseType == 'Error':
                error_msg = "Unknown TaxCloud Error"
                if response.Messages and response.Messages.ResponseMessage:
                    msgs = response.Messages.ResponseMessage
                    if isinstance(msgs, list):
                        error_msg = msgs[0].Message
                    else:
                        error_msg = msgs.Message
                formatted_response['error_message'] = error_msg

            else:
                formatted_response['response'] = response

        except Exception as e:
            formatted_response['error_message'] = str(e)

        return formatted_response

    def get_taxcloud_returned(self, origin_invoice, invoice_date):
        if self.api_version == 'v3':
            return self._returned_v3(origin_invoice, invoice_date)
        else:
            return self._returned_v1(origin_invoice, invoice_date)
    def _returned_v3(self, origin_invoice, invoice_date):
        if not self.connection_id or not self.api_key:
            return {"error_message": "Missing TaxCloud connectionId or API key"}

        url = f"{self.BASE_URL}/connections/{self.connection_id}/orders/refunds/{origin_invoice}"

        refund_items = []
        if self.cart_items:
            for item in self.cart_items:
                refund_items.append({
                    "itemId": str(item.get("itemId")),  # Ensure string
                    "quantity": float(item.get("quantity", 0)) # Ensure number
                })
        payload = {
            "items": refund_items,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=60,
            )
            data ={
                "api_login": self.connection_id,
                "api_url": url,
                "cart_items": refund_items,
                "invoice_id":origin_invoice,
            }
            response = response.json()
            module_path = self.__class__.__module__
            self._log_taxcloud_request(data, response, module_path)
            return response

        except requests.exceptions.RequestException as e:
            return {"error_message": str(e)}

    def _returned_v1(self, origin_invoice, invoice_date):
        formatted_response = {}
        try:
            response = self.client.service.Returned(
                self.api_login_id,
                self.api_key,
                origin_invoice,
                self.cart_items,
                fields.Datetime.from_string(invoice_date),
            )

            if response.ResponseType == 'Error':
                error_msg = "Unknown TaxCloud Error"

                if response.Messages and response.Messages.ResponseMessage:
                    msgs = response.Messages.ResponseMessage
                    if isinstance(msgs, list):
                        error_msg = msgs[0].Message
                    else:
                        error_msg = msgs.Message

                formatted_response['error_message'] = error_msg
            else:
                formatted_response['response'] = response

        except Exception as e:
            formatted_response['error_message'] = str(e)

        return formatted_response

    def get_taxcloud_captured(self, invoice):
        return self.client.service.Captured(
            self.api_login_id,
            self.api_key,
            invoice,
        )

    @property
    def hash(self):
        # The hash is used as key to cache request responses,
        # to avoid using too much space in the cache.
        # The current date is appended to refresh the value every day.
        hash_parameters = (
            (self.connection_id or "")
            + (self.api_key or "")
            + str(hasattr(self, "customer_id") and self.customer_id or "NoCustomerID")
            + str(hasattr(self, "cart_id") and self.cart_id or "NoCartID")
            + str(self.cart_items)
            + str(self.origin)
            + str(self.destination)
            + fields.Date.to_string(fields.Date.today())
        )
        if hasattr(self, "ExemptionCertificate") and hasattr(
            self.ExemptionCertificate, "CertificateID"
        ):
            hash_parameters += str(self.ExemptionCertificate.CertificateID)
        return hashlib.sha1((hash_parameters).encode("utf-8")).hexdigest()
