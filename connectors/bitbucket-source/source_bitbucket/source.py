

from typing import Any, List, Mapping, Tuple

from airbyte_cdk import BasicHttpAuthenticator, SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream

from .streams import (
    RepositoriesStream,
    PullRequestsStream,
    CommitsStream,
    DeploymentsStream,
    WorkspaceUsersStream,
)


class SourceBitbucket(AbstractSource):
    """
    Bitbucket source connector for Airbyte.

    This connector extracts data from Bitbucket Cloud using the Bitbucket REST API v2.0.

    Supported streams:
    - repositories: All repositories in the workspace
    - pull_requests: Pull requests for each repository (incremental)
    - commits: Commits for each repository (incremental)
    - deployments: Deployments for each repository (incremental, with environment enrichment)
    - workspace_users: Members of the workspace
    """

    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        """
        Test the connection to Bitbucket by attempting to list repositories.

        Args:
            logger: Airbyte logger instance
            config: Configuration dictionary containing workspace, email, and api_token

        Returns:
            Tuple of (success: bool, error_message: Any)
        """
        try:
            # Validate required config fields
            required_fields = ["workspace", "email", "api_token"]
            for field in required_fields:
                if field not in config:
                    return False, f"Missing required field: {field}"

            workspace = config["workspace"]
            if not workspace or not workspace.strip():
                return False, "Workspace cannot be empty"

            email = config.get("email", "")
            api_token = config.get("api_token", "")
            # Create authenticator and test connection by listing repositories
            authenticator = BasicHttpAuthenticator(username=email, password=api_token, config=config, parameters={})

            # Create a temporary WorkspaceUsersStream to test the connection
            users_stream = WorkspaceUsersStream(
                config=config, authenticator=authenticator
            )

            # Try to read the first record
            for _ in users_stream.read_records(sync_mode=SyncMode.full_refresh):
                # Successfully read at least one record, connection is valid
                return True, None

            # No users found, but connection is still valid
            print("Connection successful, but no users found in the workspace")
            return True, None

        except ValueError as e:
            # Authentication error (missing email or api_token)
            print(f"Authentication error: {str(e)}")
            return False, str(e)

        except Exception as e:
            print(f"Failed to connect to Bitbucket: {str(e)}")
            return False, f"Connection failed: {str(e)}"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Define the streams supported by this connector.

        Args:
            config: Configuration dictionary

        Returns:
            List of stream instances
        """
        email = config.get("email", "")
        api_token = config.get("api_token", "")

        authenticator = BasicHttpAuthenticator(username=email, password=api_token, config=config, parameters={})

        # Create parent stream
        repositories_stream = RepositoriesStream(config=config, authenticator=authenticator)

        # Create substreams (depend on repositories)
        pull_requests_stream = PullRequestsStream(
            parent_stream=repositories_stream,
            config=config,
            authenticator=authenticator,
        )

        commits_stream = CommitsStream(
            parent_stream=repositories_stream,
            config=config,
            authenticator=authenticator,
        )

        deployments_stream = DeploymentsStream(
            parent_stream=repositories_stream,
            config=config,
            authenticator=authenticator,
        )

        # Independent stream
        workspace_users_stream = WorkspaceUsersStream(
            config=config,
            authenticator=authenticator,
        )

        return [
            repositories_stream,
            pull_requests_stream,
            commits_stream,
            deployments_stream,
            workspace_users_stream,
        ]
