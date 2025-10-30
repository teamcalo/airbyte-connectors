

from typing import Any, Mapping, Optional

import boto3
import requests
from airbyte_cdk.sources.streams.http.requests_native_auth.abstract_token import AbstractHeaderAuthenticator

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class AWSSigV4Authenticator(AbstractHeaderAuthenticator):
    """
    Base authenticator that uses AWS Signature Version 4 for authentication.
    This authenticator signs HTTP requests using AWS credentials.
    """

    def __init__(self, region: str):
        self.region = region or "us-east-1"
        self.service_name = "amplify"

    def get_session(self) -> boto3.Session:
        """
        To be implemented by subclasses to provide boto3 session.
        """
        raise NotImplementedError("Subclasses must implement get_session()")

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """
        Sign the request using AWS SigV4.
        """
        session = self.get_session()
        credentials = session.get_credentials()

        # Create AWS request for signing
        aws_request = AWSRequest(
            method=request.method,
            url=request.url,
            headers={"Host": f"{self.service_name}.{self.region}.amazonaws.com"},
        )

        # Sign the request
        SigV4Auth(credentials, self.service_name, self.region).add_auth(aws_request)

        # Update the original request with signed headers
        request.headers.update(dict(aws_request.headers))
        return request


class AWSCredentialsAuthenticator(AWSSigV4Authenticator):
    """
    Authenticator using AWS IAM credentials (access key ID and secret access key).
    """

    def __init__(
        self,
        region: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        super().__init__(region)
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key

    def get_session(self) -> boto3.Session:
        """
        Create boto3 session with IAM credentials.
        """
        if self.access_key_id and self.secret_access_key:
            return boto3.Session(
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )
        else:
            # Use default credentials (from environment, ~/.aws/credentials, or instance profile)
            return boto3.Session(region_name=self.region)

    @property
    def auth_header(self) -> str:
        # AWS SigV4 does not use a static auth header; this is required by the abstract base class.
        return "Authorization"

    @property
    def token(self) -> str:
        # AWS SigV4 does not use a static token; this is required by the abstract base class.
        return ""


class AWSRoleAuthenticator(AWSSigV4Authenticator):
    """
    Authenticator using AWS IAM role assumption.
    """

    def __init__(
        self,
        region: str,
        assume_role: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        super().__init__(region)
        self.assume_role = assume_role
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self._cached_session = None

    def get_session(self) -> boto3.Session:
        """
        Create boto3 session by assuming an IAM role.
        The session is cached to avoid repeated assume_role calls.
        """
        if self._cached_session:
            return self._cached_session

        # Create initial session for STS client
        if self.access_key_id and self.secret_access_key:
            sts_session = boto3.Session(
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )
        else:
            sts_session = boto3.Session(region_name=self.region)

        sts_client = sts_session.client("sts", region_name=self.region)

        # Assume the role
        if self.assume_role:
            response = sts_client.assume_role(
                RoleArn=self.assume_role, RoleSessionName="AirbyteAmplifySession"
            )
            credentials = response["Credentials"]

            # Create session with assumed role credentials
            self._cached_session = boto3.Session(
                region_name=self.region,
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        else:
            # If no role specified, use the base session
            self._cached_session = sts_session

        return self._cached_session

    @property
    def auth_header(self) -> str:
        # AWS SigV4 does not use a static auth header; this is required by the abstract base class.
        return "Authorization"

    @property
    def token(self) -> str:
        # AWS SigV4 does not use a static token; this is required by the abstract base class.
        return ""


def get_authenticator(config: Mapping[str, Any]) -> AbstractHeaderAuthenticator:
    """
    Factory function to create the appropriate authenticator based on config.
    """
    region = config.get("region", "us-east-1")
    auth_config = config.get("auth_type", {})
    auth_type = auth_config.get("type")

    if auth_type == "auth_type_credentials":
        return AWSCredentialsAuthenticator(
            region=region,
            access_key_id=auth_config.get("access_key_id"),
            secret_access_key=auth_config.get("secret_access_key"),
        )
    elif auth_type == "auth_type_role":
        return AWSRoleAuthenticator(
            region=region,
            assume_role=auth_config.get("assume_role"),
            access_key_id=auth_config.get("access_key_id"),
            secret_access_key=auth_config.get("secret_access_key"),
        )
    else:
        # Default to credentials authenticator (will use default AWS credentials chain)
        return AWSCredentialsAuthenticator(region=region)
