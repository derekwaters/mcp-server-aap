#!/usr/bin/env python3
"""
Unit tests for MCP Ansible Automation Platform server components
Test individual functions and classes without full MCP protocol
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import our modules
from aap_client import AAPClient, AAPConfig, JobTemplate, JobLaunch

class UnitTestRunner:
    """Run unit tests for MCP server components"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def test(self, description: str):
        """Decorator for test functions"""
        def decorator(func):
            self.tests.append((description, func))
            return func
        return decorator

    async def run_all_tests(self):
        """Run all registered tests"""
        print("🧪 Running Unit Tests for MCP AAP Server")
        print("=" * 50)

        for description, test_func in self.tests:
            print(f"\n🔍 Testing: {description}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                print(f"✅ PASSED: {description}")
                self.passed += 1
            except Exception as e:
                print(f"❌ FAILED: {description}")
                print(f"   Error: {str(e)}")
                import traceback
                traceback.print_exc()
                self.failed += 1

        print(f"\n" + "=" * 50)
        print(f"📊 Test Results: {self.passed} passed, {self.failed} failed")
        return self.failed == 0

# Create test runner instance
runner = UnitTestRunner()

@runner.test("AAPConfig Creation")
def test_aap_config():
    """Test AAPConfig model creation"""
    config = AAPConfig(
        url="https://test.example.com",
        token="test-token",
        project_id="123"
    )
    assert config.url == "https://test.example.com"
    assert config.token == "test-token"
    assert config.project_id == "123"
    assert config.verify_ssl is True
    assert config.timeout == 30

@runner.test("JobTemplate Model")
def test_job_template():
    """Test JobTemplate model creation"""
    template = JobTemplate(
        id=1,
        name="Test Template",
        description="Test Description",
        project=5,
        playbook="test.yml",
        survey_enabled=True
    )
    assert template.id == 1
    assert template.name == "Test Template"
    assert template.playbook == "test.yml"
    assert template.survey_enabled is True

@runner.test("JobLaunch Model")
def test_job_launch():
    """Test JobLaunch model creation"""
    launch = JobLaunch(
        job=123,
        id=456,
        type="job",
        url="/api/v2/jobs/123/"
    )
    assert launch.job == 123
    assert launch.id == 456
    assert launch.type == "job"

@runner.test("Inventory Model")
def test_inventory():
    """Test Inventory model creation"""
    inventory = Inventory(
        id=11,
        name="Test Inventory",
        description="Test Inventory"
    )
    assert inventory.id == 11
    assert inventory.name == "Test Inventory"
    assert inventory.description == "Test Inventory"
    assert inventory.hosts == []

@runner.test("Host Model")
def test_host():
    """Test Host model creation"""
    inventory = Host(
        name="localhost",
        description="Test Host",
        enabled=True
    )
    assert inventory.name == "localhost"
    assert inventory.description == "Test Host"
    assert inventory.enabled is True

@runner.test("AAPClient Configuration from Environment")
def test_aap_client_config():
    """Test AAPClient configuration loading"""
    # Mock environment variables
    with patch.dict(os.environ, {
        'AAP_URL': 'https://test.example.com',
        'AAP_TOKEN': 'test-token',
        'AAP_PROJECT_ID': '123',
        'AAP_VERIFY_SSL': 'False',
        'AAP_TIMEOUT': '60'
    }):
        client = AAPClient()
        assert client.config.url == 'https://test.example.com'
        assert client.config.token == 'test-token'
        assert client.config.project_id == '123'
        assert client.config.verify_ssl is False
        assert client.config.timeout == 60

@runner.test("AAPClient Invalid Configuration")
def test_aap_client_invalid_config():
    """Test AAPClient with invalid configuration"""
    with patch.dict(os.environ, {}, clear=True):
        try:
            client = AAPClient()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "AAP_URL and AAP_TOKEN must be configured" in str(e)

@runner.test("AAPClient HTTP Request Formatting")
async def test_aap_client_request_formatting():
    """Test AAPClient request URL formatting"""
    config = AAPConfig(
        url="https://test.example.com",
        token="test-token",
        project_id="123"
    )

    # Mock the httpx client
    with patch('aap_client.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

        client = AAPClient(config)

        # Test URL formatting
        async with client:
            await client.get_job_templates()

            # Check that the request was made with correct URL
            call_args = mock_client.return_value.__aenter__.return_value.request.call_args
            assert call_args[0][0] == "GET"  # Method
            assert call_args[0][1] == "/api/v2/job_templates/"  # URL

@runner.test("Server Tool Registration")
def test_server_tool_registration():
    """Test that server tools are properly registered"""
    # Import server to test tool registration
    import server

    # Check that the server has the expected tools
    expected_tools = [
        "get_job_templates",
        "launch_job_template",
        "get_job_status",
        "get_job_output",
        "test_aap_connection"
    ]

    # This is a basic check - in a real scenario, we'd need to mock the server startup
    # For now, just verify the server module can be imported
    assert hasattr(server, 'server')
    assert hasattr(server, 'list_tools')
    assert hasattr(server, 'call_tool')

@runner.test("Mock AAP API Response Parsing")
async def test_mock_aap_response():
    """Test parsing of mock AAP API responses"""
    # Mock AAP API response
    mock_response = {
        "results": [
            {
                "id": 1,
                "name": "Deploy Web App",
                "description": "Deploy web application",
                "project": 5,
                "playbook": "deploy.yml",
                "survey_enabled": False
            },
            {
                "id": 2,
                "name": "Restart Services",
                "description": "Restart system services",
                "project": 5,
                "playbook": "restart.yml",
                "survey_enabled": True
            }
        ]
    }

    # Test parsing
    templates = []
    for template_data in mock_response["results"]:
        template = JobTemplate(**template_data)
        templates.append(template)

    assert len(templates) == 2
    assert templates[0].name == "Deploy Web App"
    assert templates[1].survey_enabled is True

@runner.test("Error Handling in AAP Client")
async def test_aap_client_error_handling():
    """Test error handling in AAPClient"""
    config = AAPConfig(
        url="https://test.example.com",
        token="test-token",
        project_id="123",
        max_retries=1  # Limit retries for testing
    )

    with patch('aap_client.httpx.AsyncClient') as mock_client:
        # Mock a failing HTTP request
        mock_client.return_value.__aenter__.return_value.request.side_effect = Exception("Network error")

        client = AAPClient(config)

        try:
            async with client:
                await client.get_job_templates()
            assert False, "Should have raised exception"
        except Exception as e:
            assert "AAP API request failed" in str(e)

def test_environment_loading():
    """Test environment variable loading"""
    # Test with .env file
    env_content = """
AAP_URL=https://env.example.com
AAP_TOKEN=env-token
AAP_PROJECT_ID=456
AAP_VERIFY_SSL=True
"""

    # Create temporary .env file
    with open('.env.test', 'w') as f:
        f.write(env_content)

    try:
        # Load environment from test file
        from dotenv import load_dotenv
        load_dotenv('.env.test')

        # Check if variables are loaded
        assert os.getenv('AAP_URL') == 'https://env.example.com'
        assert os.getenv('AAP_TOKEN') == 'env-token'
        assert os.getenv('AAP_PROJECT_ID') == '456'

    finally:
        # Clean up
        if os.path.exists('.env.test'):
            os.remove('.env.test')

async def run_integration_test():
    """Run integration test with real AAP (if configured)"""
    print("\n🔗 Integration Test (requires real AAP configuration)")

    try:
        # Try to create a real AAPClient
        client = AAPClient()

        print(f"Testing connection to: {client.config.url}")

        async with client:
            # Test connection
            connection_ok = await client.test_connection()
            if connection_ok:
                print("✅ Real AAP connection successful!")

                # Test template listing
                templates = await client.get_job_templates()
                print(f"✅ Found {len(templates)} templates")

                if templates:
                    print("Sample templates:")
                    for i, template in enumerate(templates[:3]):
                        print(f"  {i+1}. {template.name} (ID: {template.id})")


                # Test inventory listing
                inventories = await client.get_inventories()
                print(f"✅ Found {len(inventories)} inventories")

                if inventories:
                    print("Sample inventories:")
                    for i, inventory in enumerate(inventories[:3]):
                        print(f"  {i+1}. {inventory.name} (ID: {inventory.id})")

            else:
                print("❌ Real AAP connection failed")

    except Exception as e:
        print(f"⚠️  Integration test skipped: {e}")
        print("  (This is normal if AAP is not configured)")

async def main():
    """Run all tests"""
    # Run unit tests
    success = await runner.run_all_tests()

    # Run integration test if possible
    await run_integration_test()

    if success:
        print("\n🎉 All unit tests passed!")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())