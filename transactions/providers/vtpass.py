# transactions/providers/vtpass.py

import logging
from dataclasses import dataclass
from typing import Any, Dict

import requests

from .exceptions import VTPassError

logger = logging.getLogger(__name__)


@dataclass
class VTPassClient:
    """
    Thin HTTP client around the VTPass API.
    """

    base_url: str
    api_key: str
    secret_key: str
    timeout: int = 15  # seconds

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "api-key": self.api_key,
            "secret-key": self.secret_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url.rstrip('/')}/{path}"

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = self._url(path)
        try:
            response = requests.post(
                url,
                json=json,
                headers=self._headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
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


