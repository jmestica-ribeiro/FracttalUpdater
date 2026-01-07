"""
Fracttal API client for authentication and meter operations.
"""

import base64
import requests
from datetime import datetime, timedelta, timezone


class FracttalAPI:
    """Client for interacting with the Fracttal API."""

    AUTH_URL = "https://one.fracttal.com/oauth/token"
    API_BASE = "https://app.fracttal.com"

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Fracttal API client.

        Args:
            api_key: Fracttal API key
            api_secret: Fracttal API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.token = None

    def authenticate(self) -> bool:
        """
        Authenticate with Fracttal and obtain an access token.

        Returns:
            True if authentication was successful, False otherwise.
        """
        # Encode credentials in Base64 as "key:secret"
        auth_string = f"{self.api_key}:{self.api_secret}"
        auth_base64 = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_base64}",
        }

        payload = {"grant_type": "client_credentials"}

        try:
            response = requests.post(self.AUTH_URL, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("access_token")
            return self.token is not None
        except requests.RequestException as e:
            print(f"Authentication error: {e}")
            return False

    def _get_headers(self) -> dict:
        """Get headers with authorization token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_meter_value(self, serial: str) -> float | None:
        """
        Get the current accumulated meter value for an asset.

        Args:
            serial: The asset's serial/internal code (e.g., 'ER-1022')

        Returns:
            The accumulated value, or None if not found.
        """
        url = f"{self.API_BASE}/api/meters?serial={serial}"

        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                return None

            meter = data["data"][0]
            accumulated_value = meter.get("last_data", {}).get("accumulated_value")
            return accumulated_value

        except requests.RequestException as e:
            print(f"Error getting meter for {serial}: {e}")
            return None

    def update_meter(
        self,
        serial: str,
        new_value: float,
        is_historical: bool = False,
        fecha: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        Update the meter reading for an asset.

        Args:
            serial: The asset's serial/internal code
            new_value: The new accumulated value
            is_historical: True for historical readings, False for current
            fecha: Optional datetime, defaults to current time (UTC-3)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Set timezone to Argentina (UTC-3)
        zona_arg = timezone(timedelta(hours=-3))
        if fecha is None:
            fecha = datetime.now(zona_arg)

        # Format date for Fracttal
        fecha_formato = fecha.strftime("%Y-%m-%dT%H:%M:%S-03:00")

        payload = {
            "date": fecha_formato,
            "value": new_value,
            "serial": serial,
            "is_historical": is_historical,
        }

        url = f"{self.API_BASE}/api/meter_reading?code={serial}"

        try:
            response = requests.put(url, headers=self._get_headers(), json=payload)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True, "Contador actualizado correctamente."
                else:
                    return False, f"Error reportado por Fracttal: {data}"
            else:
                return False, f"Error HTTP {response.status_code}: {response.text}"

        except requests.RequestException as e:
            return False, f"Excepción al actualizar contador: {e}"
