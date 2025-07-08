import logging

import requests

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Text2SQLClient:
    def __init__(self, base_url: str, workspace_id: str):
        self.base_url = base_url
        self.workspace_id = workspace_id
        # Credentials and token will be stored here
        self._username = None
        self._password = None
        self.token = None

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticates with the API, stores credentials, and retrieves a token."""
        auth_url = f"{self.base_url}/api/auth/token"
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        try:
            response = requests.post(auth_url, data=payload)
            response.raise_for_status()
            self.token = response.json().get("access_token")
            if self.token:
                # Store credentials only on successful authentication
                self._username = username
                self._password = password
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with SaaS API: {e}")
            return False

    def get_sql(self, question: str) -> dict | None:
        """
        Calls the AI service to get the SQL query.
        Handles token expiration and re-authentication automatically.
        """
        # --- First Attempt ---
        response = self._make_request(question)

        # --- Handle Expired Token and Retry ---
        if response and response.status_code == 401:
            logger.info("Token expired or invalid. Attempting to re-authenticate...")
            if self.authenticate(self._username, self._password):
                logger.info("Re-authentication successful. Retrying the request...")
                # --- Second Attempt ---
                response = self._make_request(question)
            else:
                logger.error("Re-authentication failed. Cannot proceed.")
                return None

        # --- Process Final Response ---
        if response and response.ok:
            data = response.json()
            if not data.get("read_only"):
                logger.warning(
                    "API returned a query that is not flagged as read-only. Rejecting."
                )
                return None
            return data
        elif response:
            logger.error(
                f"API request failed with status {response.status_code}: {response.text}"
            )

        return None

    def _make_request(self, question: str) -> requests.Response | None:
        """Helper method to make the actual API request."""
        if not self.token:
            logger.error("Authentication token not found.")
            return None

        ai_url = f"{self.base_url}/api/ai/{self.workspace_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"question": question}
        try:
            # We don't raise for status here, so we can handle 401s manually
            return requests.get(ai_url, headers=headers, params=params)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get SQL from AI service: {e}")
            return None
