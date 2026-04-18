# K+F Fitnessstudio - Django Website

A modern, responsive gym website built with Django. Perfect for fitness enthusiasts!

## Features

- **Responsive Design**: Works beautifully on desktop, tablet, and mobile devices
- **Membership Management**: Display different membership tiers with pricing
- **Class Scheduling**: Showcase fitness classes with instructor information
- **Contact Form with Email**: Allow visitors to send inquiries with automatic email notifications
- **Admin Panel**: Manage memberships, classes, and contact submissions
- **SEO Friendly**: Clean URLs and proper HTML structure
- **Minimal JavaScript**: Built with Python and CSS, perfect if you prefer backend development

## Project Structure

```
.
├── config/              # Django settings and URL configuration
│   ├── settings.py     # Project settings
│   ├── urls.py         # Main URL router
│   └── wsgi.py         # WSGI configuration
├── gym_app/            # Main application
│   ├── models.py       # Database models
│   ├── views.py        # View functions
│   ├── urls.py         # App URL routing
│   ├── admin.py        # Admin panel configuration
│   ├── templates/      # HTML templates
│   └── static/         # CSS and JavaScript files
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
└── db.sqlite3         # Database (created after migrations)
```

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Setup Steps

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser** (for admin panel):
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set username, email, and password.

5. **Load sample data** (optional):
   ```bash
   python manage.py shell
   ```
   Then in the Python shell:
   ```python
   from gym_app.models import Membership, Class
   
   # Create sample memberships
   Membership.objects.create(
       name="Basic",
       description="Perfect for beginners",
       price=29.99,
       frequency="monthly",
       features="Access to gym equipment\nOpen during business hours\nBasic support"
   )
   
   Membership.objects.create(
       name="Premium",
       description="All features included",
       price=59.99,
       frequency="monthly",
       features="24/7 gym access\nAll group classes\nPersonal training sessions\nAdvanced support"
   )
   
   # Create sample classes
   Class.objects.create(
       name="High-Intensity Interval Training",
       description="Burn calories fast with our intense circuit workouts",
       instructor="Coach Mike",
       schedule_day="Monday",
       schedule_time="18:00",
       duration_minutes=45,
       max_participants=20
   )
   
   exit()
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Visit the site**:
   - Website: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

## Usage

### Adding Memberships
1. Go to http://localhost:8000/admin
2. Log in with your superuser credentials
3. Click "Memberships" and "Add membership"
4. Fill in the details and save

### Adding Classes
1. In the admin panel, click "Classes" and "Add class"
2. Enter class details and save
3. The class will automatically appear on the Classes page

### View Contact Submissions
1. In the admin panel, click "Contacts"
2. View all messages sent through the contact form

## Pages

- **Home** (`/`): Landing page with features and class previews
- **Memberships** (`/memberships/`): Detailed membership information
- **Classes** (`/classes/`): Available fitness classes
- **About** (`/about/`): Information about the gym
- **Contact** (`/contact/`): Contact form and gym info
- **Admin** (`/admin/`): Manage site content

## Customization

### Branding
Edit the gym name and colors in:
- `base.html`: Change "PowerFit Gym" to your gym name
- `style.css`: Update the `:root` CSS variables for colors

### Homepage Live Status Bar
The homepage can show whether the studio is currently open and which trainer is currently scheduled.

Set these environment variables before starting Django:

```bash
export GYM_TIMEZONE="Europe/Berlin"
export TRAINER_CALENDAR_ICS_URL="https://calendar.google.com/calendar/ical/.../basic.ics"
export TRAINER_CALENDAR_TIMEOUT_SECONDS="5"
export TRAINER_CALENDAR_SYNC_INTERVAL_SECONDS="900"
export LIVE_STATUS_CACHE_SECONDS="60"
```

Notes:
- Use your Google Calendar ICS feed URL for `TRAINER_CALENDAR_ICS_URL`.
- The calendar sync checks Google Calendar at most every 15 minutes by default.
- The status bar uses the gym opening hours defined in code and the trainer name from the current calendar event summary.
- Recurring calendar events are supported.

To run the sync on a real 15-minute server timer, use the included management command:

```bash
python manage.py sync_trainer_calendar --force
```

If you want to manually clear the saved ICS and CSV files and reload the calendar from Google Calendar:

```bash
python manage.py sync_trainer_calendar --reload
```

Example cron entry:

```cron
*/15 * * * * cd /path/to/website_K+F && /bin/bash scripts/sync_trainer_calendar.sh >> /var/log/trainer-calendar-sync.log 2>&1
```

If the site runs under Apache on Linux, `systemd` is usually the cleaner option. Template units are included in `scripts/systemd/`.

Update the placeholders in `scripts/systemd/trainer-calendar-sync.service` first:
- `User` and `Group`
- `WorkingDirectory`
- Conda install path in `conda.sh`

Then install and enable the timer:

```bash
sudo cp scripts/systemd/trainer-calendar-sync.service /etc/systemd/system/
sudo cp scripts/systemd/trainer-calendar-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trainer-calendar-sync.timer
```

Useful checks:

```bash
sudo systemctl status trainer-calendar-sync.timer
sudo systemctl list-timers trainer-calendar-sync.timer
sudo systemctl start trainer-calendar-sync.service
sudo journalctl -u trainer-calendar-sync.service -n 50 --no-pager
```

### Contact Information
Edit in `templates/gym_app/contact.html`:
- Address
- Phone number
- Email
- Business hours

### Email Delivery For The Contact Form
The contact form already saves submissions in the database and can send two emails:
- one notification to the studio inbox
- one confirmation to the visitor

Local development defaults to Django's console email backend, so emails are printed in the terminal. For real delivery, create a `.env` file in the project root and configure SMTP:

```bash
DEBUG=False
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.tld
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=noreply@kpf-fitnessstudio.de
CONTACT_RECIPIENT_EMAIL=info@kpf-fitnessstudio.de
```

Notes:
- `CONTACT_RECIPIENT_EMAIL` is the inbox that receives contact form messages.
- The admin notification sets `Reply-To` to the visitor's email address, so staff can answer directly.
- If your provider requires SSL on port 465, set `EMAIL_USE_SSL=True` and `EMAIL_USE_TLS=False`.

### Styling
All colors and fonts are defined in `gym_app/static/css/style.css`
- Primary colors: Used for buttons and accents
- Fonts: Using system fonts (no external dependencies)

## Database Models

### Membership
- Name, description, price
- Frequency (monthly/annual)
- Features list
- Active status

### Class
- Name, description, instructor
- Schedule day and time
- Duration and max participants

### Contact
- Name, email, message
- Created timestamp
- Read status

## Deployment Considerations

Before deploying to production:

1. Set `DEBUG = False` in `settings.py`
2. Generate a secure `SECRET_KEY`
3. Set `ALLOWED_HOSTS` to your domain
4. Use a production database (PostgreSQL recommended)
5. Collect static files: `python manage.py collectstatic`
6. Use a production WSGI server (Gunicorn, uWSGI)
7. Configure SMTP environment variables for the contact form

## Troubleshooting

**"ModuleNotFoundError: No module named 'django'"**
- Make sure you've activated the virtual environment and installed requirements

**"Port 8000 already in use"**
- Use a different port: `python manage.py runserver 8001`

**Database errors after code changes**
- Create and apply migrations: `python manage.py makemigrations` then `python manage.py migrate`

## Next Steps

- Add user authentication for member login
- Implement payment processing
- Create a booking system for classes
- Add a blog for fitness tips

## Support

For Django documentation, visit: https://docs.djangoproject.com

Happy coding! 💪
