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
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')  # Use env variable

# Configuration
UPLOAD_FOLDER = 'uploads'
TEMPLATES_FOLDER = 'templates_saved'
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# CUHK Email Server Configuration
SMTP_SERVER = 'mailserv.cuhk.edu.hk'
SMTP_PORT = 25

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-11-20-preview')
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

# Initialize Azure OpenAI client
azure_openai_client = None
if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    try:
        azure_openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        logger.info("Azure OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        azure_openai_client = None
else:
    logger.warning("Azure OpenAI credentials not found. AI features will be disabled.")


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


def send_email(smtp_server, smtp_port, sender_email, recipient_email, subject, body, sender_name=None, is_html=True):
    """Send individual email using SMTP."""
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
        
        # Connect to server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        return True, "Email sent successfully"
    except Exception as e:
        error_msg = f"Failed to send email to {recipient_email}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


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
    Utilizes structured output (Pydantic model) for reliable JSON parsing using .beta.chat.completions.parse().
    
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
        logger.error(f"Error calling Azure OpenAI API: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Failed to get AI suggestions: {str(e)}'
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
          # Store file info in session or pass to next page
        templates = list_templates()
        return render_template('compose.html', 
                             filename=filename, 
                             columns=result,
                             filepath=filepath,
                             templates=templates)
    else:
        flash('Invalid file type. Please upload a CSV file.')
        return redirect(url_for('index'))


@app.route('/send_emails', methods=['POST'])
def send_emails():
    """Send mass emails based on uploaded CSV and composed message."""
    try:
        # Get form data
        filepath = request.form.get('filepath')
        sender_email = request.form.get('sender_email')
        sender_name = request.form.get('sender_name', '')
        subject_template = request.form.get('subject')
        body_template = request.form.get('body')
        email_column = request.form.get('email_column')
        
        # Validate inputs
        if not all([filepath, sender_email, subject_template, body_template, email_column]):
            flash('All fields are required')
            return redirect(url_for('index'))
        
        # Read CSV data
        csv_data = read_csv_data(filepath)
        if not csv_data:
            flash('Error reading CSV data')
            return redirect(url_for('index'))
        
        # Initialize email logging
        campaign_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        email_log = []
        
        # Send emails
        success_count = 0
        failure_count = 0
        failures = []
        
        for row_index, row in enumerate(csv_data, 1):
            recipient_email = row.get(email_column)
            timestamp = datetime.now().isoformat()
            
            if not recipient_email:
                failure_count += 1
                error_msg = f"Row {row_index}: Missing email address"
                failures.append(error_msg)
                
                # Log the failure
                email_log.append({
                    'campaign_id': campaign_id,
                    'timestamp': timestamp,
                    'row_number': row_index,
                    'recipient_email': 'N/A',
                    'subject': 'N/A',
                    'status': 'FAILED',
                    'error_message': 'Missing email address',
                    'sender_email': sender_email,
                    'sender_name': sender_name
                })
                continue
            
            # Personalize subject and body
            personalized_subject = personalize_content(subject_template, row)
            personalized_body = personalize_content(body_template, row)
            
            # Send email
            success, message = send_email(
                SMTP_SERVER, SMTP_PORT, sender_email, recipient_email,
                personalized_subject, personalized_body, sender_name, is_html=True
            )
            
            # Log the email attempt
            log_entry = {
                'campaign_id': campaign_id,
                'timestamp': timestamp,
                'row_number': row_index,
                'recipient_email': recipient_email,
                'subject': personalized_subject,
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
                failures.append(f"Row {row_index}: {message}")
        
        # Store email log in session for download
        app.config['LAST_EMAIL_LOG'] = email_log
        app.config['LAST_CAMPAIGN_ID'] = campaign_id
        
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Show results
        return render_template('results.html',
                             success_count=success_count,
                             failure_count=failure_count,
                             failures=failures,
                             campaign_id=campaign_id)
        
    except Exception as e:
        logger.error(f"Error in send_emails: {str(e)}")
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('index'))


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
