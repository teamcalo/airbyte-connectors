from dataclasses import dataclass

import boto3
import requests
from airbyte_cdk.sources.declarative.auth.declarative_authenticator import DeclarativeAuthenticator
from airbyte_cdk.sources.declarative.types import Config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


@dataclass
class IAMAuthenticator(DeclarativeAuthenticator):
    config: Config

    def __call__(self, request: requests.PreparedRequest):
        region = self.config.get("region", "us-east-1")
        access_key_id = self.config.get("access_key_id", None)
        secret_access_key = self.config.get("secret_access_key", None)
        assume_role = self.config.get("assume_role", None)

        credentials = None
        if assume_role:
            sts_client = boto3.client(
                "sts",
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )
            credentials = sts_client.assume_role(
                RoleArn=assume_role, RoleSessionName="CrossAcctSession"
            )["Credentials"]
        else:
            session = boto3.Session(
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                
            )
            credentials = session.get_credentials()
        
        aws_req = AWSRequest(method=request.method, url=request.url, headers={"Host": f"amplify.{region}.amazonaws.com"})

        SigV4Auth(credentials, "amplify", region).add_auth(aws_req)

        request.headers.update(dict(aws_req.headers))
        return request
