<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Mass Email Sender Project

This is a Python Flask web application for sending mass emails using CSV files as the source.

## Project Context

- **Framework**: Flask web application
- **Email Server**: CUHK mailserv.cuhk.edu.hk:25 (campus network required)
- **File Processing**: CSV file upload and parsing
- **Email Features**: Personalization with CSV data, SMTP sending

## Code Style Guidelines

- Follow PEP 8 for Python code
- Use descriptive variable and function names
- Include error handling and logging
- Add docstrings for functions and classes
- Use type hints where appropriate

## Security Considerations

- Validate and sanitize all user inputs
- Use secure filename handling for uploads
- Implement CSRF protection for forms
- Validate email addresses before sending
- Clean up uploaded files after processing

## Email Functionality

- SMTP server: mailserv.cuhk.edu.hk
- Port: 25 (no authentication required)
- Must be connected to campus network
- Support email personalization using CSV column data
- Handle email sending errors gracefully

## Flask Specific

- Use proper Flask patterns (blueprints if needed)
- Handle file uploads securely
- Use Flask flash messages for user feedback
- Implement proper error handling and logging
- Use templates with proper escaping
