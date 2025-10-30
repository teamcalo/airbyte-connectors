

from abc import ABC
from typing import Any, Iterable, Mapping, MutableMapping, Optional, List
from datetime import datetime
from urllib.parse import quote

import requests
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.requests_native_auth.abstract_token import AbstractHeaderAuthenticator


class AmplifyStream(HttpStream, ABC):
    """
    Base stream class for AWS Amplify API streams.
    Implements common functionality for all Amplify streams including pagination,
    datetime transformation, and AWS-specific request handling.
    """

    def __init__(self, region: str, authenticator: AbstractHeaderAuthenticator, **kwargs):
        super().__init__(authenticator=authenticator, **kwargs)
        self.region = region

    @property
    def url_base(self) -> str:
        """Return the API base URL for AWS Amplify."""
        return f"https://amplify.{self.region}.amazonaws.com"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        Handle pagination using AWS Amplify's nextToken pattern.
        AWS Amplify APIs use cursor-based pagination with a nextToken field.
        """
        json_response = response.json()
        next_token = json_response.get("nextToken")
        if next_token:
            return {"nextToken": next_token}
        return None

    def request_params(
        self,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        """
        Set request parameters including pagination token and maxResults.
        """
        params = {"maxResults": 100}
        if next_page_token:
            params.update(next_page_token)
        return params

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Parse the response and transform datetime fields.
        Extracts records from the response using the data_field property.
        """
        json_response = response.json()
        records = json_response.get(self.data_field, [])

        for record in records:
            # Transform datetime fields from timestamp to ISO format
            yield self.transform_datetime_fields(record)

    def transform_datetime_fields(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Transform datetime fields from Unix timestamp to ISO 8601 format.
        Handles fields like createTime, updateTime, startTime, endTime, commitTime.

        AWS Amplify returns timestamps as Unix epochs (seconds or milliseconds).
        This method converts them to ISO 8601 format for consistency.
        """
        datetime_fields = ["createTime", "updateTime", "startTime", "endTime", "commitTime"]

        for field in datetime_fields:
            if field in record and record[field] is not None:
                try:
                    # Convert scientific notation to float
                    timestamp = float(record[field])
                    # Convert to seconds if in milliseconds
                    if timestamp > 1e11:
                        timestamp = timestamp / 1000
                    # Convert to datetime string
                    dt = datetime.fromtimestamp(timestamp)
                    record[field] = dt.isoformat()
                except (ValueError, TypeError):
                    # If conversion fails, keep original value
                    pass

        return record


class AppsStream(AmplifyStream):
    """
    Stream for AWS Amplify applications.
    This is the parent stream for branches and jobs.

    API Reference: https://docs.aws.amazon.com/amplify/latest/APIReference/API_ListApps.html
    """

    primary_key = "appId"
    data_field = "apps"

    @property
    def name(self) -> str:
        return "apps"

    def path(
        self,
        stream_state: Mapping[str, Any] = None,
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> str:
        return "/apps"


class BranchesStream(AmplifyStream):
    """
    Stream for AWS Amplify branches.
    This is a substream that depends on the AppsStream.
    Each app can have multiple branches.

    API Reference: https://docs.aws.amazon.com/amplify/latest/APIReference/API_ListBranches.html
    """

    primary_key = "branchName"
    data_field = "branches"

    @property
    def name(self) -> str:
        return "branches"

    def __init__(self, parent_stream: AppsStream, **kwargs):
        super().__init__(**kwargs)
        self.parent_stream = parent_stream

    def path(
        self,
        stream_state: Mapping[str, Any] = None,
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> str:
        app_id = stream_slice["app_id"]
        return f"/apps/{app_id}/branches"

    def request_params(
        self,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        """
        Set request parameters with a lower maxResults for branches.
        """
        params = {"maxResults": 50}
        if next_page_token:
            params.update(next_page_token)
        return params

    def stream_slices(
        self, sync_mode, cursor_field: List[str] = None, stream_state: Mapping[str, Any] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """
        Generate slices based on parent stream (apps).
        Each app becomes a slice for fetching branches.
        """
        for app_record in self.parent_stream.read_records(sync_mode=sync_mode):
            yield {"app_id": app_record["appId"]}


class JobsStream(AmplifyStream):
    """
    Stream for AWS Amplify deployment jobs.
    This is a substream that depends on both AppsStream and BranchesStream.
    Each branch can have multiple build/deployment jobs.

    API Reference: https://docs.aws.amazon.com/amplify/latest/APIReference/API_ListJobs.html
    """

    primary_key = "jobId"
    data_field = "jobSummaries"

    @property
    def name(self) -> str:
        return "jobs"

    def __init__(self, parent_streams: Mapping[str, AmplifyStream], **kwargs):
        super().__init__(**kwargs)
        self.apps_stream = parent_streams["apps"]
        self.branches_stream = parent_streams["branches"]

    def path(
        self,
        stream_state: Mapping[str, Any] = None,
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> str:
        app_id = stream_slice["app_id"]
        branch_name = stream_slice["branch_name"]
        # URL encode the branch name to handle slashes and special characters
        encoded_branch = quote(branch_name, safe="")
        return f"/apps/{app_id}/branches/{encoded_branch}/jobs"

    def request_params(
        self,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        """
        Set request parameters with a lower maxResults for jobs.
        """
        params = {"maxResults": 50}
        if next_page_token:
            params.update(next_page_token)
        return params

    def stream_slices(
        self, sync_mode, cursor_field: List[str] = None, stream_state: Mapping[str, Any] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """
        Generate slices based on parent stream (branches).
        Each branch becomes a slice for fetching jobs.

        This iterates through all apps, then all branches for each app,
        and creates a slice for each app/branch combination.
        """
        for app_record in self.apps_stream.read_records(sync_mode=sync_mode):
            app_id = app_record["appId"]
            # Get branches for this app
            for branch_record in self.branches_stream.read_records(
                sync_mode=sync_mode, stream_slice={"app_id": app_id}
            ):
                yield {"app_id": app_id, "branch_name": branch_record["branchName"]}
