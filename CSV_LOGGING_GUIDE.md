# CSV Logging Guide

## Overview
The Mass Email Sender now includes comprehensive CSV logging functionality that tracks every email sending attempt in your campaigns.

## Features

### Campaign Tracking
- **Unique Campaign ID**: Each email campaign gets a unique timestamp-based ID (format: `YYYYMMDD_HHMMSS`)
- **Detailed Logging**: Every email attempt is logged regardless of success or failure
- **Downloadable Reports**: CSV logs can be downloaded immediately after campaign completion

### Log Content
Each log entry contains:
- `campaign_id`: Unique identifier for the campaign
- `timestamp`: ISO format timestamp when email was attempted
- `row_number`: Row number from the original CSV file
- `recipient_email`: Email address of the recipient
- `subject`: Personalized subject line sent to recipient
- `status`: `SUCCESS` or `FAILED`
- `error_message`: Detailed error message if sending failed
- `sender_email`: Email address used as sender
- `sender_name`: Display name of sender

### How to Access Logs

1. **Complete an Email Campaign**: Upload CSV, compose email, and send
2. **View Results Page**: After sending, you'll see campaign results
3. **Download Log**: Click the "Download Email Log (CSV)" button
4. **File Name**: Downloaded file will be named `email_campaign_log_YYYYMMDD_HHMMSS.csv`

### Example Log Entry
```csv
campaign_id,timestamp,row_number,recipient_email,subject,status,error_message,sender_email,sender_name
20250526_111730,2025-05-26T11:17:30.123456,1,john.doe@example.com,"Welcome John Doe!",SUCCESS,,admin@cuhk.edu.hk,Admin Team
20250526_111730,2025-05-26T11:17:31.234567,2,invalid@email,Welcome to our service,FAILED,Invalid email address,admin@cuhk.edu.hk,Admin Team
```

### Use Cases

1. **Compliance**: Keep records of all email communications
2. **Analysis**: Track delivery rates and identify problematic email addresses
3. **Debugging**: Investigate failed email deliveries
4. **Reporting**: Generate reports on campaign performance
5. **Follow-up**: Identify recipients who didn't receive emails for manual follow-up

### Best Practices

1. **Download Immediately**: Log data is only available during the current session
2. **Archive Logs**: Save downloaded logs for future reference
3. **Review Failures**: Check error messages to improve future campaigns
4. **Privacy**: Handle logs securely as they contain personal email addresses
5. **Cleanup**: Regularly review and archive old campaign logs

### Technical Notes

- Logs are generated in memory during campaign execution
- Data is only available for download during the current browser session
- CSV format ensures compatibility with Excel, Google Sheets, and data analysis tools
- All timestamps are in ISO 8601 format for consistent parsing
