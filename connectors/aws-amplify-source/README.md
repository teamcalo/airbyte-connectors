# AWS Amplify Source Connector

This is a declarative source connector for AWS Amplify that extracts data from AWS Amplify applications, branches, and deployment jobs using the AWS Amplify API.

## Features

- **3 Supported Streams**: apps, branches, jobs
- **AWS Authentication**: Supports IAM credentials and role assumption
- **Regional Support**: Configure for any AWS region
- **Configurable Limits**: Control API pagination and data volume
- **Airbyte CDK**: Built using the latest Airbyte CDK with declarative YAML configuration

## Supported Streams

| Stream | Primary Key | Description |
|--------|-------------|-------------|
| `apps` | `appId` | AWS Amplify applications in your account |
| `branches` | `branchName` | Branches for each Amplify application |
| `jobs` | `jobId` | Build and deployment jobs for each branch |

## Prerequisites

- Python 3.9+
- AWS Account with Amplify applications
- AWS IAM credentials or role with appropriate permissions

## Configuration

### Required Parameters

- **region** (string): AWS region where your Amplify apps are located (e.g., "us-east-1")
- **auth_type** (object): Authentication configuration

### Optional Parameters

- **limit** (integer): Maximum number of records to retrieve per stream (default: 100)

### Authentication Types

#### 1. IAM Credentials
```json
{
  "region": "us-east-1",
  "limit": 100,
  "auth_type": {
    "type": "auth_type_credentials",
    "access_key_id": "your-access-key-id",
    "secret_access_key": "your-secret-access-key"
  }
}
```

#### 2. IAM Role Assumption
```json
{
  "region": "us-east-1", 
  "limit": 100,
  "auth_type": {
    "type": "auth_type_role",
    "role_to_assume": "arn:aws:iam::123456789012:role/AmplifyReadRole"
  }
}
```

## Authentication Setup

### Option 1: IAM User Credentials

1. **Create IAM User**:
   - Go to AWS IAM Console
   - Create a new user for Airbyte sync
   - Generate access keys

2. **Attach Permissions**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "amplify:ListApps",
           "amplify:GetApp",
           "amplify:ListBranches",
           "amplify:GetBranch", 
           "amplify:ListJobs",
           "amplify:GetJob"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### Option 2: IAM Role (Recommended)

1. **Create IAM Role**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::YOUR-ACCOUNT:user/airbyte-user"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```

2. **Attach Amplify Permissions** to the role (same as above)

### Required AWS Permissions

| Stream | Required Permissions |
|--------|---------------------|
| apps | `amplify:ListApps`, `amplify:GetApp` |
| branches | `amplify:ListBranches`, `amplify:GetBranch` |
| jobs | `amplify:ListJobs`, `amplify:GetJob` |

## Local Development

### Installation

1. Clone this repository
2. Navigate to the connector directory:
   ```bash
   cd connectors/aws-amplify-source
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `secrets/config.json` file with your AWS credentials:

```json
{
  "region": "us-east-1",
  "limit": 100,
  "auth_type": {
    "type": "auth_type_credentials",
    "access_key_id": "your-access-key-id",
    "secret_access_key": "your-secret-access-key"
  }
}
```

## Testing

### 1. Quick Test Script

Create a simple test script to validate the connector:

```python
#!/usr/bin/env python3

import json
import sys
from pathlib import Path

# Add the source directory to the path
sys.path.insert(0, str(Path(__file__).parent / "source_aws_amplify"))

from source_aws_amplify.source import SourceAwsAmplify

def test_connector():
    """Test the AWS Amplify connector"""
    print("🚀 Testing AWS Amplify Source Connector")
    print("=" * 50)
    
    # Load config
    config_path = Path(__file__).parent / "secrets" / "config.json"
    if not config_path.exists():
        print("❌ No config file found at secrets/config.json")
        return False
        
    with open(config_path) as f:
        config = json.load(f)
    
    source = SourceAwsAmplify()
    
    # Test spec
    print("Testing spec command...")
    spec = source.spec(logger=None)
    print("✓ Spec command successful")
    
    # Test check
    print("Testing check command...")
    try:
        check_result = source.check(logger=None, config=config)
        if check_result.status.name == "SUCCEEDED":
            print("✓ Check command successful")
        else:
            print(f"✗ Check command failed: {check_result.message}")
            return False
    except Exception as e:
        print(f"✗ Check command failed: {e}")
        return False
    
    # Test discover
    print("Testing discover command...")
    try:
        catalog = source.discover(logger=None, config=config)
        streams = [stream.name for stream in catalog.streams]
        print(f"✓ Discover command successful. Found streams: {streams}")
    except Exception as e:
        print(f"✗ Discover command failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Connector is working correctly.")
    return True

