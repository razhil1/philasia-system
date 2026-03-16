from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, DecimalField, SelectField, DateField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange
from app.models import Category, Warehouse, ProjectSite, Item

class ItemForm(FlaskForm):
    sku = StringField('SKU/Identifier', validators=[DataRequired()])
    name = StringField('Product/Asset Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    unit = StringField('Unit (e.g., Pcs, Bags, Liters)', validators=[DataRequired()])
    reorder_level = DecimalField('Reorder Threshold', default=0, validators=[DataRequired()])
    photo = FileField('Asset Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Save Asset')

    def __init__(self, *args, **kwargs):
        super(ItemForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

class WarehouseForm(FlaskForm):
    name = StringField('Warehouse Name', validators=[DataRequired()])
    location = StringField('Location/Address', validators=[DataRequired()])
    contact_info = TextAreaField('Authority/Contact Info', validators=[Optional()])
    submit = SubmitField('Register Warehouse')

class ProjectSiteForm(FlaskForm):
    name = StringField('Project Site Name', validators=[DataRequired()])
    address = TextAreaField('Site Address', validators=[DataRequired()])
    client = StringField('Client Name', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    status = SelectField('Project Status', choices=[
        ('planned', 'Planned / Pending'),
        ('active', 'Active / Ongoing'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed')
    ], validators=[DataRequired()])
    contact_person = StringField('Site Supervisor', validators=[DataRequired()])
    contact_phone = StringField('Direct Line', validators=[DataRequired()])
    submit = SubmitField('Authorize Project Site')

class MovementForm(FlaskForm):
    movement_type = SelectField('Transaction Type', choices=[
        ('delivery', 'Delivery (Inflow from Vendor/WH)'),
        ('pullout', 'Pullout (Return from Site)'),
        ('transfer', 'Transfer (WH to WH / Site to Site)'),
        ('adjustment', 'Quantity Adjustment')
    ], validators=[DataRequired()])
    item_id = SelectField('Select Asset', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Volume / Quantity', validators=[DataRequired(), NumberRange(min=0.01)])
    
    from_location_type = SelectField('From Type', choices=[
        ('none', 'N/A (External Vendor)'),
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site')
    ], default='none')
    from_warehouse_id = SelectField('From Warehouse', coerce=int, validators=[Optional()])
    from_site_id = SelectField('From Site', coerce=int, validators=[Optional()])
    
    to_location_type = SelectField('To Type', choices=[
        ('warehouse', 'Warehouse'),
        ('site', 'Project Site'),
        ('none', 'N/A (Lost / Scrapped)')
    ], default='warehouse')
    to_warehouse_id = SelectField('To Warehouse', coerce=int, validators=[Optional()])
    to_site_id = SelectField('To Site', coerce=int, validators=[Optional()])
    
    reference = StringField('Reference # (PO/Receipt)', validators=[Optional()])
    notes = TextAreaField('Audit Notes', validators=[Optional()])
    submit = SubmitField('Authorize Transaction')

    def __init__(self, *args, **kwargs):
        super(MovementForm, self).__init__(*args, **kwargs)
        self.item_id.choices = [(i.id, f"{i.name} ({i.sku})") for i in Item.query.all()]
        self.from_warehouse_id.choices = [(0, 'Select...')] + [(w.id, w.name) for w in Warehouse.query.all()]
        self.from_site_id.choices = [(0, 'Select...')] + [(s.id, s.name) for s in ProjectSite.query.all()]
        self.to_warehouse_id.choices = [(0, 'Select...')] + [(w.id, w.name) for w in Warehouse.query.all()]
        self.to_site_id.choices = [(0, 'Select...')] + [(s.id, s.name) for s in ProjectSite.query.all()]

class RequestForm(FlaskForm):
    site_id = SelectField('Your Project Site', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Priority / Reason for Request', validators=[Optional()])
    submit = SubmitField('Submit Material Request')

    def __init__(self, *args, **kwargs):
        super(RequestForm, self).__init__(*args, **kwargs)
        self.site_id.choices = [(s.id, s.name) for s in ProjectSite.query.filter_by(status='active').all()]

class RequestItemForm(FlaskForm):
    item_id = SelectField('Select Asset', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Requested Volume', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Add to Request')

    def __init__(self, *args, **kwargs):
        super(RequestItemForm, self).__init__(*args, **kwargs)
        self.item_id.choices = [(i.id, f"{i.name} ({i.sku})") for i in Item.query.all()]
