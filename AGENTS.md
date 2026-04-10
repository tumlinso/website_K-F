# Repository Guidelines

## Project Structure & Module Organization
This repository is a Django site rooted at `manage.py`. Global configuration lives in `config/` (`settings.py`, `urls.py`, `wsgi.py`). The main app is `gym_app/`, which contains models, forms, views, URL routes, and a single test module in `gym_app/tests.py`. Templates live in `gym_app/templates/` with page templates under `gym_app/templates/gym_app/`. Static assets live in `gym_app/static/` (`css/`, `js/`, `img/`, `trainer/`, `ics/`). Utility scripts belong in `scripts/`.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` — create and activate a local virtual environment.
- `pip install -r requirements.txt` — install Django and supporting packages.
- `python manage.py migrate` — apply database migrations to `db.sqlite3`.
- `python manage.py runserver` — start the local development server at `http://127.0.0.1:8000/`.
- `python manage.py test` — run the full Django test suite.
- `python manage.py test gym_app.tests.ContactViewTests` — run a focused test class while iterating.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and clear, descriptive names. Use `snake_case` for Python functions, variables, and modules; use `PascalCase` for Django models, forms, and test classes. Keep view logic in `gym_app/views.py` or focused helper modules such as `trainer_cards.py`. Prefer Django templates and server-rendered behavior over adding new JavaScript. Template filenames should stay lowercase and match routes where practical, for example `preise.html` or `contact.html`.

## Testing Guidelines
Use Django’s built-in `TestCase` and name test methods `test_<behavior>`. Mock external services such as reCAPTCHA or email side effects instead of making network calls. Add regression coverage for each change to forms, views, or model behavior. Keep assertions specific: verify status codes, redirects, rendered content, and database side effects.

## Commit & Pull Request Guidelines
Recent commits use short, imperative summaries such as `Fix German spelling across website copy and trainer status` or `fix calendar parsing for new calendar format`. Keep commit messages concise, scoped to one change, and descriptive enough to scan in `git log`. Pull requests should include: a brief summary, affected pages or modules, setup or migration notes, linked issues if available, and screenshots for template or styling changes.

## Security & Configuration Tips
Load local settings from `.env`; start from `.env.example`. Never commit real secrets, SMTP credentials, or reCAPTCHA keys. Before merging config changes, verify `ALLOWED_HOSTS`, email settings, and reCAPTCHA behavior in `config/settings.py`.
