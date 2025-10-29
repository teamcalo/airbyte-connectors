from dataclasses import dataclass, InitVar
from abc import ABC, abstractmethod

import boto3
import requests
from airbyte_cdk.sources.declarative.auth.declarative_authenticator import DeclarativeAuthenticator
from airbyte_cdk.sources.declarative.interpolation import InterpolatedString
from airbyte_cdk.sources.declarative.transformations import RecordTransformation
from airbyte_cdk.sources.types import Config, Record, StreamSlice, StreamState
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import Union, Mapping, Any, Optional
from datetime import datetime


@dataclass
class BaseIAMAuthenticator(DeclarativeAuthenticator, ABC):
    config: Config
    parameters: InitVar[Mapping[str, Any]]

    @abstractmethod
    def sign(self):
        pass

    def __call__(self, request: requests.PreparedRequest):
        region = self.config.get("region", "us-east-1")

        aws_req = AWSRequest(method=request.method, url=request.url, headers={"Host": f"amplify.{region}.amazonaws.com"})
        SigV4Auth(self.sign(), "amplify", region).add_auth(aws_req)

        request.headers.update(dict(aws_req.headers))
        return request


@dataclass
class IAMCredentialsAuthenticator(BaseIAMAuthenticator):
    access_key_id: Union[InterpolatedString, str]
    secret_access_key: Union[InterpolatedString, str]
    config: Config

    def sign(self):
        region = self.config.get("region", "us-east-1")

        session = boto3.Session(
            region_name=region,
            aws_access_key_id=str(self.access_key_id.eval(self.config)),
            aws_secret_access_key=str(self.secret_access_key.eval(self.config)),
        )
        return session.get_credentials()

    def __post_init__(self, parameters: Mapping[str, Any]):
        if isinstance(self.access_key_id, str):
            self.access_key_id = InterpolatedString(self.access_key_id, parameters=parameters)
        if isinstance(self.secret_access_key, str):
            self.secret_access_key = InterpolatedString(self.secret_access_key, parameters=parameters)


@dataclass
class IAMRoleAuthenticator(BaseIAMAuthenticator):
    assume_role: Union[InterpolatedString, str]
    config: Config

    def sign(self):
        region = self.config.get("region", "us-east-1")
        sts_client = boto3.client("sts", region_name=region)
        response = sts_client.assume_role(
            RoleArn=str(self.assume_role.eval(self.config)), 
            RoleSessionName="CrossAcctSession"
        )
        credentials = response['Credentials']

        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
        return session.get_credentials()

    def __post_init__(self, parameters: Mapping[str, Any]):
        if isinstance(self.assume_role, str):
            self.assume_role = InterpolatedString(self.assume_role, parameters=parameters)


class DateTimeTransformation(RecordTransformation):
    DATETIME_FIELDS = [
        "commitTime",
        "startTime",
        "endTime",
        "createTime",
        "updateTime",
    ]

    def transform(
        self,
        record: Record,
        config: Optional[Config] = None,
        stream_state: Optional[StreamState] = None,
        stream_slice: Optional[StreamSlice] = None,
    ) -> Record:
        for field in self.DATETIME_FIELDS:
            if field in record and record[field] is not None:
                # Convert scientific notation to float
                timestamp = float(record[field])
                # Convert to seconds if in milliseconds
                if timestamp > 1e11:
                    timestamp = timestamp / 1000
                # Convert to datetime string
                dt = datetime.fromtimestamp(timestamp)
                record[field] = dt.isoformat()
        return record
