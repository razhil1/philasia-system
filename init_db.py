from app import create_app, db
from app.models import User, Category, ROLES

app = create_app()

with app.app_context():
    db.create_all()

    # Admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@philasia.com',
                     full_name='System Administrator', role='admin', is_active=True)
        admin.set_password('admin123')
        db.session.add(admin)
        print("Admin user created.")
    else:
        # Ensure existing admin has role set
        admin = User.query.filter_by(username='admin').first()
        if not admin.role or admin.role == 'viewer':
            admin.role = 'admin'
        if not admin.full_name:
            admin.full_name = 'System Administrator'
        print("Admin user already exists — updated role.")

    # Demo users for each role
    demo_users = [
        ('pm_demo', 'pm@philasia.com', 'Project Manager Demo', 'project_manager'),
        ('clerk_demo', 'clerk@philasia.com', 'Stock Clerk Demo', 'stock_clerk'),
        ('viewer_demo', 'viewer@philasia.com', 'Viewer Demo', 'viewer'),
        ('delivery_demo', 'delivery@philasia.com', 'Delivery Demo', 'delivery_guy'),
    ]
    for uname, email, fname, role in demo_users:
        if not User.query.filter_by(username=uname).first():
            u = User(username=uname, email=email, full_name=fname, role=role, is_active=True)
            u.set_password('password123')
            db.session.add(u)
    db.session.commit()

    # Categories
    if not Category.query.first():
        cats = ['Tools & Equipment', 'Construction Materials', 'Safety Gear',
                'Electrical Supplies', 'Plumbing & Piping', 'Consumables', 'Machinery', 'Office Supplies']
        for cname in cats:
            db.session.add(Category(name=cname))
        db.session.commit()
        print("Default categories created.")

    print("Database initialized successfully.")
    print("\nDefault credentials:")
    print("  Admin:   admin / admin123")
    print("  Others:  <username> / password123")
