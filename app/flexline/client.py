import base64
import json
import logging

import boto3
from pydantic import ValidationError

# Import the schema from the new file
from .schemas import QueryInfo

# --- Custom Exception ---


class FlexlineError(Exception):
    """Custom exception for errors during Flexline Lambda execution."""

    pass


# --- Main Lambda Client Class ---
logger = logging.getLogger(__name__)


class FlexlineClient:
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        api_key: str,
        username: str,
        password: str,
    ):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.client = boto3.client(
            "lambda",
            region_name="us-east-1",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    @property
    def encoded_api_key(self) -> str:
        return base64.b64encode(self.api_key.encode()).decode()

    def _invoke_lambda(
        self, lambda_name: str, params: dict | None = None, body: dict | None = None
    ) -> dict:
        request_payload = {
            "headers": {"authorization": self.encoded_api_key},
            "queryStringParameters": params,
            "body": json.dumps(body) if body else None,
        }

        try:
            response = self.client.invoke(
                FunctionName=lambda_name, Payload=json.dumps(request_payload).encode()
            )
            payload = response["Payload"].read().decode()
            response_payload = json.loads(payload)

            status_code = response_payload.get("statusCode")
            response_body = json.loads(response_payload.get("body", "{}"))

            if status_code != 200:
                raise FlexlineError(
                    f"Lambda function '{lambda_name}' failed with status {status_code}: {response_body}"
                )

            return response_body
        except Exception as e:
            logger.error(f"Error invoking Lambda function '{lambda_name}': {e}")
            raise FlexlineError(f"Failed to communicate with AWS Lambda. {e}")

    def _get_auth_token(self) -> str:
        logger.info("Authenticating with Flexline service...")
        result = self._invoke_lambda(
            "Sbl_Authenticate", {"user": self.username, "pass": self.password}
        )
        token = result.get("token", result) if isinstance(result, dict) else result
        if not token:
            raise FlexlineError(
                "Authentication with Flexline service failed, token not received."
            )
        return token

    def _get_route(self, token: str) -> QueryInfo:
        logger.info("Getting route from Flexline service...")
        result = self._invoke_lambda(
            "Sbl_GetRoute", {"userId": self.username, "empresaId": token}
        )
        try:
            return QueryInfo.model_validate(result)
        except ValidationError as e:
            raise FlexlineError(f"Failed to parse route information from Lambda: {e}")

    def _process_query(self, sql_query: str, query_info: QueryInfo) -> list[dict]:
        logger.info("Processing query via FlexlineData Lambda...")
        query_info.command = sql_query.replace(";", "") + " for json path"
        body_payload = query_info.model_dump(by_alias=True, exclude_none=True)
        return self._invoke_lambda("FlexlineData", body=body_payload)

    def run(self, sql_query: str) -> list[dict]:
        logger.info("Starting Flexline Lambda execution run.")
        token = self._get_auth_token()
        query_info = self._get_route(token)
        return self._process_query(sql_query, query_info)
