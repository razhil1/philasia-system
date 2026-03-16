# PhilAsia Pro: Inventory & Project Management System

A professional, movement-based inventory management system designed for industrial and construction operations. Built with **Flask**, **SQLAlchemy**, and **QuickBooks-inspired UI**.

## 🚀 Overview
PhilAsia Pro is a local-first, high-performance inventory system that tracks assets across multiple warehouses and project sites. Unlike traditional systems that simply update "current stock", this system uses a **transactional ledger** approach—calculating stock from a complete audit trail of movements.

## 🏗️ Technical Architecture
- **Framework**: Flask (Application Factory Pattern)
- **Database**: SQLAlchemy ORM (SQLite for local / PostgreSQL for production)
- **UI/UX**: Bootstrap 5 + Custom CSS (QuickBooks Aesthetic)
- **Authentication**: Flask-Login with Role-Based Access
- **Security**: CSRF Protection & Password Hashing (Werkzeug)

## ✨ Core Features
- **Asset Catalog**: Track tools, equipment, and consumables with SKU-level precision and reorder thresholds.
- **Stock Movement Ledger**: Transactional tracking of:
  - **Deliveries**: Intake from vendors to central warehouses.
  - **Transfers**: Moving resources between facilities or sites.
  - **Pullouts**: Returning assets from sites to storage.
  - **Adjustments**: Corrections for scrap, loss, or audits.
- **Project Site Monitor**: Real-time visibility into resource allocation at various construction project sites.
- **Material Requisitions**: Streamlined workflow for site managers to request supplies from the warehouse.
- **Audit Trail**: Every gram of material and every single tool is tracked with an immutable record of "Who, What, Where, and When".

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+
- Virtual Environment (`venv`)

### Installation Steps
1. **Clone the Repository**
   ```bash
   git clone <your-repository-url>
   cd PhilAsia-System
   ```

2. **Setup Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Initialize the Database**
   ```bash
   python init_db.py
   ```

4. **Run Locally**
   ```bash
   python run.py
   ```
   Access the system at `http://127.0.0.1:5000`

## 📁 Project Structure
```text
PhilAsia System/
├── app/
│   ├── auth/            # Authentication logic & Blueprints
│   ├── templates/       # Professional QuickBooks-style pages
│   ├── models.py        # SQLAlchemy Database Models
│   ├── routes.py        # Core Business Logic & Inventory API
│   └── forms.py         # Validated Input Forms
├── config.py            # Environment & Security Configuration
├── init_db.py           # Database Seeding & Schema Creation
└── run.py               # Application Entry Point
```

## 🛡️ Safety & Data Integrity
- **Atomic Updates**: Stock level updates are performed as atomic transactions to ensure no quantity is ever "lost" in a transfer.
- **Validation**: Strict server-side validation prevents negative inventory balances.
- **Audit Logs**: All movements are linked to the user who authorized them.

---
*Built for PhilAsia Operations — Modernized for Growth.*
