"""
Custom components for Bitbucket source connector.
"""

import logging
from typing import Any, Dict, Mapping, Optional

import requests
from airbyte_cdk.sources.declarative.transformations import RecordTransformation
from airbyte_cdk.sources.types import Config, StreamSlice, StreamState


class EnrichDeploymentWithEnvironmentTransformation(RecordTransformation):
    """
    Custom transformation that enriches deployment records with environment details
    by making additional API calls to Bitbucket's environments endpoint.
    """

    def __init__(self, config: Optional[Config] = None, **kwargs):
        super().__init__(**kwargs)
        # Handle case where config might be passed through kwargs
        self.config = config or kwargs.get('config', {})

        # Extract auth details from config
        if isinstance(self.config, dict):
            email = self.config.get("email")
            api_token = self.config.get("api_token")
        else:
            # Handle case where config might have attributes
            email = getattr(self.config, 'email', None) if self.config else None
            api_token = getattr(self.config, 'api_token', None) if self.config else None

        self._auth = (email, api_token) if email and api_token else None
        self._base_url = "https://api.bitbucket.org/2.0"
        self._environment_cache: Dict[str, Dict[str, Any]] = {}

    def transform(
        self,
        record: Dict[str, Any],
        config: Optional[Config] = None,
        stream_state: Optional[StreamState] = None,
        stream_slice: Optional[StreamSlice] = None,
    ) -> Dict[str, Any]:
        # Update auth if config is provided and different from instance config
        if config and config != self.config:
            if isinstance(config, dict):
                email = config.get("email")
                api_token = config.get("api_token")
            else:
                email = getattr(config, 'email', None)
                api_token = getattr(config, 'api_token', None)

            if email and api_token:
                self._auth = (email, api_token)

        # Get the environment UUID from the deployment record
        environment_info = record.get("environment", {})
        environment_uuid = environment_info.get("uuid")

        if not environment_uuid:
            return record

        # Get repository name from stream slice
        repository = None
        if stream_slice and hasattr(stream_slice, 'partition'):
            repository = stream_slice.partition.get("repository")
        elif stream_slice and isinstance(stream_slice, dict):
            repository = stream_slice.get("repository")
        print(f"Repository from stream slice: {repository}")
        if not repository:
            return record

        # Fetch environment details
        environment_details = self._get_environment_details(repository, environment_uuid)

        # Always merge - if environment_details is None/empty, we merge with {}
        record["environment"] = environment_details
        return record

    def _get_environment_details(self, repository: str, environment_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch environment details from Bitbucket API.
        Uses caching to avoid duplicate API calls for the same environment.
        Returns None if the request fails (which will be enriched as empty object).
        """
        cache_key = f"{repository}:{environment_uuid}"

        # Check cache first
        if cache_key in self._environment_cache:
            return self._environment_cache[cache_key]

        # Construct API URL
        url = f"{self._base_url}/repositories/{repository}/environments/{environment_uuid}"
        print(f"Fetching environment details from: {url}")
        try:
            # First attempt with clean UUID
            response = requests.get(url, auth=self._auth, timeout=30)

            if response.status_code == 200:
                environment_data = response.json()
                self._environment_cache[cache_key] = environment_data
                print(f"Environment details fetched successfully: {environment_data}")
                return environment_data

            else:
                # Cache the failure to avoid repeated calls
                self._environment_cache[cache_key] = None
                return None

        except requests.exceptions.RequestException:
            # Cache the failure to avoid repeated calls
            self._environment_cache[cache_key] = None
            return None
