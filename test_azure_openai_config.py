#!/usr/bin/env python3
"""
Test script to diagnose Azure OpenAI configuration issues.
This script helps identify common problems with Azure OpenAI setup.
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
            print("\n🔧 Troubleshooting Suggestions:")
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
        
        return False

def list_common_deployment_names():
    """List common Azure OpenAI deployment names to try."""
    print("\n📝 Common Azure OpenAI Deployment Names:")
    common_names = [
        "gpt-35-turbo",
        "gpt-35-turbo-16k", 
        "gpt-4",
        "gpt-4-32k",
        "gpt-4o",
        "gpt-4o-mini",
        "text-embedding-ada-002"
    ]
    
    for name in common_names:
        print(f"  - {name}")
    
    print("\n💡 Tip: Log into Azure OpenAI Studio to see your actual deployment names")
    print("   URL: https://oai.azure.com/")

if __name__ == "__main__":
    success = test_azure_openai_config()
    
    if not success:
        list_common_deployment_names()
        print("\n" + "=" * 50)
        print("❌ Azure OpenAI configuration test failed!")
        print("Please fix the issues above and run this test again.")
        sys.exit(1)
    else:
        print("\n" + "=" * 50) 
        print("✅ Azure OpenAI configuration test passed!")
        print("Your AI email improvement feature should work correctly.")
