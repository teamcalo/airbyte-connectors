

from typing import Any, List, Mapping, Tuple

from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream

from .auth import get_authenticator
from .streams import AppsStream, BranchesStream, JobsStream


class SourceAwsAmplify(AbstractSource):
    """
    AWS Amplify source connector for Airbyte.

    This connector extracts data from AWS Amplify applications, branches, and deployment jobs
    using the AWS Amplify API with AWS SigV4 authentication.

    Supported streams:
    - apps: AWS Amplify applications
    - branches: Branches for each application
    - jobs: Build and deployment jobs for each branch
    """

    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        """
        Test the connection to AWS Amplify by attempting to list apps.

        Args:
            logger: Airbyte logger instance (not used, we use print instead)
            config: Configuration dictionary containing region and auth credentials

        Returns:
            Tuple of (success: bool, error_message: Any)
        """
        try:
            # Validate required config fields
            if "region" not in config:
                return False, "Missing required field: region"

            if "auth_type" not in config:
                return False, "Missing required field: auth_type"

            auth_config = config.get("auth_type", {})
            auth_type = auth_config.get("type")

            if not auth_type:
                return False, "Missing auth_type.type field"

            if auth_type == "auth_type_credentials":
                if not auth_config.get("access_key_id") or not auth_config.get("secret_access_key"):
                    return False, "Missing access_key_id or secret_access_key for credentials auth"
            elif auth_type == "auth_type_role":
                if not auth_config.get("assume_role"):
                    return False, "Missing assume_role for role auth"
            else:
                return False, f"Unknown auth_type: {auth_type}"

            # Create authenticator and test connection by listing apps
            region = config.get("region", "us-east-1")
            authenticator = get_authenticator(config)

            # Create a temporary AppsStream to test the connection
            apps_stream = AppsStream(region=region, authenticator=authenticator)

            # Try to read the first record
            try:
                records = list(apps_stream.read_records(sync_mode="full_refresh"))
                # Successfully read records, connection is valid
                if records:
                    return True, None
                else:
                    # No apps found, but connection is still valid
                    print("Connection successful, but no apps found in the specified region")
                    return True, None
            except (ConnectionError, TimeoutError, ValueError) as conn_error:
                print(f"Connection error: {str(conn_error)}")
                return False, str(conn_error)

        except (ValueError, KeyError, TypeError) as e:
            print(f"Failed to connect to AWS Amplify: {str(e)}")
            return False, str(e)

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Define the streams supported by this connector.

        Args:
            config: Configuration dictionary containing region and auth credentials

        Returns:
            List of stream instances
        """
        region = config.get("region", "us-east-1")
        authenticator = get_authenticator(config)

        # Create parent stream
        apps_stream = AppsStream(region=region, authenticator=authenticator)

        # Create substream for branches (depends on apps)
        branches_stream = BranchesStream(
            parent_stream=apps_stream, region=region, authenticator=authenticator
        )

        # Create substream for jobs (depends on both apps and branches)
        jobs_stream = JobsStream(
            parent_streams={"apps": apps_stream, "branches": branches_stream},
            region=region,
            authenticator=authenticator,
        )

        return [apps_stream, branches_stream, jobs_stream]
