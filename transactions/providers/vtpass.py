# transactions/providers/vtpass.py

import logging
from typing import Any, Dict

import httpx

from .exceptions import VTPassError

logger = logging.getLogger(__name__)


class VTPassClient:
    """
    HTTP client for VTPass API with connection pooling and optimized timeouts.

    Uses httpx for better performance:
    - Connection pooling (reuses TCP connections)
    - Separate connect/read timeouts
    - HTTP/2 support (if server supports it)
    """

    # Singleton httpx client for connection pooling across requests
    _client: httpx.Client | None = None

    def __init__(
        self,
        base_url: str,
        api_key: str,
        secret_key: str,
        connect_timeout: float = 5.0,  # Time to establish connection
        read_timeout: float = 15.0,     # Time to receive response
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=5.0,
            pool=5.0,
        )
        self._headers = {
            "api-key": self.api_key,
            "secret-key": self.secret_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def client(self) -> httpx.Client:
        """
        Lazy-initialize a shared httpx client with connection pooling.
        The client is shared across all VTPassClient instances for maximum reuse.
        """
        if VTPassClient._client is None or VTPassClient._client.is_closed:
            VTPassClient._client = httpx.Client(
                timeout=self.timeout,
                headers=self._headers,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
            )
        return VTPassClient._client

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = self._url(path)
        try:
            response = self.client.post(url, json=json)
        except httpx.ConnectTimeout as exc:
            logger.error("VTPass connection timeout: %s", url)
            raise VTPassError("Connection to VTPass timed out. Please try again.") from exc
        except httpx.ReadTimeout as exc:
            logger.error("VTPass read timeout: %s", url)
            raise VTPassError("VTPass took too long to respond. Please try again.") from exc
        except httpx.HTTPError as exc:
            logger.exception("VTPass network error")
            raise VTPassError("Network error while contacting VTPass") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("VTPass returned non-JSON response: %s", response.text[:300])
            raise VTPassError("Invalid response from VTPass", payload={"raw": response.text}) from exc

        logger.debug("VTPass response from %s: %s", url, data)
        return data

    # -------- Public methods --------

    def buy_airtime(
        self,
        service_id: str,
        phone: str,
        amount: str | int | float,
        request_id: str,
    ) -> Dict[str, Any]:

        payload = {
            "serviceID": service_id,
            "phone": phone,
            "amount": str(amount),
            "request_id": request_id,
        }

        data = self._post("pay", json=payload)

        # Normalize response to a dict with a 'code' field
        if not isinstance(data, dict):
            # VTPass returned something unexpected (string, etc.)
            return {
                "code": "ERROR",
                "raw": str(data),
            }

        if "code" not in data:
            data["code"] = "ERROR"

        return data


    def requery(self, request_id: str) -> Dict[str, Any]:
        """
        Requery a previous transaction by our request_id.
        """
        payload = {"request_id": request_id}
        data = self._post("requery", json=payload)

        if "code" not in data:
            raise VTPassError("VTPass requery response missing 'code'", payload=data)

        return data

# -------- Data services --------
    def buy_data(
        self,
        service_id: str,
        phone: str,
        variation_code: str,
        amount: str | int | float,
        request_id: str,
    ) -> dict:
        """
        Purchase data via VTPass.

        :param service_id: e.g. 'mtn-data', 'airtel-data'
        :param phone: customer phone number
        :param variation_code: VTpass variation_code for the data bundle
        :param amount: price of the bundle in Naira
        :param request_id: our unique reference
        """
        payload = {
            "serviceID": service_id,
            "phone": phone,
            "variation_code": variation_code,
            "amount": str(amount),
            "request_id": request_id,
        }

        data = self._post("pay", json=payload)

        # Normalise response
        if not isinstance(data, dict):
            return {
                "code": "ERROR",
                "raw": str(data),
            }

        if "code" not in data:
            data["code"] = "ERROR"

        return data

    
    def verify_meter(self, service_id: str, meter_number: str, meter_type: str) -> dict:
        """
        Verify a prepaid/postpaid meter number via VTpass merchant-verify API.
        meter_type: 'prepaid' or 'postpaid'
        """
        payload = {
            "billersCode": meter_number,
            "serviceID": service_id,
            "type": meter_type,
        }
        data = self._post("merchant-verify", json=payload)

        if not isinstance(data, dict):
            return {"code": "ERROR", "raw": str(data)}

        if "code" not in data:
            data["code"] = "ERROR"

        return data

    def pay_electricity(
        self,
        service_id: str,
        meter_number: str,
        meter_type: str,
        amount,
        phone: str,
        request_id: str,
    ) -> dict:
        """
        Vend electricity (prepaid token or postpaid bill payment).
        meter_type: 'prepaid' or 'postpaid'
        """
        payload = {
            "request_id": request_id,
            "serviceID": service_id,
            "billersCode": meter_number,
            "variation_code": meter_type,
            "amount": str(amount),
            "phone": phone,
        }
        data = self._post("pay", json=payload)

        if not isinstance(data, dict):
            return {"code": "ERROR", "raw": str(data)}

        if "code" not in data:
            data["code"] = "ERROR"

        return data


