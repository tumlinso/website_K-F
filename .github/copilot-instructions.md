# Copilot Instructions for Gym Website

## Project Overview
A Django-based gym website project built with Python, HTML, and CSS. Minimal JavaScript required.

## Tech Stack
- Backend: Django 4.2.0
- Frontend: HTML, CSS (minimal JavaScript)
- Database: SQLite (development), can be upgraded to PostgreSQL
- Python 3.8+

## Key Files
- `config/settings.py` - Django configuration
- `config/urls.py` - URL routing
- `gym_app/models.py` - Database models (Membership, Class, Contact)
- `gym_app/views.py` - View logic
- `gym_app/templates/` - HTML templates
- `gym_app/static/css/style.css` - Styling
- `manage.py` - Django CLI

## Common Tasks

### Add a New Page
1. Create a view in `gym_app/views.py`
2. Create a template in `gym_app/templates/gym_app/`
3. Add URL route in `gym_app/urls.py`

### Modify Database
1. Update models in `gym_app/models.py`
2. Run: `python manage.py makemigrations`
3. Run: `python manage.py migrate`

### Add New Features
- Use Django forms for input validation
- Keep business logic in views.py
- Use templates for HTML generation

## Setup Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start dev server
python manage.py runserver
```

## Development Guidelines
- Use Python for backend logic whenever possible (user prefers Python over JavaScript)
- Keep JavaScript minimal and simple
- Use Django ORM instead of raw SQL
- Follow Django app structure and conventions
