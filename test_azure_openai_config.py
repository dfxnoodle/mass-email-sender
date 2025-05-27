#!/usr/bin/env python3
"""
Test script to diagnose Azure OpenAI configuration issues.
This script helps identify common problems with Azure OpenAI setup, with special
focus on API version compatibility issues.

Usage:
  python test_azure_openai_config.py              # Full configuration test
  python test_azure_openai_config.py --test-api-versions  # Test API versions only
"""

import os
import sys
from dotenv import load_dotenv
from openai import AzureOpenAI
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_azure_openai_config():
    """Test Azure OpenAI configuration step by step."""
    
    print("🔍 Testing Azure OpenAI Configuration...")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-11-20-preview')
    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
    
    print("📋 Configuration Check:")
    print(f"  ✓ API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"  ✓ Endpoint: {endpoint if endpoint else '❌ Missing'}")
    print(f"  ✓ API Version: {api_version}")
    print(f"  ✓ Deployment Name: {deployment_name}")
    print()
    
    if not api_key or not endpoint:
        print("❌ Missing required environment variables!")
        print("Please check your .env file and ensure AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are set.")
        return False
    
    # Test client initialization
    print("🔧 Testing Client Initialization...")
    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        print("  ✅ Client initialized successfully")
    except Exception as e:
        print(f"  ❌ Client initialization failed: {str(e)}")
        return False
    
    # Test simple API call
    print("🚀 Testing API Call...")
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "user", "content": "Hello, please respond with 'Connection successful'"}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        if response.choices and response.choices[0].message:
            print("  ✅ API call successful!")
            print(f"  📝 Response: {response.choices[0].message.content}")
            return True
        else:
            print("  ❌ API call returned empty response")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ API call failed: {error_msg}")
          # Provide specific troubleshooting suggestions
        if "404" in error_msg:
            print("\n🔧 Troubleshooting Suggestions for 404 Error:")
            if "api-version" in error_msg.lower() or "not supported" in error_msg.lower():
                print(f"  - API version '{api_version}' may not be supported")
                print("  - Try using a different API version (see suggestions below)")
                test_api_versions()
            else:
                print(f"  - The deployment '{deployment_name}' was not found")
                print("  - Check your deployment name in Azure OpenAI Studio")
                print("  - Verify the deployment is deployed and not just created")
                print("  - Common deployment names: gpt-35-turbo, gpt-4, gpt-4o-mini")
        elif "401" in error_msg:
            print("\n🔧 Troubleshooting Suggestions:")
            print("  - API key authentication failed")
            print("  - Check if your API key is correct and not expired")
            print("  - Verify the API key has proper permissions")
        elif "403" in error_msg:
            print("\n🔧 Troubleshooting Suggestions:")
            print("  - Access forbidden - check permissions")
            print("  - Verify your Azure subscription is active")
            print("  - Check if the resource is properly configured")
        elif "api-version" in error_msg.lower():
            print("\n🔧 API Version Issue Detected:")
            print(f"  - Current API version '{api_version}' may be invalid")
            test_api_versions()
        else:
            print("\n🔧 General Troubleshooting:")
            print("  - Check network connectivity")
            print("  - Verify all configuration parameters")
            test_api_versions()
        
        return False

def list_common_deployment_names():
    """List common Azure OpenAI deployment names to try."""
    print("\n📝 Common Azure OpenAI Deployment Names:")
    
    print("🚀 Latest Models (2025):")
    latest_models = [
        "gpt-4.5-preview",    # version 2025-02-27
        "o3-mini",            # version 2025-01-31
        "gpt-4.1",            # version 2025-04-14
        "gpt-4.1-nano",       # version 2025-04-14
        "gpt-4.1-mini",       # version 2025-04-14
        "o4-mini",            # version 2025-04-16
        "o3"                  # version 2025-04-16
    ]
    
    print("📅 Established Models:")
    established_models = [
        "o1",                 # version 2024-12-17
        "gpt-4o",             # version 2024-11-20 or 2024-08-06
        "gpt-4o-mini",        # version 2024-07-18
        "gpt-35-turbo",
        "gpt-35-turbo-16k", 
        "gpt-4",
        "gpt-4-32k",
        "text-embedding-ada-002"
    ]
    
    for name in latest_models:
        print(f"  🆕 {name}")
    
    print()
    for name in established_models:
        print(f"  📋 {name}")
    
    print("\n💡 Tip: Log into Azure OpenAI Studio to see your actual deployment names")
    print("   URL: https://oai.azure.com/")
    print("💡 Latest models may require newer API versions (2025-xx-xx-preview)")
    print("💡 Use o3, o4-mini for reasoning tasks, gpt-4.5 for general improvements")

