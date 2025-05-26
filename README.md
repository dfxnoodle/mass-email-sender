# Mass Email Sender

A Python Flask web application for sending mass emails using CSV files as the source. Designed specifically for CUHK campus network with their SMTP server configuration.

## Features

- **CSV Upload**: Upload CSV files with email addresses and recipient data
- **HTML Email Editor**: Rich text editor with formatting options (bold, italic, colors, lists, etc.)
- **Email Personalization**: Use CSV column data to personalize emails
- **Template Management**: Save, load, and reuse email templates for future campaigns
- **Web Interface**: User-friendly web interface for composing and sending emails
- **Preview Functionality**: Preview personalized HTML emails before sending
- **Campaign Results**: Detailed results showing success/failure rates
- **CSV Logging**: Download detailed logs of all email sending attempts
- **CUHK Integration**: Pre-configured for CUHK mail server (mailserv.cuhk.edu.hk)
- **Multi-format Support**: Sends both HTML and plain text versions for compatibility
- **Animated UI**: Modern interface with email-themed animations

## Requirements

- Python 3.7+
- Flask 2.3.3+
- Access to CUHK campus network (for SMTP server)
- CSV files with email addresses

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. **Upload CSV File**: 
   - Must contain at least one column with 'email' in the name
   - First row should contain column headers
   - Example format:
     ```
     name,email,company
     John Doe,john@example.com,ABC Corp
     Jane Smith,jane@example.com,XYZ Ltd
     ```

2. **Compose Email**:
   - Enter sender email (must be valid CUHK email)
   - Select email column from CSV
   - Use the rich text editor to format your email with HTML
   - Click placeholder buttons or manually use `{column_name}` syntax for personalization
   - Bold, italic, colors, lists, and other formatting supported

3. **Send Emails**:
   - Preview emails before sending
   - Monitor campaign results
   - Review any failed emails
   - Download detailed CSV logs of all email attempts

4. **Template Management**:
   - Save email compositions as reusable templates
   - Load saved templates for quick campaign setup
   - Manage templates with preview and delete options
   - Access template management via navigation menu

5. **Campaign Logging**:
   - Each campaign generates a unique ID with timestamp
   - Download comprehensive CSV logs containing:
     - Campaign ID and timestamp
     - Row number from original CSV
     - Recipient email address
     - Personalized subject line
     - Success/failure status
     - Error messages for failed emails
     - Sender information
   - Use logs for compliance, tracking, and analysis

For detailed information about CSV logging features, see [CSV_LOGGING_GUIDE.md](CSV_LOGGING_GUIDE.md).
For template management instructions, see [TEMPLATE_GUIDE.md](TEMPLATE_GUIDE.md).

## Email Server Configuration

- **Server**: mailserv.cuhk.edu.hk
- **Port**: 25
- **Connection**: Must be on CUHK campus network
- **Authentication**: None required

## Personalization

Use curly braces to insert data from CSV columns. The rich text editor supports HTML formatting:

**Text formatting:**
```
Dear {name},

Thank you for your interest in {company}.

Best regards,
{sender_name}
```

**HTML formatting:**
- **Bold text** for emphasis
- *Italic text* for style
- Colored text and backgrounds
- Bulleted and numbered lists
- Headers and different font sizes
- Links and images

## File Structure

```
MassMail/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── README.md                # Main documentation
├── CSV_LOGGING_GUIDE.md     # Detailed CSV logging guide
├── sample_emails.csv        # Example CSV file
├── templates/               # HTML templates
│   ├── base.html           # Base template with animations
│   ├── index.html          # Upload page
│   ├── compose.html        # Compose email page
│   └── results.html        # Results page
├── uploads/                # Temporary CSV uploads
└── .github/
    └── copilot-instructions.md
```

## Security Notes

- Only CSV files are accepted for upload
- Files are cleaned up after processing
- Input validation and sanitization implemented
- CSRF protection recommended for production use

## Development

To run in development mode:

```bash
python app.py
```

The application will start on `http://localhost:5000` with debug mode enabled.

## License

This project is created for CUHK internal use.