if __name__ == "__main__":
    test_connector()
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
# Test only apps stream
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | grep '"stream": "apps"' | head -5
```

### 3. Validate AWS Authentication

Test your AWS credentials manually with AWS CLI:

```bash
# Test AWS credentials
aws amplify list-apps --region us-east-1

# Test specific app access
aws amplify get-app --app-id your-app-id --region us-east-1

# Test role assumption (if using roles)
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/AmplifyReadRole --role-session-name test-session
```

## Docker Usage

### Building the Docker Image

```bash
# Build the Docker image
docker build -t aws-amplify-source:latest .

# Or build with a specific tag
docker build -t your-registry/aws-amplify-source:v1.0.0 .
```

### Running with Docker

```bash
# Test the connector
docker run --rm aws-amplify-source:latest spec

# Check connection (mount config file)
docker run --rm -v $(pwd)/secrets:/secrets \
  aws-amplify-source:latest check --config /secrets/config.json

# Discover streams
docker run --rm -v $(pwd)/secrets:/secrets \
  aws-amplify-source:latest discover --config /secrets/config.json

# Read data
docker run --rm -v $(pwd)/secrets:/secrets -v $(pwd)/integration_tests:/integration_tests \
  aws-amplify-source:latest read --config /secrets/config.json --catalog /integration_tests/catalog.json
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /airbyte/integration_code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy connector files
COPY . ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set entrypoint
ENV AIRBYTE_ENTRYPOINT "python /airbyte/integration_code/main.py"
ENTRYPOINT ["python", "/airbyte/integration_code/main.py"]

# Labels for metadata
LABEL io.airbyte.name=airbyte/source-aws-amplify
LABEL io.airbyte.version=1.0.0
LABEL description="Airbyte Source for AWS Amplify"
```

## Troubleshooting

### Common Issues

#### 403 Access Denied
- Verify your AWS credentials are correct
- Check that IAM user/role has required Amplify permissions
- Ensure you're using the correct AWS region

#### 404 Not Found / Empty Results
- Verify you have Amplify applications in the specified region
- Check if applications exist: `aws amplify list-apps --region your-region`
- Some regions may not have Amplify applications

#### Authentication Errors
- Test AWS credentials with AWS CLI: `aws sts get-caller-identity`
- For role assumption, verify the trust policy allows your user to assume the role
- Check if temporary credentials have expired

#### Connection Timeout
- Check your network connectivity to AWS
- Verify AWS region is correct and available
- Ensure no firewall blocking AWS API access

### Required AWS Permissions

For read-only access to Amplify, attach this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "amplify:ListApps",
        "amplify:GetApp",
        "amplify:ListBranches", 
        "amplify:GetBranch",
        "amplify:ListJobs",
        "amplify:GetJob"
      ],
      "Resource": "*"
    }
  ]
}
```

### Debug Mode

For detailed logging, set the debug environment variable:

```bash
export AIRBYTE_LOG_LEVEL=DEBUG
python main.py check --config secrets/config.json
```

## AWS Rate Limits

AWS Amplify API has rate limits:
- Most APIs: 1000 requests per minute
- The connector implements pagination to minimize API calls
- Large numbers of applications may take longer to sync

## Data Schemas

Each stream returns structured data according to AWS Amplify's API schemas:

- **apps**: Application metadata, configuration, and settings
- **branches**: Branch configuration, build settings, and deployment info  
- **jobs**: Build and deployment job details, status, and logs

See the `schemas/` directory for detailed field definitions.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your AWS configuration and credentials
3. Test individual AWS Amplify API endpoints manually
4. Check Airbyte logs for detailed error messages

## License

This connector is built using the Airbyte CDK and follows Airbyte's licensing terms.