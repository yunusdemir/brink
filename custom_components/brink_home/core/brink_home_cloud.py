"""Implementation for Eldes Cloud"""
import asyncio
import async_timeout
import logging
import aiohttp

from ..const import API_URL, API_PATHS

_LOGGER = logging.getLogger(__name__)


class BrinkHomeCloud:
    """Interacts with Brink Home via public API."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        """Performs login and save session cookie."""
        self.timeout = 10
        self.headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "okhttp/3.11.0",
            "Content-Type": "application/json; charset=UTF-8",
        }
        self.token_exists = None

        self._http_session = session
        self._username = username
        self._password = password

    async def _api_call(self, url, method, data=None):
        try:
            async with async_timeout.timeout(self.timeout):
                req = await self._http_session.request(
                    method,
                    url,
                    json=data,
                    headers=self.headers
                )
            req.raise_for_status()
            return req

        except aiohttp.ClientError as err:
            _LOGGER.error("Client error on API %s request %s", url, err)
            raise

        except asyncio.TimeoutError:
            _LOGGER.error("Client timeout error on API request %s", url)
            raise

    async def login(self):
        data = {
            'UserName': self._username,
            'Password': self._password,
        }

        url = f"{API_URL}UserLogon"

        resp = await self._api_call(url, "POST", data)
        result = await resp.json()
        self.token_exists = True

        _LOGGER.debug(
            "login result: %s",
            result
        )

        return result

    async def get_systems(self):
        """Gets systems list."""
        url = f"{API_URL}GetSystemList"

        response = await self._api_call(url, "GET")
        result = await response.json()

        mapped_result = []

        for system in result:
            mapped_result.append({
                'system_id': system["id"],
                'gateway_id': system["gatewayId"],
                'name': system['name']
        })

        _LOGGER.debug(
            "get_systems result: %s",
            mapped_result
        )

        return mapped_result

    async def get_description_values(self, system_id, gateway_id):
        """Gets values info."""
        url = f"{API_URL}GetParameterValues?GatewayId={gateway_id}&SystemId={system_id}"

        response = await self._api_call(url, "GET")
        result = await response.json()
        menu_items = result.get("menuItems", [])
        pages = menu_items.get("pages", [])
        home_page = pages[0]
        parameters = home_page.get("parameterDescriptors", [])
        ventilation = parameters[0]
        mode = parameters[1]

        description_result = {
            "ventilation": self.__get_type(ventilation),
            "mode": self.__get_type(mode)
        }

        _LOGGER.debug(
            "get_description_values result: %s",
            description_result
        )

        return description_result

    def __get_type(self, type):
        return {
            "name": type["name"],
            "value_id": type["valueId"],
            "value": type["value"],
            "values": self.__get_values(type)
        }

    @staticmethod
    def __get_values(type):
        values = type["listItems"]
        extracted = []
        for value in values:
            if value["isSelectable"]:
                extracted.append({
                    "value": value["value"],
                    "text": value["displayText"]
                })

        return extracted

    # 1 as mode value changes mode to manual every time you change ventilation value
    async def set_ventilation_value(self, system_id, gateway_id, mode, ventilation):
        """Sets alarm to provided mode."""
        data = {
            'GatewayId': gateway_id,
            'SystemId': system_id,
            'WriteParameterValues': [
                {
                    'ValueId': mode["value_id"],
                    'Value': '1',
                },
                {
                    'ValueId': ventilation["value_id"],
                    'Value': ventilation["value"],
                }
            ],
            'SendInOneBundle': True,
            'DependendReadValuesAfterWrite': [
                ventilation["value_id"],
                mode["value_id"]
            ]
        }

        url = f"{API_URL}WriteParameterValuesAsync"

        response = await self._api_call(url, "POST", data)
        result = await response.text()

        _LOGGER.debug(
            "set_ventilation_value result: %s",
            result
        )

        return result

    async def set_mode_value(self, system_id, gateway_id, mode):
        """Sets alarm to provided mode."""
        data = {
            'GatewayId': gateway_id,
            'SystemId': system_id,
            'WriteParameterValues': [
                {
                    'ValueId': mode["value_id"],
                    'Value': mode["value"],
                },
            ],
            'SendInOneBundle': True,
            'DependendReadValuesAfterWrite': [
                mode["value_id"]
            ]
        }

        url = f"{API_URL}WriteParameterValuesAsync"

        response = await self._api_call(url, "POST", data)
        result = await response.text()

        _LOGGER.debug(
            "set_mode_value result: %s",
            result
        )

        return result
