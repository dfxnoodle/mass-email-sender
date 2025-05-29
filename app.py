"""
Mass Email Sender Web Application
A Flask web application for sending mass emails using CSV files as the source.
"""

import os
import csv
import smtplib
import html
import re
import json
import time
import threading
import queue
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import logging
import io
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel
from typing import List, Dict

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')  # Use env variable

# Configuration
UPLOAD_FOLDER = 'uploads'
TEMPLATES_FOLDER = 'templates_saved'
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# CUHK Email Server Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.googlemail.com')  # Default to Gmail SMTP
SMTP_PORT = os.getenv('SMTP_PORT', 587)  # Default SMTP port for TLS

# Rate limiting configuration for SMTP server
EMAIL_RATE_LIMIT_DELAY = os.getenv('EMAIL_RATE_LIMIT_DELAY', 2)  # seconds between emails
EMAIL_BATCH_SIZE = os.getenv('EMAIL_BATCH_SIZE', 10)  # number of emails before longer pause
EMAIL_BATCH_DELAY = os.getenv('EMAIL_BATCH_DELAY', 5)  # seconds to pause after each batch

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_FOLDER'] = TEMPLATES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload and templates directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global progress tracking storage
campaign_progress = {}
campaign_control = {}  # For pause/stop controls

# Initialize Azure OpenAI client
azure_openai_client = None
if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    try:
        azure_openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        logger.info(f"Azure OpenAI client initialized successfully with endpoint: {AZURE_OPENAI_ENDPOINT}")
        logger.info(f"Using deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
        logger.info(f"API Version: {AZURE_OPENAI_API_VERSION}")
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        azure_openai_client = None
else:
    logger.warning("Azure OpenAI credentials not found. AI features will be disabled.")


def test_azure_openai_connection():
    """Test Azure OpenAI connection and deployment availability."""
    if not azure_openai_client:
        return False, "Azure OpenAI client not initialized"
    
    try:
        # Test with a simple completion call
        completion = azure_openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.1
        )
        return True, "Connection successful"
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return False, f"Deployment '{AZURE_OPENAI_DEPLOYMENT_NAME}' not found. Please check your deployment name in Azure OpenAI Studio."
        elif "401" in error_msg:
            return False, "Authentication failed. Please check your API key."
        elif "403" in error_msg:
            return False, "Access forbidden. Please check your permissions."
        else:
            return False, f"Connection failed: {error_msg}"


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_csv(filepath):
    """Validate CSV file format and return column names."""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)
            
            # Check if email column exists
            email_columns = [col for col in headers if 'email' in col.lower()]
            if not email_columns:
                return False, "CSV must contain an 'email' column"
            
            return True, headers
    except Exception as e:
        return False, f"Error reading CSV file: {str(e)}"


def read_csv_data(filepath):
    """Read CSV data and return list of dictionaries."""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                data.append(row)
        return data
    except Exception as e:
        logger.error(f"Error reading CSV data: {str(e)}")
        return []


