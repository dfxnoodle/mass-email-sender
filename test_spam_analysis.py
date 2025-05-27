#!/usr/bin/env python3
"""
Test script for spam analysis functionality
"""

import requests
import json

def test_spam_analysis():
    """Test the spam analysis endpoint"""
    
    # Test data with potentially spammy content
    test_data = {
        'subject': 'FREE URGENT OFFER!!! LIMITED TIME!!!',
        'body': '<p>CLICK HERE NOW FOR FREE MONEY!!! URGENT!!! Act fast before this amazing offer expires!!!</p><p>You have WON $1000000!!!</p>',
        'context': 'Spam risk analysis for mass email campaign'
    }
    
    try:
        print("Testing spam analysis endpoint...")
        print(f"Test subject: {test_data['subject']}")
        print(f"Test body length: {len(test_data['body'])}")
        
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
                print("✅ Spam analysis successful!")
                print(f"Spam assessment: {result.get('spam_score_assessment', 'N/A')}")
                print(f"Spam suggestions: {result.get('spam_suggestions', [])}")
                print(f"Deliverability tips: {result.get('deliverability_tips', [])}")
            else:
                print("❌ Spam analysis failed!")
                print(f"Error: {result.get('error', 'Unknown error')}")
                if 'raw_response' in result:
                    print("Raw response available in result")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

if __name__ == "__main__":
    test_spam_analysis()
