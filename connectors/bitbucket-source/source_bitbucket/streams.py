from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

from airbyte_cdk import BasicHttpAuthenticator, SyncMode
import requests
from airbyte_cdk.sources.streams.http import HttpStream


class BitbucketStream(HttpStream, ABC):
    """
    Base stream class for Bitbucket API streams.
    Implements common functionality including cursor-based pagination and rate limiting.
    """

    # Bitbucket uses cursor-based pagination with a 'next' URL in responses
    @property
    def url_base(self) -> str:
        return "https://api.bitbucket.org/2.0/"

    @property
    def page_size(self) -> int:
        return 100

    def __init__(
        self, config: Mapping[str, Any], authenticator: BasicHttpAuthenticator, **kwargs
    ):
        super().__init__(authenticator=authenticator, **kwargs)
        self.config = config
        self.workspace = config["workspace"]
        self.start_date = config.get("start_date", "2020-01-01T00:00:00Z")

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        """
        Bitbucket uses cursor-based pagination with a 'next' URL.
        The next URL is a complete URL, not just a token.
        """
        json_response = response.json()
        next_url = json_response.get("next")

        if next_url:
            # Return the full next URL - we'll use it in request_path
            return {"next_url": next_url}
        return None

    def request_params(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        """
        Set request parameters including page size.
        If we have a next_page_token, we don't need params (they're in the URL).
        """
        if next_page_token:
            # When using next URL, don't add additional params
            return {}

        params = {"pagelen": self.page_size}
        return params

    def path(
        self,
        *,
        stream_state: Optional[Mapping[str, Any]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        Return the API path. If we have a next_page_token with next_url,
        extract the path from that URL.
        """
        if next_page_token and "next_url" in next_page_token:
            # Parse the next URL and return path + query
            next_url = next_page_token["next_url"]
            parsed = urlparse(next_url)
            # Return path with query string
            return f"{parsed.path.replace('/2.0/', '')}{parsed.query and '?' + parsed.query or ''}"

        # Return the default path for the first page
        return self.get_path(stream_slice)

    @abstractmethod
    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        """
        To be implemented by subclasses.
        Returns the base path for the first request.
        """
        raise NotImplementedError("Subclasses must implement get_path()")

    def parse_response(
        self,
        response: requests.Response,
        *,
        stream_state: Mapping[str, Any],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Parse the response and extract records from 'values' array.
        """
        json_response = response.json()
        records = json_response.get("values", [])

        for record in records:
            yield record

    def backoff_time(self, response: requests.Response) -> Optional[float]:
        """
        Handle rate limiting with exponential backoff.
        """
        if response.status_code == 429:
            # Bitbucket rate limit - wait 60 seconds
            return 60.0
        return None

    def should_retry(self, response: requests.Response) -> bool:
        """
        Determine if request should be retried based on response.
        """
        if response.status_code in [429, 500, 502, 503, 504]:
            return True
        return False


class RepositoriesStream(BitbucketStream):
    """
    Stream for Bitbucket repositories in a workspace.
    This is the parent stream for pull_requests, commits, and deployments.

    API Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-repositories/
    """
    @property
    def primary_key(self) -> str:
        return "uuid"   

    @property
    def name(self) -> str:
        return "repositories"

    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        return f"repositories/{self.workspace}"


class IncrementalBitbucketStream(BitbucketStream, ABC):
    """
    Base class for incremental streams with client-side datetime filtering.
    """

    _cursor_value = None

    @property
    def cursor_field(self) -> str:
        return "cursor_at"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cursor_value = None

    @property
    def state(self) -> MutableMapping[str, Any]:
        """Return the current stream state."""
        if self._cursor_value:
            return {self.cursor_field: self._cursor_value}
        return {}

    @state.setter
    def state(self, value: MutableMapping[str, Any]):
        """Set the stream state."""
        self._cursor_value = value.get(self.cursor_field)

    def parse_response(
        self,
        response: requests.Response,
        *,
        stream_state: Mapping[str, Any],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Parse response and apply client-side incremental filtering.
        """
        start_date = stream_state.get(self.cursor_field, self.start_date) if stream_state else self.start_date

        # Parse start_date to datetime for comparison
        if isinstance(start_date, str):
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)

        for record in super().parse_response(
            response,
            stream_state=stream_state,
            stream_slice=stream_slice,
            next_page_token=next_page_token,
        ):
            # Add cursor field to record
            record_with_cursor = self.add_cursor_field(record)

            # Filter by start date (client-side incremental)
            cursor_value = record_with_cursor.get(self.cursor_field)
            if cursor_value:
                try:
                    record_dt = datetime.fromisoformat(cursor_value.replace('Z', '+00:00'))
                    if record_dt >= start_dt:
                        # Update cursor
                        if not self._cursor_value or cursor_value > self._cursor_value:
                            self._cursor_value = cursor_value
                        yield record_with_cursor
                except (ValueError, AttributeError):
                    # If date parsing fails, include the record
                    yield record_with_cursor
            else:
                yield record_with_cursor

    @abstractmethod
    def add_cursor_field(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Add cursor field to record. To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_cursor_field()")


class PullRequestsStream(IncrementalBitbucketStream):
    """
    Stream for pull requests in repositories.
    Supports incremental sync based on updated_on field.

    API Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
    """

    @property
    def primary_key(self) -> str:
        return "id"

    @property
    def name(self) -> str:
        return "pull_requests"

    def __init__(self, parent_stream: RepositoriesStream, **kwargs):
        super().__init__(**kwargs)
        self.parent_stream = parent_stream

    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        if not stream_slice:
            raise ValueError("stream_slice is required for PullRequestsStream")
        repository = stream_slice["repository"]
        return f"repositories/{repository}/pullrequests"

    def request_params(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        """Add sort parameter for pull requests."""
        params = super().request_params(stream_state, stream_slice, next_page_token)
        if not next_page_token:
            params["sort"] = "-updated_on"
        return params

    def stream_slices(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """Generate slices based on parent repositories."""
        for repo in self.parent_stream.read_records(sync_mode=SyncMode.full_refresh):
            yield {"repository": repo["full_name"]}

    def add_cursor_field(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Add cursor_at field from updated_on."""
        if "updated_on" in record:
            record["cursor_at"] = record["updated_on"]
        return record


class CommitsStream(IncrementalBitbucketStream):
    """
    Stream for commits in repositories.
    Supports incremental sync based on date field.

    API Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-commits/
    """

    @property
    def primary_key(self) -> str:
        return "hash"

    @property
    def name(self) -> str:
        return "commits"

    def __init__(self, parent_stream: RepositoriesStream, **kwargs):
        super().__init__(**kwargs)
        self.parent_stream = parent_stream

    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        if not stream_slice:
            raise ValueError("stream_slice is required for CommitsStream")
        repository = stream_slice["repository"]
        return f"repositories/{repository}/commits"

    def stream_slices(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """Generate slices based on parent repositories."""
        for repo in self.parent_stream.read_records(sync_mode=SyncMode.full_refresh):
            yield {"repository": repo["full_name"]}

    def add_cursor_field(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Add cursor_at field from date."""
        if "date" in record:
            record["cursor_at"] = record["date"]
        return record


class DeploymentsStream(IncrementalBitbucketStream):
    """
    Stream for deployments in repositories.
    Supports incremental sync based on state.completed_on field.
    Enriches deployment records with environment details.

    API Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-deployments/
    """

    @property
    def primary_key(self) -> str:
        return "uuid"

    @property
    def name(self) -> str:
        return "deployments"

    def __init__(self, parent_stream: RepositoriesStream, **kwargs):
        super().__init__(**kwargs)
        self.parent_stream = parent_stream
        self._environment_cache: Dict[str, Dict[str, Any]] = {}

    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        if not stream_slice:
            raise ValueError("stream_slice is required for DeploymentsStream")
        repository = stream_slice["repository"]
        return f"repositories/{repository}/deployments"

    def request_params(
        self,
        stream_state: Optional[Mapping[str, Any]],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        """Add sort parameter for deployments."""
        params = super().request_params(stream_state, stream_slice, next_page_token)
        if not next_page_token:
            params["sort"] = "-state.completed_on"
        return params

    def stream_slices(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        """Generate slices based on parent repositories."""
        for repo in self.parent_stream.read_records(sync_mode=SyncMode.full_refresh):
            yield {"repository": repo["full_name"]}

    def parse_response(
        self,
        response: requests.Response,
        *,
        stream_state: Mapping[str, Any],
        stream_slice: Optional[Mapping[str, Any]] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Parse response, filter deployments, and enrich with environment details.
        """
        for record in super().parse_response(
            response,
            stream_state=stream_state,
            stream_slice=stream_slice,
            next_page_token=next_page_token,
        ):
            # Filter: only version 3+ deployments with completed_on
            version = record.get("version", 0)
            state = record.get("state", {})
            completed_on = state.get("completed_on")

            if version >= 3 and completed_on:
                # Enrich with environment details
                enriched_record = self.enrich_with_environment(record, stream_slice)
                yield enriched_record

    def enrich_with_environment(self, record: Mapping[str, Any], stream_slice: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
        """
        Enrich deployment record with environment details from API.
        """
        environment_info = record.get("environment", {})
        environment_uuid = environment_info.get("uuid")

        if not environment_uuid:
            return record

        if not stream_slice:
            return record

        repository = stream_slice.get("repository")
        if not repository:
            return record

        # Fetch environment details
        environment_details = self._get_environment_details(repository, environment_uuid)
        if environment_details:
            record["environment"] = environment_details

        return record

    def _get_environment_details(self, repository: str, environment_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch environment details from Bitbucket API with caching.
        """
        cache_key = f"{repository}:{environment_uuid}"

        # Check cache
        if cache_key in self._environment_cache:
            return self._environment_cache[cache_key]

        # Fetch from API
        url = f"{self.url_base}repositories/{repository}/environments/{environment_uuid}"
        try:
            response = requests.get(
                url,
                auth=(self.config["email"], self.config["api_token"]),
                timeout=30
            )

            if response.status_code == 200:
                environment_data = response.json()
                self._environment_cache[cache_key] = environment_data
                return environment_data
            else:
                self._environment_cache[cache_key] = None
                return None

        except requests.exceptions.RequestException:
            self._environment_cache[cache_key] = None
            return None

    def add_cursor_field(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Add cursor_at field from state.completed_on."""
        state = record.get("state", {})
        if "completed_on" in state:
            record["cursor_at"] = state["completed_on"]
        else:
            # Fallback to current time if no completed_on
            record["cursor_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return record


class WorkspaceUsersStream(BitbucketStream):
    """
    Stream for workspace members/users.
    Full refresh only.

    API Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-workspaces/
    """

    @property
    def primary_key(self) -> str:
        return "uuid"

    @property
    def name(self) -> str:
        return "workspace_users"

    def get_path(self, stream_slice: Optional[Mapping[str, Any]] = None) -> str:
        return f"workspaces/{self.workspace}/members"
