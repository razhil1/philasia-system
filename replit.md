# PhilAsia Pro — Inventory & Operations System

## Overview
A comprehensive movement-based inventory management system for companies managing warehouses and project sites. Built with Python Flask, PostgreSQL, and Bootstrap 5.

## Tech Stack
- **Backend**: Flask (Application Factory + Blueprints)
- **Database**: PostgreSQL (via DATABASE_URL env var) with SQLAlchemy ORM
- **Auth**: Flask-Login + CSRF protection
- **Forms**: Flask-WTF
- **UI**: Bootstrap 5 + Bootstrap Icons + Chart.js

## Key Features
- **Dashboard** with live charts (7-day movement trends), low-stock alerts, recent activity
- **Global Live Search** — Instant search across items, asset tags, sites, warehouses from the topbar
- **Quick Entry** — Fast 3-in-1 form: Consumption, Pullout to Warehouse, or Stock Adjustment — no complex movement form needed
- **Inventory Catalog** — Items with SKU, category, unit cost, photo, reorder threshold
- **Two Item Types with separate workflows:**
  - **Consumables / Materials** (cement, rebar, fuel, etc.) — tracked by quantity. Movements: Delivery, Transfer (WH→Site), Pullout (Site→WH if surplus), Consumption (used up at site, cannot be pulled out), Adjustment, Return, Scrap
  - **Tools / Equipment / Non-Consumables (Assets)** — tracked individually by asset tag. Each physical unit is Transferred to site, Pulled out back to warehouse, or moved to another site. NEVER consumed.
- **Asset Unit Management** — Individual unit lifecycle (Available → Deployed → Maintenance → Scrapped), bulk register, move/pullout per unit
- **QR Code Generation** — QR codes for items and individual asset units (download or print)
- **Print Labels** — Printable label sheets with QR codes for items and asset tags
- **Category Overview** — Inventory value and stock summary grouped by category, with low-stock highlights
- **Stock Ledger** — All quantities calculated from transaction history (immutable audit trail)
- **Warehouses** — Multiple storage facilities with stock tracking and value calculation
- **Project Sites** — Split view: Tools/Equipment (deployed units) vs Materials (consumable stock); both with pullout actions
- **Material Requisitions** — Full workflow: submit → approve/reject → fulfill (auto-transfers stock)
- **Vendor Input / Purchase Receipt** — Multi-item intake form (`/movements/vendor-input`). Mix existing catalog items and brand-new items (auto-created on the fly) in one receipt.
- **Reports with Excel Export** — Stock levels, movement log, and low stock alerts — all exportable to .xlsx
- **User Management** — 7 roles with permission-based access control (admin only)
- **Profile** — Password change for all users

## User Roles
| Role | Key Permissions |
|------|----------------|
| admin | Full access including user management |
| project_manager | Manage sites, approve requests, manage movements |
| delivery_guy | Post movements only |
| accounting | View reports, view sites |
| finance_manager | View reports, approve requests |
| stock_clerk | Manage inventory, post movements, manage warehouses |
| viewer | Read-only (own requests only) |

## Project Structure
```
app/
├── auth/           # Auth blueprint (login/logout)
│   ├── __init__.py
│   ├── forms.py
│   └── routes.py
├── templates/
│   ├── auth/         # login.html
│   ├── inventory/    # dashboard, items, warehouses, sites, movements, requests, categories, overview
│   ├── reports/      # stock, movements, low-stock reports
│   ├── users/        # user management, profile
│   └── layouts/      # base.html
├── static/
│   └── uploads/      # item photos
├── __init__.py       # App factory
├── forms.py          # WTForms definitions
├── models.py         # SQLAlchemy models
└── routes.py         # All business routes + RBAC decorators
config.py             # Config (reads DATABASE_URL, SECRET_KEY)
init_db.py            # Schema init + seed data
run.py                # Entry point (host=0.0.0.0, port=5000)
```

## Running
- Dev server: `python3 run.py`
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port run:app`

## Database
- Replit built-in PostgreSQL via DATABASE_URL env var
- Run `python3 init_db.py` to create/migrate schema and seed admin user
- Default admin: `admin` / `admin123`
- Demo users: `pm_demo`, `clerk_demo`, `viewer_demo`, `delivery_demo` — all password `password123`

## Notes
- `password_hash` uses String(256) to accommodate scrypt hashes
- RBAC uses `current_user.can('permission')` pattern via decorator
- Stock is updated atomically on every movement post
- Requisition fulfillment automatically creates transfer movements
