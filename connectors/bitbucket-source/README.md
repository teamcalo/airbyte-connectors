# Bitbucket Source Connector

This is a declarative source connector for Bitbucket Cloud that extracts data from Bitbucket repositories, pull requests, commits, deployments, and workspace users using the Bitbucket API v2.0.

## Features

- **5 Supported Streams**: repositories, pull_requests, commits, deployments, workspace_users
- **Incremental Sync**: Supports incremental synchronization for repositories, pull_requests, commits, and deployments
- **API Token Authentication**: Uses Bitbucket API tokens with email-based authentication
- **Configurable**: Flexible start date and pull request state filtering
- **Airbyte CDK**: Built using the latest Airbyte CDK with declarative YAML configuration

## Supported Streams

| Stream | Incremental Support | Primary Key | Cursor Field | Description |
|--------|-------------------|-------------|--------------|-------------|
| `repositories` | ✅ Yes | `uuid` | `updated_on` | All repositories in the workspace |
| `pull_requests` | ✅ Yes | `id` | `updated_on` | Pull requests from all repositories |
| `commits` | ✅ Yes | `hash` | `date` | Commits from all repositories |
| `deployments` | ✅ Yes | `uuid` | `completed_on` | Deployments from all repositories |
| `workspace_users` | ❌ No | `uuid` | N/A | Users in the workspace |

## Prerequisites

- Python 3.9+
- Bitbucket Cloud account
- API token with appropriate scopes

## Configuration

### Required Parameters

- **workspace** (string): Your Bitbucket workspace slug (from the URL)
- **email** (string): Your Atlassian account email used for Bitbucket login
- **api_token** (string, secret): Bitbucket API token

### Optional Parameters

- **start_date** (string, ISO 8601): Start date for incremental syncs (default: "2020-01-01T00:00:00Z")
- **pull_request_state** (string): Filter pull requests by state (OPEN, MERGED, DECLINED, SUPERSEDED, ALL - default: ALL)

### Example Configuration

```json
{
  "workspace": "your-workspace-slug",
  "email": "your-email@example.com",
  "api_token": "your-api-token-here",
  "start_date": "2024-01-01T00:00:00Z",
  "pull_request_state": "ALL"
}
```

## Authentication Setup

### 1. Create a Bitbucket API Token

