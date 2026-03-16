# PhilAsia Pro: Inventory & Project Management System

## Overview
A professional, movement-based inventory management system for industrial and construction operations. Uses a transactional ledger approach — all stock levels are derived from a complete audit trail of movements.

## Architecture
- **Framework**: Flask (Application Factory Pattern, Blueprints)
- **Database**: PostgreSQL (via `DATABASE_URL` env var) with SQLAlchemy ORM
- **Auth**: Flask-Login with role-based access (admin flag on User)
- **Forms**: Flask-WTF with CSRF protection
- **UI**: Jinja2 templates with Bootstrap 5

## Project Structure
```
app/
├── auth/           # Auth blueprint (login/logout)
├── templates/      # Jinja2 HTML templates
│   ├── auth/
│   ├── inventory/
│   └── layouts/
├── __init__.py     # App factory (create_app)
├── forms.py        # WTForms form definitions
├── models.py       # SQLAlchemy models
└── routes.py       # Main blueprint routes
config.py           # Config class (reads env vars)
init_db.py          # DB schema init + seed data
run.py              # Entry point (host=0.0.0.0, port=5000)
```

## Key Models
- **User**: Auth with admin flag, manages project sites
- **Category**: Hierarchical item categories
- **Item**: Asset catalog (SKU, unit, reorder level, photo)
- **Warehouse**: Storage facilities
- **ProjectSite**: Construction project sites
- **Stock**: Current quantity per item per location (warehouse or site)
- **Movement**: Immutable ledger entries (delivery, transfer, pullout, adjustment)
- **Request / RequestItem**: Material requisitions from site managers

## Running
- Dev: `python3 run.py` (port 5000, 0.0.0.0)
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port run:app`

## Database Setup
- Uses Replit's built-in PostgreSQL (`DATABASE_URL` env var set automatically)
- Run `python3 init_db.py` to create tables and seed admin user + default categories
- Default admin: username=`admin`, password=`admin123`

## Notes
- `password_hash` column uses `String(256)` (not 128) to accommodate scrypt hashes
- File uploads stored in `app/static/uploads/` (created automatically)
