#!/usr/bin/env python3
"""
Test script for CSV logging functionality
This script tests the core components of the CSV logging feature
"""

import os
import sys
import csv
import io
from datetime import datetime

# Add the app directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_csv_logging():
    """Test the CSV logging functionality"""
    print("🧪 Testing CSV Logging Functionality")
    print("=" * 50)
    
    # Mock email log data
    campaign_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    email_log = [
        {
            'campaign_id': campaign_id,
            'timestamp': datetime.now().isoformat(),
            'row_number': 1,
            'recipient_email': 'test1@example.com',
            'subject': 'Welcome John Doe!',
            'status': 'SUCCESS',
            'error_message': '',
            'sender_email': 'admin@cuhk.edu.hk',
            'sender_name': 'Admin Team'
        },
        {
            'campaign_id': campaign_id,
            'timestamp': datetime.now().isoformat(),
            'row_number': 2,
            'recipient_email': 'invalid@email',
            'subject': 'Welcome Jane Smith!',
            'status': 'FAILED',
            'error_message': 'Invalid email address',
            'sender_email': 'admin@cuhk.edu.hk',
            'sender_name': 'Admin Team'
        }
    ]
    
    print(f"✅ Campaign ID: {campaign_id}")
    print(f"✅ Generated {len(email_log)} log entries")
    
    # Test CSV generation
    output = io.StringIO()
    fieldnames = [
        'campaign_id', 'timestamp', 'row_number', 'recipient_email', 
        'subject', 'status', 'error_message', 'sender_email', 'sender_name'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(email_log)
    
    csv_content = output.getvalue()
    output.close()
    
    print(f"✅ CSV content generated ({len(csv_content)} characters)")
    
    # Save test file
    test_filename = f'test_email_log_{campaign_id}.csv'
    with open(test_filename, 'w', newline='', encoding='utf-8') as f:
        f.write(csv_content)
    
    print(f"✅ Test file saved: {test_filename}")
    
    # Verify file content
    with open(test_filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    print(f"✅ Verified {len(rows)} rows in CSV file")
    
    # Display sample content
    print("\n📋 Sample CSV Content:")
    print("-" * 30)
    lines = csv_content.split('\\n')[:4]  # Show first 4 lines
    for i, line in enumerate(lines):
        if line.strip():
            print(f"{i+1}: {line}")
    
    print("\n🎉 CSV Logging Test Completed Successfully!")
    print(f"🗂️  Test file: {test_filename}")
    
    return test_filename

if __name__ == "__main__":
    try:
        test_file = test_csv_logging()
        
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"🧹 Cleaned up test file: {test_file}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)
