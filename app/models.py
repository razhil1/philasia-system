from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    managed_sites = db.relationship('ProjectSite', secondary='site_managers', back_populates='managers')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    description = db.Column(db.Text)
    
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    items = db.relationship('Item', backref='category', lazy='dynamic')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    unit = db.Column(db.String(20))
    reorder_level = db.Column(db.Numeric(10, 2), default=0)
    photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255))
    contact_info = db.Column(db.Text)
    stocks = db.relationship('Stock', backref='warehouse', lazy='dynamic')

class ProjectSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    client = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='planned')
    contact_person = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    
    managers = db.relationship('User', secondary='site_managers', back_populates='managed_sites')
    stocks = db.relationship('Stock', backref='site', lazy='dynamic')

site_managers = db.Table('site_managers',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('site_id', db.Integer, db.ForeignKey('project_site.id'), primary_key=True)
)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_type = db.Column(db.String(20)) # 'warehouse' or 'site'
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    item = db.relationship('Item', backref='stocks')

class Movement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(db.String(20)) # 'delivery', 'pullout', 'transfer', 'adjustment'
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    from_location_type = db.Column(db.String(20))
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    from_site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'))
    
    to_location_type = db.Column(db.String(20))
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    to_site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'))
    
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    quantity = db.Column(db.Numeric(10, 2))
    reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    item = db.relationship('Item')
    user = db.relationship('User')
    from_warehouse = db.relationship('Warehouse', foreign_keys=[from_warehouse_id])
    from_site = db.relationship('ProjectSite', foreign_keys=[from_site_id])
    to_warehouse = db.relationship('Warehouse', foreign_keys=[to_warehouse_id])
    to_site = db.relationship('ProjectSite', foreign_keys=[to_site_id])

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_needed = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rejection_reason = db.Column(db.Text)
    
    site = db.relationship('ProjectSite')
    requested_by = db.relationship('User', foreign_keys=[user_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    items = db.relationship('RequestItem', backref='request', lazy='dynamic')

class RequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    quantity_requested = db.Column(db.Numeric(10, 2))
    quantity_delivered = db.Column(db.Numeric(10, 2), default=0)
    
    item = db.relationship('Item')
