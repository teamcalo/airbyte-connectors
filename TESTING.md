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
