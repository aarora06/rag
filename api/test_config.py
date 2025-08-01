"""
Test configuration for filter functionality tests.
This file provides test-specific configuration and utilities.
"""

import os
from unittest.mock import patch

# Test API key
TEST_API_KEY = "test-api-key-for-unit-tests"

# Mock configuration for testing
TEST_CONFIG = {
    'API_KEY': TEST_API_KEY,
    'openai_api_key': 'test-openai-key',
    'MODEL': 'gpt-3.5-turbo',
    'db_name': 'test_db',
    'knowledge_base_path': '/tmp/test_knowledge_base'
}

def mock_config_for_tests():
    """Mock configuration for testing purposes."""
    return patch.multiple(
        'config',
        API_KEY=TEST_API_KEY,
        openai_api_key='test-openai-key',
        MODEL='gpt-3.5-turbo',
        db_name='test_db',
        knowledge_base_path='/tmp/test_knowledge_base'
    )

def setup_test_environment():
    """Set up test environment variables."""
    os.environ['API_KEY'] = TEST_API_KEY
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['MODEL'] = 'gpt-3.5-turbo'

def cleanup_test_environment():
    """Clean up test environment variables."""
    for key in ['API_KEY', 'OPENAI_API_KEY', 'MODEL']:
        if key in os.environ:
            del os.environ[key] 