def send_email(smtp_server, smtp_port, sender_email, recipient_email, subject, body, sender_name=None, is_html=True, smtp_connection=None):
    """Send individual email using SMTP with optional connection reuse."""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Create HTML and plain text versions
        if is_html:
            # Convert HTML to plain text for fallback
            plain_text = re.sub('<[^<]+?>', '', body)  # Simple HTML tag removal
            plain_text = html.unescape(plain_text)  # Decode HTML entities
            
            # Create both parts
            text_part = MIMEText(plain_text, 'plain')
            html_part = MIMEText(body, 'html')
            
            # Add parts to message
            msg.attach(text_part)
            msg.attach(html_part)
        else:
            # Plain text only
            msg.attach(MIMEText(body, 'plain'))
        
        # Use provided connection or create new one
        if smtp_connection:
            server = smtp_connection
            server.sendmail(sender_email, recipient_email, msg.as_string())
        else:
            # Connect to server and send email (single email mode)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
        
        return True, "Email sent successfully"
    except Exception as e:
        error_msg = f"Failed to send email to {recipient_email}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def send_batch_emails_with_progress(smtp_server, smtp_port, sender_email, email_data_list, 
                                   sender_name=None, rate_limit_delay=2, batch_size=10, 
                                   batch_delay=10, campaign_id=None):
    """
    Send multiple emails with rate limiting, connection reuse, and progress tracking.
    
    Args:
        smtp_server: SMTP server address
        smtp_port: SMTP server port
        sender_email: Sender's email address
        email_data_list: List of dicts with 'recipient', 'subject', 'body' keys
        sender_name: Sender's display name
        rate_limit_delay: Seconds to wait between individual emails
        batch_size: Number of emails before taking a longer break
        batch_delay: Seconds to wait after each batch
        campaign_id: Campaign ID for progress tracking
    
    Returns:
        List of tuples: (success, message, recipient_email) for each email
    """
    results = []
    smtp_connection = None
    
    # Initialize progress tracking
    if campaign_id:
        campaign_progress[campaign_id] = {
            'progress': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_emails': len(email_data_list),
            'status': 'Initializing SMTP connection...',
            'activity': None,
            'activity_type': 'info',
            'current_email': '',
            'start_time': datetime.now()
        }
        
        campaign_control[campaign_id] = {
            'paused': False,
            'stopped': False
        }
    
    try:
        # Create persistent SMTP connection
        smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
        logger.info(f"Established SMTP connection to {smtp_server}:{smtp_port}")
        
        if campaign_id:
            campaign_progress[campaign_id]['status'] = 'SMTP connection established. Starting to send emails...'
            campaign_progress[campaign_id]['activity'] = f'Connected to {smtp_server}:{smtp_port}'
        
        total_emails = len(email_data_list)
        
        for index, email_data in enumerate(email_data_list, 1):
            # Check for pause/stop controls
            if campaign_id and campaign_id in campaign_control:
                # Handle pause
                while campaign_control[campaign_id].get('paused', False):
                    if campaign_id in campaign_progress:
                        campaign_progress[campaign_id]['status'] = 'Campaign paused by user'
                        campaign_progress[campaign_id]['activity'] = 'Campaign paused - waiting for resume'
                        campaign_progress[campaign_id]['activity_type'] = 'warning'
                    time.sleep(1)  # Check every second
                
                # Handle stop
                if campaign_control[campaign_id].get('stopped', False):
                    if campaign_id in campaign_progress:
                        campaign_progress[campaign_id]['status'] = 'Campaign stopped by user'
                        campaign_progress[campaign_id]['activity'] = 'Campaign stopped - remaining emails cancelled'
                        campaign_progress[campaign_id]['activity_type'] = 'warning'
                    logger.info(f"Campaign {campaign_id} stopped by user at email {index}/{total_emails}")
                    break
            
            recipient_email = email_data['recipient']
            subject = email_data['subject']
            body = email_data['body']
            
            # Update progress with current email
            if campaign_id:
                campaign_progress[campaign_id]['current_email'] = recipient_email
                campaign_progress[campaign_id]['status'] = f'Sending email {index}/{total_emails} to {recipient_email}'
            
            # Send email using persistent connection
            success, message = send_email(
                smtp_server, smtp_port, sender_email, recipient_email,
                subject, body, sender_name, is_html=True, smtp_connection=smtp_connection
            )
            
            results.append((success, message, recipient_email))
            
            # Update progress tracking
            if campaign_id:
                campaign_progress[campaign_id]['progress'] = index
                if success:
                    campaign_progress[campaign_id]['success_count'] += 1
                    campaign_progress[campaign_id]['activity'] = f'✓ Email sent successfully to {recipient_email}'
                    campaign_progress[campaign_id]['activity_type'] = 'success'
                else:
                    campaign_progress[campaign_id]['failure_count'] += 1
                    campaign_progress[campaign_id]['activity'] = f'✗ Failed to send to {recipient_email}: {message}'
                    campaign_progress[campaign_id]['activity_type'] = 'error'
            
            # Log progress
            if index % 10 == 0 or index == total_emails:
                logger.info(f"Campaign {campaign_id}: Sent {index}/{total_emails} emails")
            
            # Rate limiting: pause between emails
            if index < total_emails:  # Don't pause after the last email
                time.sleep(rate_limit_delay)
                logger.debug(f"Waiting {rate_limit_delay}s before next email")
            
            # Batch delay: longer pause after every batch_size emails
            if index % batch_size == 0 and index < total_emails:
                if campaign_id:
                    campaign_progress[campaign_id]['status'] = f'Completed batch of {batch_size} emails. Taking {batch_delay}s break...'
                    campaign_progress[campaign_id]['activity'] = f'Batch completed ({index}/{total_emails}). Taking {batch_delay}s break...'
                    campaign_progress[campaign_id]['activity_type'] = 'info'
                
                logger.info(f"Completed batch of {batch_size} emails. Taking {batch_delay}s break...")
                time.sleep(batch_delay)
        
    except Exception as e:
        logger.error(f"Error in batch email sending: {str(e)}")
        
        if campaign_id:
            campaign_progress[campaign_id]['status'] = f'SMTP connection error: {str(e)}'
            campaign_progress[campaign_id]['activity'] = f'Connection error: {str(e)}'
            campaign_progress[campaign_id]['activity_type'] = 'error'
        
        # If connection failed, mark remaining emails as failed
        remaining_emails = email_data_list[len(results):]
        for email_data in remaining_emails:
            results.append((False, f"SMTP connection error: {str(e)}", email_data['recipient']))
    
    finally:
        # Close SMTP connection
        if smtp_connection:
            try:
                smtp_connection.quit()
                logger.info("SMTP connection closed")
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {str(e)}")
        
        # Mark campaign as completed
        if campaign_id and campaign_id in campaign_progress:
            # Ensure progress shows 100% (total_emails) and send this update first
            campaign_progress[campaign_id]['progress'] = len(email_data_list)
            campaign_progress[campaign_id]['status'] = 'Campaign completed'
            campaign_progress[campaign_id]['activity'] = f'Campaign finished. Total: {len(results)} emails processed'
            campaign_progress[campaign_id]['activity_type'] = 'success'
            
            # Small delay to ensure the progress update is sent before marking as completed
            time.sleep(0.1)
    
    return results


