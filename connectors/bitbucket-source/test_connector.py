#!/usr/bin/env python3

"""
Test script for Bitbucket connector
"""

import json
import sys
from pathlib import Path

# Add the source directory to the path
sys.path.insert(0, str(Path(__file__).parent / "source_bitbucket"))

from source_bitbucket.source import SourceBitbucket

def test_spec():
    """Test the spec command"""
    print("Testing spec command...")
    source = SourceBitbucket()
    spec = source.spec(logger=None)
    print("✓ Spec command successful")
    print(f"Connector supports: {list(spec.connectionSpecification['properties'].keys())}")
    return spec

def test_check(config):
    """Test the check command"""
    print("Testing check command...")
    source = SourceBitbucket()
    try:
        check_result = source.check(logger=None, config=config)
        if check_result.status.name == "SUCCEEDED":
            print("✓ Check command successful")
            return True
        else:
            print(f"✗ Check command failed: {check_result.message}")
            return False
    except Exception as e:
        print(f"✗ Check command failed with exception: {e}")
        return False

def test_discover(config):
    """Test the discover command"""
    print("Testing discover command...")
    source = SourceBitbucket()
    try:
        catalog = source.discover(logger=None, config=config)
        streams = [stream.name for stream in catalog.streams]
        print(f"✓ Discover command successful. Found streams: {streams}")
        return catalog
    except Exception as e:
        print(f"✗ Discover command failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Testing Bitbucket Source Connector")
    print("=" * 50)
    
    # Test spec
    spec = test_spec()
    
    # Load config
    config_path = Path(__file__).parent / "secrets" / "config.json"
    if not config_path.exists():
        print("⚠️  No config file found. Using sample config for validation.")
        config = {
            "workspace": "test-workspace",
            "email": "test@example.com",
            "api_token": "test-token",
            "start_date": "2024-01-01T00:00:00Z"
        }
    else:
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)
    
    # Test check
    check_success = test_check(config)
    
    # Test discover  
    catalog = test_discover(config)
    
    print("\n" + "=" * 50)
    if check_success and catalog:
        print("🎉 All tests passed! Connector is working correctly.")
    else:
        print("❌ Some tests failed. Please check the configuration and credentials.")

if __name__ == "__main__":
    main()
