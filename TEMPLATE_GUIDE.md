# Email Template Management Guide

## Overview
The Mass Email Sender now includes a comprehensive template management system that allows you to save, load, and reuse email templates for future campaigns.

## Features

### Save Templates
- Save current email composition (subject, body, sender name) as a reusable template
- Assign descriptive names to templates for easy identification
- Templates preserve HTML formatting and personalization placeholders

### Load Templates
- Quick access to saved templates from the compose page
- Load template content with one click
- Preview templates before loading

### Template Management
- Dedicated templates management page
- View all saved templates with previews
- Delete outdated or unwanted templates
- See creation and modification dates

## How to Use Templates

### Saving a Template
1. Compose your email with subject and body content
2. In the "Email Templates" section of the sidebar, enter a descriptive name
3. Click the "Save" button
4. Your template is now saved for future use

### Loading a Template
1. In the "Email Templates" section, browse your saved templates
2. Click the upload icon (📤) next to the template you want to use
3. The template content will be loaded into the current composition
4. Modify as needed for your current campaign

### Managing Templates
1. Click "Templates" in the navigation bar
2. View all your saved templates with previews
3. Use the eye icon (👁️) to preview template content
4. Use the trash icon (🗑️) to delete templates you no longer need

## Template Best Practices

### Naming Conventions
- Use descriptive names: "Welcome Email", "Event Invitation", "Follow-up Message"
- Include purpose or campaign type in the name
- Avoid generic names like "Template 1"

### Content Design
- Include placeholder variables like `{name}`, `{company}` for personalization
- Use HTML formatting for better visual appeal
- Keep content flexible for different audiences
- Test templates with sample data before mass sending

### Organization
- Regularly review and clean up old templates
- Update templates when contact information or branding changes
- Create separate templates for different email types (newsletters, promotions, announcements)

## Technical Details

### Storage
- Templates are stored as JSON files in the `templates_saved/` directory
- Each template includes metadata: name, subject, body, sender name, timestamps
- Files are automatically named based on template name (sanitized for filesystem compatibility)

### Data Structure
```json
{
  "name": "Welcome Email",
  "subject": "Welcome to {company}!",
  "body": "<h1>Hello {name}!</h1><p>Welcome to our community...</p>",
  "sender_name": "Support Team",
  "created_at": "2025-05-26T10:30:00",
  "updated_at": "2025-05-26T10:30:00"
}
```

### Security
- Template names are sanitized to prevent filesystem attacks
- Only authorized users can access template management functions
- Templates are stored locally and not shared between different sessions

## API Endpoints

- `POST /save_template` - Save a new template
- `GET /load_template/<filename>` - Load template content
- `POST /delete_template/<filename>` - Delete a template
- `GET /templates` - View templates management page

## Troubleshooting

### Template Not Saving
- Ensure template name, subject, and body are all filled in
- Check that template name doesn't contain special characters
- Verify sufficient disk space in the `templates_saved/` directory

### Template Not Loading
- Check that the template file still exists
- Verify template file is not corrupted
- Try refreshing the page and loading again

### Missing Templates
- Templates are stored locally in the `templates_saved/` folder
- If the folder is deleted, all templates will be lost
- Consider backing up important templates

## Future Enhancements
- Template categories and tagging
- Template sharing between users
- Template import/export functionality
- Template performance analytics
- Advanced template validation