1. Go to [Bitbucket Personal Settings - API tokens](https://bitbucket.org/account/settings/api-tokens)
2. Click "Create token"
3. Give it a descriptive name (e.g., "Airbyte Sync")
4. Select the required scopes:
   - ✅ **Repositories: Read** (for repositories, commits streams)
   - ✅ **Pull requests: Read** (for pull_requests stream)
   - ✅ **Account: Read** (for workspace_users stream)
   - ✅ **Pipelines: Read** (optional, for deployments stream)
5. Click "Create"
6. Copy the generated token (it won't be shown again)

### 2. Find Your Atlassian Email

Your Atlassian account email is listed under "Email aliases" on your [Bitbucket Personal Settings](https://bitbucket.org/account/settings/email/) page.

### 3. Find Your Workspace Slug

Your workspace slug is the part after `bitbucket.org/` in your workspace URL. For example, if your workspace URL is `https://bitbucket.org/mycompany/`, then your workspace slug is `mycompany`.

## Local Development

### Installation

1. Clone this repository
2. Navigate to the connector directory:
   ```bash
   cd connectors/bitbucket-source
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `secrets/config.json` file with your credentials:

```json
{
  "workspace": "your-workspace-slug",
  "email": "your-email@example.com", 
  "api_token": "your-api-token",
  "start_date": "2024-01-01T00:00:00Z",
  "pull_request_state": "ALL"
}
```

## Testing

### 1. Quick Test Script

Run the included test script to validate all connector functions:

```bash
python test_connector.py
```

This will test:
- ✅ Spec command (configuration validation)
- ✅ Check command (connection test)
- ✅ Discover command (stream discovery)

Expected output:
```
🚀 Testing Bitbucket Source Connector
==================================================
Testing spec command...
✓ Spec command successful
Connector supports: ['workspace', 'email', 'api_token', 'start_date', 'pull_request_state']
Testing check command...
✓ Check command successful
Testing discover command...
✓ Discover command successful. Found streams: ['repositories', 'pull_requests', 'commits', 'deployments', 'workspace_users']

==================================================
🎉 All tests passed! Connector is working correctly.
```

### 2. Manual Testing Commands

#### Test Connection
```bash
python main.py check --config secrets/config.json
```

#### Discover Streams
```bash
python main.py discover --config secrets/config.json
```

#### Test Data Reading
```bash
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json
```

#### Test Specific Stream
```bash
# Test only repositories stream
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | grep '"stream": "repositories"' | head -5
```

### 3. Validate Authentication

Test your API token manually with curl:

```bash
# Test basic authentication
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/user"

# Test workspace access  
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/repositories/your-workspace-slug"
```

## Troubleshooting

### Common Issues

#### 401 Unauthorized
- Verify your email is the correct Atlassian account email
- Check that your API token is valid and not expired
- Ensure API token has the required scopes

#### 403 Forbidden
- Check that your API token has the required scopes for the streams you want to sync
- Verify you have access to the workspace

#### Empty Streams
- **deployments**: Normal if repositories don't use Bitbucket Pipelines
- **commits**: Check if repositories have any commits
- **pull_requests**: Verify repositories have pull requests

#### Connection Timeout
- Check your internet connection
- Verify Bitbucket API is accessible from your network

### Required Scopes by Stream

| Stream | Required API Token Scopes |
|--------|---------------------------|
| repositories | `Repositories: Read` |
| pull_requests | `Repositories: Read`, `Pull requests: Read` |
| commits | `Repositories: Read` |
| deployments | `Repositories: Read`, `Pipelines: Read` |
| workspace_users | `Account: Read` |

### Debug Mode

For detailed logging, set the debug environment variable:

```bash
export AIRBYTE_LOG_LEVEL=DEBUG
python main.py check --config secrets/config.json
```

## Incremental Sync

The connector supports incremental synchronization for most streams:

- **repositories**: Syncs repositories updated since the last run
- **pull_requests**: Syncs pull requests updated since the last run  
- **commits**: Syncs commits created since the last run
- **deployments**: Syncs deployments updated since the last run
- **workspace_users**: Full refresh only (no incremental support)

### State Management

The connector automatically manages state for incremental streams. You can check the current state in the sync logs or state files.

## API Rate Limits

Bitbucket API has rate limits:
- 1000 requests per hour for authenticated requests
- The connector implements pagination to minimize API calls
- Large workspaces may take longer to sync initially

## Docker Usage

### Building the Docker Image

```bash
# Build the Docker image
docker build -t bitbucket-source:latest .

# Or build with a specific tag
docker build -t your-registry/bitbucket-source:v1.0.0 .
```

### Running with Docker

```bash
# Test the connector
docker run --rm bitbucket-source:latest spec

# Check connection (mount config file)
docker run --rm -v $(pwd)/secrets:/secrets \
  bitbucket-source:latest check --config /secrets/config.json

# Discover streams
docker run --rm -v $(pwd)/secrets:/secrets \
  bitbucket-source:latest discover --config /secrets/config.json

# Read data
docker run --rm -v $(pwd)/secrets:/secrets -v $(pwd)/integration_tests:/integration_tests \
  bitbucket-source:latest read --config /secrets/config.json --catalog /integration_tests/catalog.json
```

## Data Schemas

Each stream returns structured data according to Bitbucket's API v2.0 schemas. See the `schemas/` directory for detailed field definitions.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your configuration and credentials
3. Test individual API endpoints manually
4. Check Airbyte logs for detailed error messages

## License

This connector is built using the Airbyte CDK and follows Airbyte's licensing terms.