def quick_api_version_test(api_version_to_test):
    """Quickly test if an API version works by making a minimal API call."""
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
    
    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version_to_test,
            azure_endpoint=endpoint
        )
        
        # Try a very minimal API call
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            temperature=0
        )
        return True
    except Exception as e:
        return False

def test_api_versions():
    """Test different API versions to find a working one."""
    print("\n🔄 Testing Different API Versions:")
    
    # Latest API versions to try (from newest to oldest, including 2025 versions)
    api_versions_to_test = [
        "2025-04-01-preview",  # GPT-image-1, evaluations API, reasoning summary with o3 and o4-mini
        "2025-03-01-preview",  # Responses API & support for computer-use-preview model
        "2025-02-01-preview",  # Stored Completions (distillation) API
        "2025-01-01-preview",  # Predicted Outputs
        "2024-12-01-preview",  # Reasoning models, Stored completions/distillation
        "2024-11-20-preview", 
        "2024-10-21",
        "2024-08-01-preview",
        "2024-06-01",
        "2024-05-01-preview",  # Assistants V2
        "2024-04-01-preview",
        "2024-03-01-preview",  # Embeddings encoding_format and dimensions parameters
        "2024-02-01"
    ]
    
    api_key = os.getenv('AZURE_OPENAI_API_KEY')
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
    
    if not api_key or not endpoint:
        print("  ❌ Cannot test API versions without API key and endpoint")
        return
    
    print("📋 Recommended API Versions to try:")
    working_versions = []
    
    for i, version in enumerate(api_versions_to_test[:5], 1):
        print(f"  {i}. {version} ... ", end="", flush=True)
        if quick_api_version_test(version):
            print("✅ Works")
            working_versions.append(version)
        else:
            print("❌ Failed")
    
    if working_versions:
        print(f"\n✅ Found {len(working_versions)} working API version(s):")
        for version in working_versions:
            print(f"  - {version}")
        print(f"\n💡 Try updating your .env file with: AZURE_OPENAI_API_VERSION={working_versions[0]}")
    else:
        print("\n❌ No working API versions found in quick test")
        print("💡 This might indicate a deployment name or authentication issue")
        print(f"\n💡 Current version in use: {os.getenv('AZURE_OPENAI_API_VERSION', '2024-11-20-preview')}")
        print("💡 To change API version, update AZURE_OPENAI_API_VERSION in your .env file")
        print("💡 Preview versions have latest features but may be less stable")
        print("💡 Non-preview versions are more stable for production use")
        print("💡 2025-xx-xx-preview versions support newest models like o3, o4-mini, gpt-4.5")
        print("💡 Use 2025-04-01-preview for o3/o4-mini reasoning models")
        print("💡 Use 2025-02-01-preview for gpt-4.5-preview model")

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--test-api-versions":
        print("🔍 Testing API Versions Only...")
        print("=" * 50)
        test_api_versions()
        sys.exit(0)
    
    success = test_azure_openai_config()
    
    if not success:
        list_common_deployment_names()
        print("\n" + "=" * 50)
        print("❌ Azure OpenAI configuration test failed!")
        print("Please fix the issues above and run this test again.")
        print("\n💡 Common fixes:")
        print("  1. Check API version compatibility")
        print("  2. Verify deployment name exists and is deployed")
        print("  3. Confirm API key is valid and has permissions")
        print("  4. Ensure network connectivity to Azure")
        print("\n🔧 To test API versions specifically, run:")
        print("  python test_azure_openai_config.py --test-api-versions")
        sys.exit(1)
    else:
        print("\n" + "=" * 50) 
        print("✅ Azure OpenAI configuration test passed!")
        print("Your AI email improvement feature should work correctly.")
