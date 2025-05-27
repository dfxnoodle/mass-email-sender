#!/usr/bin/env python3
"""
Test script for AI email improvement functionality
"""

import requests
import json

def test_ai_improvement():
    """Test the AI improvement endpoint"""
    
    # Test data
    test_data = {
        'subject': 'Test Email Subject',
        'body': '<p>Dear {name},</p><p>This is a test email with {placeholder}.</p><p>Best regards,<br>{sender_name}</p>',
        'context': 'Test email for development'
    }
    
    try:
        print("Testing AI improvement endpoint...")
        
        # Make request to the local Flask app
        response = requests.post(
            'http://127.0.0.1:5000/improve_email',
            data=test_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Response received successfully!")
            print(f"Success: {result.get('success', False)}")
            
            if result.get('success'):
                print("✅ AI improvement successful!")
                print(f"Improved subject: {result.get('improved_subject', 'N/A')}")
                print(f"Spam suggestions count: {len(result.get('spam_suggestions', []))}")
                print(f"General improvements count: {len(result.get('general_improvements', []))}")
                print(f"Spam assessment: {result.get('spam_score_assessment', 'N/A')}")
            else:
                print("❌ AI improvement failed!")
                print(f"Error: {result.get('error', 'Unknown error')}")
                if 'raw_response' in result:
                    print("Raw response available in result")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

if __name__ == "__main__":
    test_ai_improvement()
