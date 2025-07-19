
import httpx
from datetime import datetime

from .const import (
    API_ID,
    AUTH_URL,
    CONTRACT_URL,
)

class EauDuPicAPI:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.client = httpx.AsyncClient()
        self.token = None

    async def async_authenticate(self):
        headers = {"api-id": API_ID}
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
        response = await self.client.post(AUTH_URL, headers=headers, json=payload)
        response.raise_for_status()
        self.token = response.headers["authorization"]
        return True

    async def async_get_contract_id(self):
        headers = {"authorization": self.token, "api-id": API_ID}
        response = await self.client.get(CONTRACT_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["id"]

    async def async_get_consumption_data(self):
        contract_id = await self.async_get_contract_id()
        url = f"{CONTRACT_URL}/{contract_id}"
        headers = {"authorization": self.token, "api-id": API_ID}
        response = await self.client.get(url, headers=headers)
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
