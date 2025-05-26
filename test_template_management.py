# Template Management Test Script

import requests
import json
import os

# Test the template management system
BASE_URL = "http://localhost:5000"

def test_template_management():
    """Test template saving, loading, and deletion."""
    
    print("🧪 Testing Template Management System")
    print("=" * 50)
    
    # Test data
    test_template = {
        'template_name': 'Test Welcome Email',
        'subject': 'Welcome to {company}, {name}!',
        'body': '<h1>Hello {name}!</h1><p>Welcome to <strong>{company}</strong>. We are excited to have you!</p>',
        'sender_name': 'Test Team'
    }
    
    try:
        # Test 1: Save template
        print("📝 Test 1: Saving template...")
        response = requests.post(f"{BASE_URL}/save_template", data=test_template)
        result = response.json()
        
        if result.get('success'):
            print("✅ Template saved successfully!")
        else:
            print(f"❌ Failed to save template: {result.get('error')}")
            return False
            
        # Test 2: List templates (check if our template appears)
        print("\n📋 Test 2: Checking if template appears in list...")
        templates_dir = "templates_saved"
        if os.path.exists(templates_dir):
            template_files = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
            print(f"Found {len(template_files)} template files:")
            for file in template_files:
                print(f"  - {file}")
            
            # Find our test template
            test_filename = None
            for file in template_files:
                filepath = os.path.join(templates_dir, file)
                with open(filepath, 'r') as f:
                    template_data = json.load(f)
                    if template_data.get('name') == test_template['template_name']:
                        test_filename = file
                        break
            
            if test_filename:
                print(f"✅ Test template found: {test_filename}")
            else:
                print("❌ Test template not found in saved templates")
                return False
        else:
            print("❌ Templates directory not found")
            return False
            
        # Test 3: Load template
        print(f"\n📥 Test 3: Loading template '{test_filename}'...")
        response = requests.get(f"{BASE_URL}/load_template/{test_filename}")
        result = response.json()
        
        if result.get('success'):
            loaded_template = result.get('template')
            print("✅ Template loaded successfully!")
            print(f"   Name: {loaded_template.get('name')}")
            print(f"   Subject: {loaded_template.get('subject')}")
            print(f"   Sender: {loaded_template.get('sender_name')}")
            
            # Verify content matches
            if (loaded_template.get('name') == test_template['template_name'] and
                loaded_template.get('subject') == test_template['subject'] and
                loaded_template.get('body') == test_template['body']):
                print("✅ Template content matches original!")
            else:
                print("❌ Template content doesn't match original")
                return False
        else:
            print(f"❌ Failed to load template: {result.get('error')}")
            return False
            
        # Test 4: Delete template
        print(f"\n🗑️ Test 4: Deleting template '{test_filename}'...")
        response = requests.post(f"{BASE_URL}/delete_template/{test_filename}")
        result = response.json()
        
        if result.get('success'):
            print("✅ Template deleted successfully!")
            
            # Verify deletion
            filepath = os.path.join(templates_dir, test_filename)
            if not os.path.exists(filepath):
                print("✅ Template file removed from disk!")
            else:
                print("❌ Template file still exists on disk")
                return False
        else:
            print(f"❌ Failed to delete template: {result.get('message')}")
            return False
            
        print("\n🎉 All template management tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask application. Make sure it's running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

def test_templates_page():
    """Test the templates management page."""
    print("\n🌐 Testing Templates Management Page")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/templates")
        if response.status_code == 200:
            print("✅ Templates page loads successfully!")
            return True
        else:
            print(f"❌ Templates page returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Templates page test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Template Management Tests")
    print("Please ensure the Flask app is running on localhost:5000\n")
    
    # Run tests
    test1_passed = test_template_management()
    test2_passed = test_templates_page()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Template Management: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Templates Page: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Template management system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