def personalize_content(template, row_data):
    """Replace placeholders in template with actual data from CSV row."""
    content = template
    for key, value in row_data.items():
        placeholder = f"{{{key}}}"
        content = content.replace(placeholder, str(value))
    return content


def save_template(name, subject, body, sender_name=''):
    """Save an email template to the templates folder."""
    try:
        template_data = {
            'name': name,
            'subject': subject,
            'body': body,
            'sender_name': sender_name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Create safe filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        filename = f"{safe_name}.json"
        filepath = os.path.join(app.config['TEMPLATES_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        # Add filename to template data for frontend
        template_data['filename'] = filename
        
        return True, template_data
    except Exception as e:
        logger.error(f"Error saving template: {str(e)}")
        return False, f"Error saving template: {str(e)}"


def load_template(filename):
    """Load an email template from the templates folder."""
    try:
        filepath = os.path.join(app.config['TEMPLATES_FOLDER'], filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return True, template_data
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        return False, f"Error loading template: {str(e)}"


def list_templates():
    """List all saved email templates."""
    try:
        templates = []
        templates_dir = app.config['TEMPLATES_FOLDER']
        
        if not os.path.exists(templates_dir):
            return []
        
        for filename in os.listdir(templates_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(templates_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    template_data['filename'] = filename
                    templates.append(template_data)
                except Exception as e:
                    logger.warning(f"Error reading template {filename}: {str(e)}")
                    continue
        
        # Sort by updated_at (most recent first)
        templates.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return templates
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        return []


def delete_template(filename):
    """Delete an email template."""
    try:
        filepath = os.path.join(app.config['TEMPLATES_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True, "Template deleted successfully"
        else:
            return False, "Template not found"
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        return False, f"Error deleting template: {str(e)}"


# Pydantic models for structured AI response
class EmailImprovementResponse(BaseModel):
    improved_subject: str
    improved_body: str
    spam_suggestions: List[str]
    general_improvements: List[str]
    spam_score_assessment: str
    deliverability_tips: List[str]


def improve_email_with_ai(subject: str, body: str, context: str = "") -> dict:
    """
    Use Azure OpenAI to improve email content and provide spam-proofing suggestions.
    
    Args:
        subject: Email subject line
        body: Email body content
        context: Additional context about the email campaign
    
    Returns:
        dict: Contains improved_subject, improved_body, spam_suggestions, general_improvements,
              spam_score_assessment, and deliverability_tips.
    """
    if not azure_openai_client:
        return {
            'success': False,
            'error': 'AI service is not available. Please check Azure OpenAI configuration.'
        }
    
    # Test connection first
    connection_ok, connection_msg = test_azure_openai_connection()
    if not connection_ok:
        return {
            'success': False,
            'error': f'Azure OpenAI connection failed: {connection_msg}'
        }
    
    prompt = f"""
Analyze and improve the following email.
Preserve placeholders like {{name}}.
Focus on content quality, spam-proofing, and deliverability.
Be very concise in your suggestions.

Original Email:
Subject: {subject}
Body: {body}
Additional Context: {context if context else "General mass email campaign"}
"""

    try:
        logger.info(f"Making Azure OpenAI API call to deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
        
        # Use regular completions.create instead of beta.parse
        completion = azure_openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert email marketing consultant. Provide concise improvements for the email. Keep your response short and focused. Return a valid JSON object with these keys: improved_subject, improved_body, spam_suggestions (max 3 items), general_improvements (max 3 items), spam_score_assessment (one sentence), and deliverability_tips (max 2 items)."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.3 
        )

        # Parse the JSON response manually
        ai_response_content = completion.choices[0].message.content
        logger.info(f"Raw AI response content: {ai_response_content[:300]}...")

        try:
            # Parse the JSON string
            parsed_json = json.loads(ai_response_content)
            
            # Validate that the response contains all required fields
            required_fields = ["improved_subject", "improved_body", "spam_suggestions", 
                              "general_improvements", "spam_score_assessment", "deliverability_tips"]
            
            missing_fields = [field for field in required_fields if field not in parsed_json]
            
            if missing_fields:
                return {
                    'success': False,
                    'error': f"AI response missing required fields: {', '.join(missing_fields)}",
                    'raw_response': ai_response_content
                }
            
            # Add success flag and return
            parsed_json['success'] = True
            return parsed_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to parse AI response as JSON: {str(e)}",
                'raw_response': ai_response_content
            }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error calling Azure OpenAI API: {error_msg}", exc_info=True)
        
        # Provide more specific error messages
        if "404" in error_msg:
            detailed_error = f"Deployment '{AZURE_OPENAI_DEPLOYMENT_NAME}' not found in Azure OpenAI resource. Please verify the deployment name in Azure OpenAI Studio."
        elif "401" in error_msg:
            detailed_error = "Authentication failed. Please check your API key in the .env file."
        elif "403" in error_msg:
            detailed_error = "Access forbidden. Please check your Azure OpenAI resource permissions."
        elif "429" in error_msg:
            detailed_error = "Rate limit exceeded. Please try again later."
        else:
            detailed_error = f"API call failed: {error_msg}"
        
        return {
            'success': False,
            'error': detailed_error
        }


# Flask Routes
@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle CSV file upload."""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Validate CSV
        is_valid, result = validate_csv(filepath)
        if not is_valid:
            flash(f'Invalid CSV file: {result}')
            os.remove(filepath)  # Clean up invalid file
            return redirect(url_for('index'))
        
        # Get CSV data count for rate limiting estimation
        csv_data = read_csv_data(filepath)
        csv_count = len(csv_data) if csv_data else 0
        
        # Store file info in session or pass to next page
        templates = list_templates()
        return render_template('compose.html', 
                             filename=filename, 
                             columns=result,
                             filepath=filepath,
                             templates=templates,
                             csv_count=csv_count)
    else:
        flash('Invalid file type. Please upload a CSV file.')
        return redirect(url_for('index'))


@app.route('/send_emails', methods=['POST'])
def send_emails():
    """Send mass emails based on uploaded CSV and composed message with progress tracking."""
    try:
        # Get form data
        filepath = request.form.get('filepath')
        sender_email = request.form.get('sender_email')
        sender_name = request.form.get('sender_name', '')
        subject_template = request.form.get('subject')
        body_template = request.form.get('body')
        email_column = request.form.get('email_column')
        
        # Get rate limiting settings with defaults
        rate_limit_delay = int(request.form.get('rate_limit_delay', EMAIL_RATE_LIMIT_DELAY))
        batch_size = int(request.form.get('batch_size', EMAIL_BATCH_SIZE))
        batch_delay = int(request.form.get('batch_delay', EMAIL_BATCH_DELAY))
        
        # Validate inputs
        if not all([filepath, sender_email, subject_template, body_template, email_column]):
            flash('All fields are required')
            return redirect(url_for('index'))
        
        # Read CSV data
        csv_data = read_csv_data(filepath)
        if not csv_data:
            flash('Error reading CSV data')
            return redirect(url_for('index'))
        
        # Initialize campaign
        campaign_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        start_time = datetime.now()
        
        # Calculate estimated duration
        total_emails = len(csv_data)
        estimated_duration = calculate_estimated_duration(total_emails, rate_limit_delay, batch_size, batch_delay)
        
        # Prepare email data for batch sending
        email_data_list = []
        failures = []
        
        logger.info(f"Starting email campaign {campaign_id} with {len(csv_data)} recipients")
        
        for row_index, row in enumerate(csv_data, 1):
            recipient_email = row.get(email_column)
            
            if not recipient_email:
                error_msg = f"Row {row_index}: Missing email address"
                failures.append(error_msg)
                continue
            
            # Personalize subject and body
            personalized_subject = personalize_content(subject_template, row)
            personalized_body = personalize_content(body_template, row)
            
            # Add to batch email list
            email_data_list.append({
                'recipient': recipient_email,
                'subject': personalized_subject,
                'body': personalized_body,
                'row_index': row_index
            })
        
        # Show progress page immediately
        subject_preview = personalize_content(subject_template, csv_data[0] if csv_data else {})
        
        # Start email sending in background thread
        if email_data_list:
            def send_emails_background():
                try:
                    batch_results = send_batch_emails_with_progress(
                        SMTP_SERVER, SMTP_PORT, sender_email, email_data_list, 
                        sender_name, rate_limit_delay, batch_size, batch_delay, campaign_id
                    )
                    
                    # Brief pause to ensure final progress update is sent before completion
                    time.sleep(0.5)
                    
                    # Mark campaign as completed immediately after batch sending
                    if campaign_id in campaign_progress:
                        campaign_progress[campaign_id]['completed'] = True
                    
                    # Process results and create logs
                    email_log = []
                    success_count = 0
                    failure_count = len(failures)  # Pre-processing failures
                    
                    for i, (success, message, recipient_email) in enumerate(batch_results):
                        email_data = email_data_list[i]
                        row_index = email_data['row_index']
                        timestamp = datetime.now().isoformat()
                        
                        # Log the email attempt
                        log_entry = {
                            'campaign_id': campaign_id,
                            'timestamp': timestamp,
                            'row_number': row_index,
                            'recipient_email': recipient_email,
                            'subject': email_data['subject'],
                            'status': 'SUCCESS' if success else 'FAILED',
                            'error_message': '' if success else message,
                            'sender_email': sender_email,
                            'sender_name': sender_name
                        }
                        email_log.append(log_entry)
                        
                        if success:
                            success_count += 1
                        else:
                            failure_count += 1
                    
                    # Add pre-processing failures to log
                    for failure in failures:
                        email_log.append({
                            'campaign_id': campaign_id,
                            'timestamp': datetime.now().isoformat(),
                            'row_number': 'N/A',
                            'recipient_email': 'N/A',
                            'subject': 'N/A',
                            'status': 'FAILED',
                            'error_message': failure,
                            'sender_email': sender_email,
                            'sender_name': sender_name
                        })
                    
                    # Store results for later retrieval
                    end_time = datetime.now()
                    duration = end_time - start_time
                    
                    app.config[f'CAMPAIGN_RESULTS_{campaign_id}'] = {
                        'success_count': success_count,
                        'failure_count': failure_count,
                        'failures': [f"Row {email_data_list[i]['row_index']}: {message}" for i, (success, message, _) in enumerate(batch_results) if not success] + failures,
                        'campaign_id': campaign_id,
                        'duration': duration.total_seconds(),
                        'total_emails': success_count + failure_count,
                        'rate_limit_info': {
                            'delay': rate_limit_delay,
                            'batch_size': batch_size,
                            'batch_delay': batch_delay
                        }
                    }
                    
                    # Store email log
                    app.config['LAST_EMAIL_LOG'] = email_log
                    app.config['LAST_CAMPAIGN_ID'] = campaign_id
                    
                    # Clean up uploaded file
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    
                    # Store results for later retrieval and update progress tracking
                    if campaign_id in campaign_progress:
                        campaign_progress[campaign_id]['results'] = app.config[f'CAMPAIGN_RESULTS_{campaign_id}']
                    
                    logger.info(f"Campaign {campaign_id} completed: {success_count} successful, {failure_count} failed")
                    
                except Exception as e:
                    logger.error(f"Error in background email sending: {str(e)}")
                    if campaign_id in campaign_progress:
                        campaign_progress[campaign_id]['error'] = str(e)
                        campaign_progress[campaign_id]['completed'] = True
            
            # Start background thread
            thread = threading.Thread(target=send_emails_background)
            thread.daemon = True
            thread.start()
        
        # Return progress page immediately
        return render_template('progress.html',
                             campaign_id=campaign_id,
                             total_emails=len(email_data_list),
                             sender_email=sender_email,
                             subject_preview=subject_preview,
                             start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
                             rate_limit_delay=rate_limit_delay,
                             batch_size=batch_size,
                             batch_delay=batch_delay,
                             estimated_duration=estimated_duration)
        
    except Exception as e:
        logger.error(f"Error in send_emails: {str(e)}")
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('index'))


def calculate_estimated_duration(total_emails, rate_limit_delay, batch_size, batch_delay):
    """Calculate estimated campaign duration."""
    if total_emails == 0:
        return "0s"
    
    # Calculate time for individual emails
    individual_delay_time = (total_emails - 1) * rate_limit_delay
    
    # Calculate number of batches and batch delay time
    num_batches = total_emails // batch_size
    batch_delay_time = num_batches * batch_delay
    
    # Add base time for processing (estimate 1 second per email)
    processing_time = total_emails * 1
    
    total_seconds = individual_delay_time + batch_delay_time + processing_time
    
    if total_seconds < 60:
        return f"{int(total_seconds)}s"
    elif total_seconds < 3600:
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def prepare_data_for_json(data):
    """Convert datetime objects to strings for JSON serialization."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = prepare_data_for_json(value)
            elif isinstance(value, list):
                result[key] = [prepare_data_for_json(item) if isinstance(item, (dict, datetime)) else item for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data


@app.route('/progress_stream/<campaign_id>')
def progress_stream(campaign_id):
    """Server-Sent Events stream for progress updates."""
    def event_stream():
        last_update = {}
        
        while True:
            if campaign_id in campaign_progress:
                current_data = campaign_progress[campaign_id].copy()
                
                # Only send update if data has changed
                if current_data != last_update:
                    # Always send progress update first (even if completed)
                    if not current_data.get('completed'):
                        # Prepare data for JSON serialization (convert datetime objects)
                        json_safe_data = prepare_data_for_json(current_data)
                        yield f"data: {json.dumps(json_safe_data)}\n\n"
                    else:
                        # Send final progress update before completion event
                        json_safe_data = prepare_data_for_json(current_data)
                        yield f"data: {json.dumps(json_safe_data)}\n\n"
                        
                        # Then send completion event
                        if current_data.get('error'):
                            yield f"event: error\ndata: {json.dumps({'error': current_data['error'], 'campaign_id': campaign_id})}\n\n"
                        else:
                            results = current_data.get('results', {})
                            yield f"event: complete\ndata: {json.dumps({'campaign_id': campaign_id, 'success_count': results.get('success_count', 0), 'failure_count': results.get('failure_count', 0)})}\n\n"
                        break
                    
                    last_update = current_data.copy()
            
            time.sleep(1)  # Update every second
    
    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/results/<campaign_id>')
def campaign_results(campaign_id):
    """Show results for a specific campaign."""
    results_key = f'CAMPAIGN_RESULTS_{campaign_id}'
    
    if results_key not in app.config:
        flash('Campaign results not found or expired')
        return redirect(url_for('index'))
    
    results = app.config[results_key]
    
    return render_template('results.html', **results)


@app.route('/pause_campaign/<campaign_id>', methods=['POST'])
def pause_campaign(campaign_id):
    """Pause an ongoing email campaign."""
    try:
        if campaign_id in campaign_control:
            campaign_control[campaign_id]['paused'] = True
            return jsonify({'success': True, 'message': 'Campaign paused'})
        else:
            return jsonify({'success': False, 'error': 'Campaign not found'})
    except Exception as e:
        logger.error(f"Error pausing campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/resume_campaign/<campaign_id>', methods=['POST'])
def resume_campaign(campaign_id):
    """Resume a paused email campaign."""
    try:
        if campaign_id in campaign_control:
            campaign_control[campaign_id]['paused'] = False
            return jsonify({'success': True, 'message': 'Campaign resumed'})
        else:
            return jsonify({'success': False, 'error': 'Campaign not found'})
    except Exception as e:
        logger.error(f"Error resuming campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/stop_campaign/<campaign_id>', methods=['POST'])
def stop_campaign(campaign_id):
    """Stop an ongoing email campaign."""
    try:
        if campaign_id in campaign_control:
            campaign_control[campaign_id]['stopped'] = True
            return jsonify({'success': True, 'message': 'Campaign stopped'})
        else:
            return jsonify({'success': False, 'error': 'Campaign not found'})
    except Exception as e:
        logger.error(f"Error stopping campaign {campaign_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/preview', methods=['POST'])
def preview_email():
    """Preview personalized email for the first row of CSV."""
    try:
        filepath = request.form.get('filepath')
        subject_template = request.form.get('subject')
        body_template = request.form.get('body')
        
        # Read first row of CSV
        csv_data = read_csv_data(filepath)
        if csv_data:
            first_row = csv_data[0]
            preview_subject = personalize_content(subject_template, first_row)
            preview_body = personalize_content(body_template, first_row)
            
            return jsonify({
                'success': True,
                'subject': preview_subject,
                'body': preview_body,
                'sample_data': first_row
            })
        else:
            return jsonify({'success': False, 'error': 'No data in CSV file'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download_log/<campaign_id>')
def download_log(campaign_id):
    """Download email campaign log as CSV file."""
    try:
        # Get the email log from app config
        email_log = app.config.get('LAST_EMAIL_LOG', [])
        stored_campaign_id = app.config.get('LAST_CAMPAIGN_ID', '')
        
        if not email_log or campaign_id != stored_campaign_id:
            flash('Email log not found or expired')
            return redirect(url_for('index'))
        
        # Create CSV content
        output = io.StringIO()
        fieldnames = [
            'campaign_id', 'timestamp', 'row_number', 'recipient_email', 
            'subject', 'status', 'error_message', 'sender_email', 'sender_name'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(email_log)
        
        # Create response
        csv_content = output.getvalue()
        output.close()
        
        # Create file-like object for download
        csv_buffer = io.BytesIO()
        csv_buffer.write(csv_content.encode('utf-8'))
        csv_buffer.seek(0)
        
        filename = f'email_campaign_log_{campaign_id}.csv'
        
        return send_file(
            csv_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error downloading log: {str(e)}")
        flash(f'Error downloading log: {str(e)}')
        return redirect(url_for('index'))


@app.route('/save_template', methods=['POST'])
def save_template_route():
    """Save an email template."""
    try:
        name = request.form.get('template_name')
        subject = request.form.get('subject')
        body = request.form.get('body')
        sender_name = request.form.get('sender_name', '')
        
        if not all([name, subject, body]):
            return jsonify({'success': False, 'error': 'Template name, subject, and body are required'})
        
        success, result = save_template(name, subject, body, sender_name)
        if success:
            return jsonify({'success': True, 'message': 'Template saved successfully', 'template': result})
        else:
            return jsonify({'success': False, 'error': result})
        
    except Exception as e:
        logger.error(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/load_template/<filename>')
def load_template_route(filename):
    """Load an email template."""
    try:
        success, result = load_template(filename)
        if success:
            return jsonify({'success': True, 'template': result})
        else:
            return jsonify({'success': False, 'error': result})
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/delete_template/<filename>', methods=['POST'])
def delete_template_route(filename):
    """Delete an email template."""
    try:
        success, message = delete_template(filename)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/templates')
def templates_page():
    """Show templates management page."""
    templates = list_templates()
    return render_template('templates.html', templates=templates)


@app.route('/improve_email', methods=['POST'])
def improve_email_route():
    """Improve email content using AI and provide spam-proofing suggestions."""
    try:
        # Get form data
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()
        context = request.form.get('context', '').strip()
        
        logger.info(f"AI improvement request - Subject: {subject[:50]}..., Body length: {len(body)}")
        
        if not subject or not body:
            return jsonify({
                'success': False, 
                'error': 'Both subject and body are required for AI improvement'
            })
        
        # Check if AI service is available
        if not azure_openai_client:
            return jsonify({
                'success': False,
                'error': 'AI service is currently unavailable. Please check the Azure OpenAI configuration.'
            })
        
        # Call AI improvement function
        result = improve_email_with_ai(subject, body, context)
        
        logger.info(f"AI improvement result: success={result.get('success', False)}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in AI email improvement route: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'An error occurred while improving the email: {str(e)}'
        })


@app.route('/debug/azure_openai')
def debug_azure_openai():
    """Debug route to test Azure OpenAI configuration."""
    debug_info = {
        'client_initialized': azure_openai_client is not None,
        'api_key_set': bool(AZURE_OPENAI_API_KEY),
        'endpoint': AZURE_OPENAI_ENDPOINT,
        'api_version': AZURE_OPENAI_API_VERSION,
        'deployment_name': AZURE_OPENAI_DEPLOYMENT_NAME,
        'connection_test': None
    }
    
    if azure_openai_client:
        success, message = test_azure_openai_connection()
        debug_info['connection_test'] = {
            'success': success,
            'message': message
        }
    
    return jsonify(debug_info)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
