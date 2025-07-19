
import httpx
from datetime import datetime

import logging

from .const import (
    API_ID,
    AUTH_URL,
    CONTRACT_URL,
)

_LOGGER = logging.getLogger(__name__)

class EauDuPicAPI:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.client = httpx.AsyncClient()
        self.token = None

    async def async_authenticate(self):
        # First, perform a GET request to the login page to obtain necessary cookies/session info
        login_page_url = "https://eaudupic.client.ccgpsl.fr/public/connexion"
        get_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Referer": "https://eaudupic.client.ccgpsl.fr/public",
            "Origin": "https://eaudupic.client.ccgpsl.fr",
        }
        try:
            get_response = await self.client.get(login_page_url, headers=get_headers)
            get_response.raise_for_status()
        except httpx.HTTPStatusError as e:
            _LOGGER.error("GET request to login page failed: HTTP status error: %s", e.response.status_code)
            _LOGGER.error("Response headers: %s", e.response.headers)
            _LOGGER.error("Response body: %s", e.response.text)
            raise
        except httpx.RequestError as e:
            _LOGGER.error("GET request to login page failed: Request error: %s", e)
            raise

        # Now, proceed with the POST authentication request
        headers = {
            "api-id": API_ID,
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
            "Origin": "https://eaudupic.client.ccgpsl.fr",
            "Referer": "https://eaudupic.client.ccgpsl.fr/public/connexion",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        }
        payload = {
            "data": {
                "type": "POICL_Signin",
                "id": "",
                "attributes": {
                    "login": self.email,
                    "password": self.password,
                    "remember": False,
                },
            }
        }

        try:
            response = await self.client.post(AUTH_URL, headers=headers, json=payload)
            response.raise_for_status()
            self.token = response.headers["authorization"]
            return True
        except httpx.HTTPStatusError as e:
            _LOGGER.error("POST authentication failed: HTTP status error: %s", e.response.status_code)
            _LOGGER.error("Response headers: %s", e.response.headers)
            _LOGGER.error("Response body: %s", e.response.text)
            raise
        except httpx.RequestError as e:
            _LOGGER.error("POST authentication failed: Request error: %s", e)
            raise

    async def async_get_contract_id(self):
        headers = {
            "authorization": self.token,
            "api-id": API_ID,
            "Accept": "application/vnd.api+json",
            "Referer": "https://eaudupic.client.ccgpsl.fr/accueil",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        }
        params = {"include": "pconso,pconso.pdessadr"}
        try:
            response = await self.client.get(CONTRACT_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("Contract ID response: %s", data)
            return data["data"][0]["id"]
        except httpx.HTTPStatusError as e:
            _LOGGER.error("Failed to get contract ID: HTTP status error: %s", e.response.status_code)
            _LOGGER.error("Response headers: %s", e.response.headers)
            _LOGGER.error("Response body: %s", e.response.text)
            raise
        except httpx.RequestError as e:
            _LOGGER.error("Failed to get contract ID: Request error: %s", e)
            raise
        except IndexError:
            _LOGGER.error("Failed to get contract ID: 'data' field in response is empty or malformed.")
            raise

    async def async_get_consumption_data(self, contract_id: str):
        url = f"{CONTRACT_URL}/{contract_id}"
        headers = {
            "authorization": self.token,
            "api-id": API_ID,
            "Accept": "application/vnd.api+json",
            "Referer": f"https://eaudupic.client.ccgpsl.fr/contrat/{contract_id}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        }
        params = {"include": "proprietes,pconso,pconso.pdessadr,pconso.compteur,pconso.dernierreleve,pconso.derniermessage,pconso.proprietes,redevable_actif.personne.proprietes,telereleve"}
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            releve_info = None
            for item in data.get("included", []):
                if item.get("type") == "POGRC_Releve":
                    releve_info = item["attributes"]
                    break

            if releve_info:
                return {
                    "value": releve_info.get("consorlv"),
                    "startDate": datetime.fromisoformat(releve_info.get("dateai")).strftime("%Y-%m-%d"),
                    "endDate": datetime.fromisoformat(releve_info.get("dateni")).strftime("%Y-%m-%d"),
                }
            return None
        except httpx.HTTPStatusError as e:
            _LOGGER.error("Failed to get consumption data: HTTP status error: %s", e.response.status_code)
            _LOGGER.error("Response headers: %s", e.response.headers)
            _LOGGER.error("Response body: %s", e.response.text)
            raise
        except httpx.RequestError as e:
            _LOGGER.error("Failed to get consumption data: Request error: %s", e)
            raise
