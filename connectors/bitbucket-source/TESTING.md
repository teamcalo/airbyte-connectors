# Testing the Bitbucket Connector

This guide provides step-by-step instructions for testing the Bitbucket source connector.

## Quick Start Testing

### 1. Basic Functionality Test

Run the comprehensive test script:

```bash
python test_connector.py
```

**Expected Output:**
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

### 2. Individual Command Testing

#### Test Configuration Validation
```bash
python main.py spec
```

#### Test Connection
```bash
python main.py check --config secrets/config.json
```

**Expected Success Response:**
```json
{"type": "LOG", "log": {"level": "INFO", "message": "Check succeeded"}}
{"type": "CONNECTION_STATUS", "connectionStatus": {"status": "SUCCEEDED"}}
```

#### Test Stream Discovery
```bash
python main.py discover --config secrets/config.json
```

#### Test Data Reading
```bash
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json
```

## Stream-Specific Testing

### Test Repositories Stream
```bash
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | grep '"stream": "repositories"' | head -3
```

### Count Records per Stream
```bash
# Count repositories
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | grep '"stream": "repositories"' | wc -l

# Count pull requests  
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | grep '"stream": "pull_requests"' | wc -l
```

## API Authentication Testing

### Manual API Testing

Test your credentials directly with curl:

```bash
# Test user endpoint
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/user"

# Test workspace repositories
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/repositories/your-workspace-slug"

# Test workspace users
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/workspaces/your-workspace-slug/members"
```

### Test API Token Scopes

```bash
# Test repositories access (requires: Repositories: Read)
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/repositories/your-workspace-slug" \
  | head -20

# Test pull requests access (requires: Repositories: Read, Pull requests: Read)
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/repositories/your-workspace-slug/REPO-NAME/pullrequests" \
  | head -20

# Test account access (requires: Account: Read)
curl --user "your-email@example.com:your-api-token" \
  "https://api.bitbucket.org/2.0/workspaces/your-workspace-slug/members" \
  | head -20
```

## Incremental Sync Testing

### Test Initial Full Sync
```bash
# Run initial sync and save state
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json > initial_sync.jsonl 2>sync.log

# Check state information
grep "STATE" initial_sync.jsonl
```

### Test Incremental Sync
```bash
# Run incremental sync with previous state
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json --state integration_tests/sample_state.json
```

## Debugging

### Enable Debug Logging
```bash
export AIRBYTE_LOG_LEVEL=DEBUG
python main.py check --config secrets/config.json
```

### Common Issues and Solutions

#### 401 Unauthorized
```bash
# Check if email and token work
curl --user "your-email:your-token" "https://api.bitbucket.org/2.0/user"

# Expected: User information
# If error: Check email format and token validity
```

#### 403 Forbidden
```bash
# Test specific endpoint access
curl --user "your-email:your-token" "https://api.bitbucket.org/2.0/repositories/workspace"

# If 403: Check API token scopes
```

#### Empty Results
```bash
# Check if workspace has repositories
curl --user "your-email:your-token" "https://api.bitbucket.org/2.0/repositories/workspace" | jq '.size'

# Check workspace members
curl --user "your-email:your-token" "https://api.bitbucket.org/2.0/workspaces/workspace/members" | jq '.size'
```

## Performance Testing

### Large Workspace Testing
```bash
# Test with pagination
python main.py read --config secrets/config.json --catalog integration_tests/catalog.json 2>/dev/null | head -100

# Check API rate limiting
time python main.py read --config secrets/config.json --catalog integration_tests/catalog.json >/dev/null
```

### Memory Usage Monitoring
```bash
# Monitor memory during sync
/usr/bin/time -v python main.py read --config secrets/config.json --catalog integration_tests/catalog.json >/dev/null
```

## Integration Testing with Airbyte

### Test Configuration in Airbyte UI

1. Use the configuration:
```json
{
  "workspace": "your-workspace-slug",
  "email": "your-email@example.com",
  "api_token": "your-api-token",
  "start_date": "2024-01-01T00:00:00Z",
  "pull_request_state": "ALL"
}
```

2. Test connection in Airbyte UI
3. Run discovery to see available streams
4. Configure sync and test data flow

## Validation Checklist

- [ ] `python test_connector.py` passes all tests
- [ ] All 5 streams are discovered
- [ ] Connection check succeeds
- [ ] Data can be read from repositories stream
- [ ] Incremental sync works with state management
- [ ] API authentication works with curl
- [ ] Required scopes are configured on API token
- [ ] No authentication errors in logs

## Test Data Expectations

Based on your workspace, you should expect:

- **repositories**: 10+ repositories (based on previous test)
- **pull_requests**: Varies by repository activity
- **commits**: Varies by repository activity  
- **deployments**: May be empty if Pipelines not used
- **workspace_users**: Number of workspace members

## Next Steps

After successful testing:

1. Use the connector in Airbyte Cloud or Self-hosted
2. Configure incremental sync schedules
3. Set up data destinations
4. Monitor sync performance and logs
