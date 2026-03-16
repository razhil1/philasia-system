from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

# Role constants
ROLES = {
    'admin': 'Administrator',
    'project_manager': 'Project Manager',
    'delivery_guy': 'Delivery Personnel',
    'accounting': 'Accounting',
    'finance_manager': 'Finance Manager',
    'stock_clerk': 'Stock Clerk',
    'viewer': 'Viewer',
}

MOVEMENT_TYPES = {
    'delivery': 'Input (from External / Vendor)',
    'transfer': 'Delivery (Warehouse to Project Site)',
    'site_transfer': 'Transfer (Project Site to Project Site)',
    'pullout': 'Pullout (Project Site to Warehouse)',
    'adjustment': 'Adjustment',
    'return': 'Return to Vendor',
    'consumption': 'Consumption (Used up at Site)',
    'scrap': 'Scrap / Disposal',
}

MOVEMENT_COLORS = {
    'delivery': 'success',
    'transfer': 'primary',
    'site_transfer': 'warning',
    'pullout': 'info',
    'adjustment': 'warning',
    'return': 'secondary',
    'consumption': 'danger',
    'scrap': 'dark',
}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    full_name = db.Column(db.String(150))
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(30), default='viewer', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    managed_sites = db.relationship('ProjectSite', secondary='site_managers', back_populates='managers')
    movements = db.relationship('Movement', backref='created_by', foreign_keys='Movement.user_id')
    requests = db.relationship('Request', backref='requested_by', foreign_keys='Request.user_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def has_role(self, *roles):
        return self.role in roles

    def can(self, permission):
        perms = {
            'admin': ['manage_users', 'manage_inventory', 'manage_movements', 'manage_sites',
                      'manage_warehouses', 'approve_requests', 'view_reports', 'manage_categories'],
            'project_manager': ['manage_movements', 'manage_sites', 'approve_requests',
                                'view_reports', 'manage_inventory'],
            'delivery_guy': ['manage_movements'],
            'accounting': ['view_reports', 'manage_sites'],
            'finance_manager': ['view_reports', 'approve_requests', 'manage_sites'],
            'stock_clerk': ['manage_inventory', 'manage_movements', 'manage_warehouses'],
            'viewer': [],
        }
        return permission in perms.get(self.role, [])

    @property
    def role_display(self):
        return ROLES.get(self.role, self.role)

    @property
    def display_name(self):
        return self.full_name or self.username


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

    def __repr__(self):
        return f'<Category {self.name}>'


ITEM_TYPES = {
    'consumable': 'Consumable / Material',
    'asset': 'Asset / Equipment / Tool',
}

ASSET_STATUSES = {
    'available': ('Available', 'success'),
    'deployed': ('Deployed at Site', 'primary'),
    'maintenance': ('Under Maintenance', 'warning'),
    'scrapped': ('Scrapped / Disposed', 'danger'),
}

ASSET_CONDITIONS = {
    'good': ('Good', 'success'),
    'fair': ('Fair', 'warning'),
    'poor': ('Poor', 'danger'),
}


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, index=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    unit = db.Column(db.String(30), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), default=0)
    reorder_level = db.Column(db.Numeric(10, 2), default=0)
    item_type = db.Column(db.String(20), default='consumable', nullable=False)
    photo = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stocks = db.relationship('Stock', backref='item', lazy='dynamic')
    movements = db.relationship('Movement', backref='item', foreign_keys='Movement.item_id')
    asset_units = db.relationship('AssetUnit', backref='item', lazy='dynamic',
                                  cascade='all, delete-orphan')

    @property
    def is_asset(self):
        return self.item_type == 'asset'

    @property
    def is_consumable(self):
        return self.item_type == 'consumable'

    @property
    def type_label(self):
        return ITEM_TYPES.get(self.item_type, self.item_type.title())

    def total_stock(self):
        from sqlalchemy import func
        from app import db as _db
        if self.is_asset:
            return float(AssetUnit.query.filter_by(item_id=self.id).filter(
                AssetUnit.status != 'scrapped').count())
        result = _db.session.query(func.sum(Stock.quantity)).filter_by(item_id=self.id).scalar()
        return float(result or 0)

    def warehouse_stock(self):
        from sqlalchemy import func
        from app import db as _db
        if self.is_asset:
            return float(AssetUnit.query.filter_by(
                item_id=self.id, location_type='warehouse', status='available').count())
        result = _db.session.query(func.sum(Stock.quantity)).filter_by(
            item_id=self.id, location_type='warehouse').scalar()
        return float(result or 0)

    def asset_count_by_status(self):
        counts = {}
        for status in ASSET_STATUSES:
            counts[status] = AssetUnit.query.filter_by(item_id=self.id, status=status).count()
        return counts

    def is_low_stock(self):
        if self.is_asset:
            return self.warehouse_stock() < float(self.reorder_level or 0)
        return self.total_stock() < float(self.reorder_level or 0)

    def __repr__(self):
        return f'<Item {self.sku}: {self.name}>'


