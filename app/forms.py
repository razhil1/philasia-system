from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, DecimalField, SelectField,
                     DateField, SubmitField, BooleanField, PasswordField)
from wtforms.validators import DataRequired, Optional, NumberRange, Email, Length, EqualTo
from app.models import ROLES, MOVEMENT_TYPES, ITEM_TYPES, ASSET_STATUSES, ASSET_CONDITIONS


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[Optional(), Length(max=150)])
    role = SelectField('Role', choices=[(k, v) for k, v in ROLES.items()], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Save User')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('new_password')])
    submit = SubmitField('Change Password')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Category')


class ItemForm(FlaskForm):
    sku = StringField('SKU / Item Code', validators=[DataRequired(), Length(max=50)])
    name = StringField('Item Name', validators=[DataRequired(), Length(max=200)])
    item_type = SelectField('Item Type', choices=[
        ('consumable', 'Consumable / Material — tracked by quantity'),
        ('asset', 'Asset / Equipment / Tool — tracked individually'),
    ], default='consumable', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    unit = StringField('Unit (e.g., pcs, kg, bag)', validators=[DataRequired(), Length(max=30)])
    unit_cost = DecimalField('Unit Cost', default=0, validators=[Optional(), NumberRange(min=0)])
    reorder_level = DecimalField('Reorder Alert Threshold', default=0, validators=[Optional(), NumberRange(min=0)])
    photo = FileField('Item Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Item')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Category
        self.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name').all()]


class AssetUnitForm(FlaskForm):
    asset_tag = StringField('Asset Tag / Code', validators=[DataRequired(), Length(max=50)],
                            description='Unique identifier, e.g. GEN-001-001')
    serial_number = StringField('Serial Number', validators=[Optional(), Length(max=100)])
    status = SelectField('Status', choices=[(k, v[0]) for k, v in ASSET_STATUSES.items()],
                         default='available', validators=[DataRequired()])
    condition = SelectField('Condition', choices=[(k, v[0]) for k, v in ASSET_CONDITIONS.items()],
                            default='good', validators=[DataRequired()])
    location_type = SelectField('Current Location Type', choices=[
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site'),
    ], default='warehouse', validators=[DataRequired()])
    location_id = SelectField('Location', coerce=int, validators=[DataRequired()])
    acquired_date = DateField('Date Acquired', validators=[Optional()])
    notes = TextAreaField('Notes / Remarks', validators=[Optional()])
    submit = SubmitField('Save Unit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Warehouse, ProjectSite
        wh = [(w.id, f'[WH] {w.name}') for w in Warehouse.query.filter_by(is_active=True).order_by('name').all()]
        st = [(s.id, f'[SITE] {s.name}') for s in ProjectSite.query.order_by('name').all()]
        self.location_id.choices = wh + st if wh or st else [(0, '— No locations —')]


class AssetMovementForm(FlaskForm):
    movement_type = SelectField('Movement Type', choices=[
        ('transfer', 'Transfer to Site'),
        ('pullout', 'Pullout — Return to Warehouse'),
        ('delivery', 'New Delivery / Received'),
        ('maintenance', 'Send to Maintenance'),
        ('scrap', 'Scrap / Dispose'),
        ('adjustment', 'Adjustment'),
    ], validators=[DataRequired()])
    to_location_type = SelectField('Destination Type', choices=[
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site'),
        ('none', 'N/A (Scrapped/Disposed)'),
    ], default='warehouse', validators=[DataRequired()])
    to_warehouse_id = SelectField('Destination Warehouse', coerce=int, validators=[Optional()])
    to_site_id = SelectField('Destination Site', coerce=int, validators=[Optional()])
    condition = SelectField('New Condition', choices=[(k, v[0]) for k, v in ASSET_CONDITIONS.items()],
                            default='good', validators=[Optional()])
    reference = StringField('Reference # (DR/PO/RR)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Remarks / Notes', validators=[Optional()])
    submit = SubmitField('Move Units')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Warehouse, ProjectSite
        wh = [(0, '— Select —')] + [(w.id, w.name) for w in Warehouse.query.filter_by(is_active=True).order_by('name').all()]
        st = [(0, '— Select —')] + [(s.id, s.name) for s in ProjectSite.query.order_by('name').all()]
        self.to_warehouse_id.choices = wh
        self.to_site_id.choices = st


class WarehouseForm(FlaskForm):
    name = StringField('Warehouse Name', validators=[DataRequired(), Length(max=100)])
    location = StringField('Address / Location', validators=[DataRequired(), Length(max=255)])
    contact_person = StringField('Person in Charge', validators=[Optional(), Length(max=100)])
    contact_info = TextAreaField('Contact Details', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Warehouse')


class ProjectSiteForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    address = TextAreaField('Site Address', validators=[DataRequired()])
    client = StringField('Client / Company', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('Target End Date', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('planned', 'Planned / Pending'),
        ('active', 'Active / Ongoing'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ], validators=[DataRequired()])
    contact_person = StringField('Site Supervisor', validators=[DataRequired(), Length(max=100)])
    contact_phone = StringField('Contact Number', validators=[DataRequired(), Length(max=50)])
    budget = DecimalField('Project Budget', default=0, validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField('Notes / Remarks', validators=[Optional()])
    submit = SubmitField('Save Project Site')


class MovementForm(FlaskForm):
    movement_type = SelectField('Transaction Type',
        choices=[(k, v) for k, v in MOVEMENT_TYPES.items()],
        validators=[DataRequired()])
    item_id = SelectField('Item / Asset', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(), NumberRange(min=0.001)])
    unit_cost = DecimalField('Unit Cost', default=0, validators=[Optional(), NumberRange(min=0)])

    from_location_type = SelectField('Source Type', choices=[
        ('external', 'External / Vendor'),
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site'),
        ('none', 'N/A'),
    ], default='external')
    from_warehouse_id = SelectField('Source Warehouse', coerce=int, validators=[Optional()])
    from_site_id = SelectField('Source Site', coerce=int, validators=[Optional()])

    to_location_type = SelectField('Destination Type', choices=[
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site'),
        ('external', 'External / Disposed'),
        ('none', 'N/A'),
    ], default='warehouse')
    to_warehouse_id = SelectField('Destination Warehouse', coerce=int, validators=[Optional()])
    to_site_id = SelectField('Destination Site', coerce=int, validators=[Optional()])

    reference = StringField('Reference # (PO/DR/RR)', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Remarks / Notes', validators=[Optional()])
    submit = SubmitField('Post Transaction')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Item, Warehouse, ProjectSite
        self.item_id.choices = [(i.id, f"{i.name} [{i.sku}]") for i in Item.query.filter_by(is_active=True).order_by('name').all()]
        wh = [(0, '— Select —')] + [(w.id, w.name) for w in Warehouse.query.filter_by(is_active=True).order_by('name').all()]
        st = [(0, '— Select —')] + [(s.id, s.name) for s in ProjectSite.query.order_by('name').all()]
        self.from_warehouse_id.choices = wh
        self.from_site_id.choices = st
        self.to_warehouse_id.choices = wh
        self.to_site_id.choices = st


class RequestForm(FlaskForm):
    site_id = SelectField('Project Site', coerce=int, validators=[DataRequired()])
    date_needed = DateField('Date Needed', validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')
    ], default='normal')
    notes = TextAreaField('Purpose / Reason', validators=[Optional()])
    submit = SubmitField('Submit Requisition')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import ProjectSite
        self.site_id.choices = [(s.id, s.name) for s in ProjectSite.query.filter(
            ProjectSite.status.in_(['active', 'planned'])).order_by('name').all()]


class RequestItemForm(FlaskForm):
    item_id = SelectField('Item', coerce=int, validators=[DataRequired()])
    quantity_requested = DecimalField('Quantity', validators=[DataRequired(), NumberRange(min=0.001)])
    notes = StringField('Notes', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Add Item')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Item
        self.item_id.choices = [(i.id, f"{i.name} [{i.sku}] \u2013 {i.unit}") for i in
                                Item.query.filter_by(is_active=True).order_by('name').all()]


class ApproveRequestForm(FlaskForm):
    submit = SubmitField('Approve Requisition')


class RejectRequestForm(FlaskForm):
    rejection_reason = TextAreaField('Reason for Rejection', validators=[DataRequired()])
    submit = SubmitField('Reject Requisition')


class ReportFilterForm(FlaskForm):
    date_from = DateField('From Date', validators=[Optional()])
    date_to = DateField('To Date', validators=[Optional()])
    warehouse_id = SelectField('Warehouse', coerce=int, validators=[Optional()])
    site_id = SelectField('Project Site', coerce=int, validators=[Optional()])
    movement_type = SelectField('Movement Type', validators=[Optional()])
    submit = SubmitField('Generate Report')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.models import Warehouse, ProjectSite
        self.warehouse_id.choices = [(0, 'All Warehouses')] + [
            (w.id, w.name) for w in Warehouse.query.order_by('name').all()]
        self.site_id.choices = [(0, 'All Sites')] + [
            (s.id, s.name) for s in ProjectSite.query.order_by('name').all()]
        self.movement_type.choices = [('', 'All Types')] + list(MOVEMENT_TYPES.items())
