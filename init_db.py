from app import create_app, db
from app.models import User, Category

app = create_app()

with app.app_context():
    db.create_all()
    
    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")
        
    # Create some default categories
    if not Category.query.first():
        cats = ['Tools', 'Equipment', 'Materials', 'Consumables']
        for cat_name in cats:
            c = Category(name=cat_name)
            db.session.add(c)
        db.session.commit()
        print("Default categories created.")