class AssetUnit(db.Model):
    __tablename__ = 'asset_unit'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False, index=True)
    serial_number = db.Column(db.String(100))
    status = db.Column(db.String(20), default='available', nullable=False)
    condition = db.Column(db.String(20), default='good', nullable=False)
    location_type = db.Column(db.String(20), default='warehouse')  # warehouse / site
    location_id = db.Column(db.Integer)
    acquired_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    movements = db.relationship('AssetUnitMovement', backref='unit', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def status_label(self):
        return ASSET_STATUSES.get(self.status, (self.status.title(), 'secondary'))[0]

    @property
    def status_color(self):
        return ASSET_STATUSES.get(self.status, (self.status.title(), 'secondary'))[1]

    @property
    def condition_label(self):
        return ASSET_CONDITIONS.get(self.condition, (self.condition.title(), 'secondary'))[0]

    @property
    def condition_color(self):
        return ASSET_CONDITIONS.get(self.condition, (self.condition.title(), 'secondary'))[1]

    def location_name(self):
        if self.location_type == 'warehouse':
            from app.models import Warehouse as _WH
            w = _WH.query.get(self.location_id)
            return w.name if w else 'Unknown Warehouse'
        elif self.location_type == 'site':
            s = ProjectSite.query.get(self.location_id)
            return s.name if s else 'Unknown Site'
        return 'Unassigned'

    def __repr__(self):
        return f'<AssetUnit {self.asset_tag}>'


class AssetUnitMovement(db.Model):
    __tablename__ = 'asset_unit_movement'
    id = db.Column(db.Integer, primary_key=True)
    asset_unit_id = db.Column(db.Integer, db.ForeignKey('asset_unit.id'), nullable=False)
    movement_id = db.Column(db.Integer, db.ForeignKey('movement.id'), nullable=False)
    movement = db.relationship('Movement')


class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255))
    contact_person = db.Column(db.String(100))
    contact_info = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stocks = db.relationship('Stock', backref='warehouse',
                             lazy='dynamic', foreign_keys='Stock.warehouse_id')

    def __repr__(self):
        return f'<Warehouse {self.name}>'


class ProjectSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    client = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='planned')
    contact_person = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    budget = db.Column(db.Numeric(14, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    managers = db.relationship('User', secondary='site_managers', back_populates='managed_sites')
    stocks = db.relationship('Stock', backref='site', lazy='dynamic', foreign_keys='Stock.site_id')
    requests = db.relationship('Request', backref='site', lazy='dynamic')

    @property
    def status_color(self):
        colors = {'planned': 'secondary', 'active': 'success', 'on_hold': 'warning', 'completed': 'primary'}
        return colors.get(self.status, 'secondary')

    def __repr__(self):
        return f'<ProjectSite {self.name}>'


site_managers = db.Table('site_managers',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('site_id', db.Integer, db.ForeignKey('project_site.id'), primary_key=True)
)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_type = db.Column(db.String(20), nullable=False)  # 'warehouse' or 'site'
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def location_name(self):
        if self.location_type == 'warehouse' and self.warehouse:
            return self.warehouse.name
        elif self.location_type == 'site' and self.site:
            return self.site.name
        return 'Unknown'


class Movement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    from_location_type = db.Column(db.String(20))  # 'warehouse', 'site', 'external', None
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    from_site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'), nullable=True)

    to_location_type = db.Column(db.String(20))  # 'warehouse', 'site', 'external', None
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    to_site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'), nullable=True)

    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), default=0)
    reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=True)

    from_warehouse = db.relationship('Warehouse', foreign_keys=[from_warehouse_id])
    from_site = db.relationship('ProjectSite', foreign_keys=[from_site_id])
    to_warehouse = db.relationship('Warehouse', foreign_keys=[to_warehouse_id])
    to_site = db.relationship('ProjectSite', foreign_keys=[to_site_id])

    @property
    def type_label(self):
        return MOVEMENT_TYPES.get(self.movement_type, self.movement_type.title())

    @property
    def type_color(self):
        return MOVEMENT_COLORS.get(self.movement_type, 'secondary')

    def from_location_name(self):
        if self.from_location_type == 'warehouse' and self.from_warehouse:
            return self.from_warehouse.name
        elif self.from_location_type == 'site' and self.from_site:
            return self.from_site.name
        elif self.from_location_type == 'external':
            return 'External / Vendor'
        return '—'

    def to_location_name(self):
        if self.to_location_type == 'warehouse' and self.to_warehouse:
            return self.to_warehouse.name
        elif self.to_location_type == 'site' and self.to_site:
            return self.to_site.name
        elif self.to_location_type == 'external':
            return 'External / Disposed'
        return '—'


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('project_site.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_needed = db.Column(db.Date)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, approved, partial, fulfilled, rejected
    notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    items = db.relationship('RequestItem', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    movements = db.relationship('Movement', backref='requisition', foreign_keys='Movement.request_id')

    @property
    def status_color(self):
        colors = {'pending': 'warning', 'approved': 'info', 'partial': 'primary',
                  'fulfilled': 'success', 'rejected': 'danger'}
        return colors.get(self.status, 'secondary')

    @property
    def priority_color(self):
        colors = {'low': 'secondary', 'normal': 'info', 'high': 'warning', 'urgent': 'danger'}
        return colors.get(self.priority, 'secondary')


class RequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity_requested = db.Column(db.Numeric(10, 2), nullable=False)
    quantity_delivered = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.String(200))

    item = db.relationship('Item')

    @property
    def is_fulfilled(self):
        return float(self.quantity_delivered or 0) >= float(self.quantity_requested or 0)
