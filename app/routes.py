from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Item, Warehouse, ProjectSite, Stock, Movement, Request, Category
from app.forms import ItemForm, WarehouseForm, ProjectSiteForm, MovementForm, RequestForm, RequestItemForm
from sqlalchemy import func
from datetime import datetime
from werkzeug.utils import secure_filename
import os

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    total_items = Item.query.count()
    total_warehouses = Warehouse.query.count()
    total_sites = ProjectSite.query.count()
    recent_movements = Movement.query.order_by(Movement.date.desc()).limit(5).all()
    
    # Low stock alerts
    low_stock_items = []
    items = Item.query.all()
    for item in items:
        total_qty = db.session.query(func.sum(Stock.quantity)).filter(Stock.item_id == item.id).scalar() or 0
        if total_qty < item.reorder_level:
            low_stock_items.append({
                'item': item,
                'current_qty': total_qty
            })

    active_projects = ProjectSite.query.filter_by(status='active').count()
    
    return render_template('inventory/dashboard.html', 
                           total_items=total_items,
                           total_warehouses=total_warehouses,
                           total_sites=total_sites,
                           recent_movements=recent_movements,
                           low_stock_items=low_stock_items[:5],
                           active_projects=active_projects,
                           now=datetime.now())

@main.route('/items')
@login_required
def item_list():
    items = Item.query.all()
    # Calculate stock for each item across all locations for display
    item_stats = []
    for item in items:
        total_qty = db.session.query(func.sum(Stock.quantity)).filter_by(item_id=item.id).scalar() or 0
        item_stats.append({'item': item, 'total_qty': total_qty})
    return render_template('inventory/item_list.html', item_stats=item_stats)

@main.route('/items/new', methods=['GET', 'POST'])
@login_required
def item_create():
    form = ItemForm()
    if form.validate_on_submit():
        filename = None
        if form.photo.data:
            filename = secure_filename(form.photo.data.filename)
            form.photo.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        item = Item(sku=form.sku.data, name=form.name.data, description=form.description.data,
                    category_id=form.category_id.data, unit=form.unit.data, 
                    reorder_level=form.reorder_level.data, photo=filename)
        db.session.add(item)
        db.session.commit()
        flash('Asset successfully registered in catalog.')
        return redirect(url_for('main.item_list'))
    return render_template('inventory/item_form.html', form=form, title='New Asset')

@main.route('/warehouses/new', methods=['GET', 'POST'])
@login_required
def warehouse_create():
    form = WarehouseForm()
    if form.validate_on_submit():
        warehouse = Warehouse(name=form.name.data, location=form.location.data, 
                              contact_info=form.contact_info.data)
        db.session.add(warehouse)
        db.session.commit()
        flash('Central facility registered successfully.')
        return redirect(url_for('main.warehouse_list'))
    return render_template('inventory/warehouse_form.html', form=form, title='New Facility')

@main.route('/sites/new', methods=['GET', 'POST'])
@login_required
def site_create():
    form = ProjectSiteForm()
    if form.validate_on_submit():
        site = ProjectSite(name=form.name.data, address=form.address.data, client=form.client.data,
                           start_date=form.start_date.data, status=form.status.data,
                           contact_person=form.contact_person.data, contact_phone=form.contact_phone.data)
        db.session.add(site)
        db.session.commit()
        flash('Project site authorized for resource allocation.')
        return redirect(url_for('main.site_list'))
    return render_template('inventory/site_form.html', form=form, title='Authorize Site')

def update_stock(item_id, qty, location_type, warehouse_id=None, site_id=None, operation='add'):
    """Helper to update stock levels atomically"""
    if location_type == 'none': return
    
    # Clean zeros/nulls from form selects
    wh_id = warehouse_id if warehouse_id != 0 else None
    s_id = site_id if site_id != 0 else None
    
    stock = Stock.query.filter_by(item_id=item_id, location_type=location_type,
                                 warehouse_id=wh_id, site_id=s_id).first()
    
    if not stock:
        if operation == 'sub': raise ValueError("Insufficient stock in source location.")
        stock = Stock(item_id=item_id, location_type=location_type, 
                      warehouse_id=wh_id, site_id=s_id, quantity=0)
        db.session.add(stock)
        
    if operation == 'add':
        stock.quantity += qty
    else:
        if stock.quantity < qty: raise ValueError("Insufficient stock in source location.")
        stock.quantity -= qty
    
    stock.last_updated = datetime.utcnow()

@main.route('/movements/new', methods=['GET', 'POST'])
@login_required
def movement_create():
    form = MovementForm()
    if form.validate_on_submit():
        try:
            # Atomic update logic
            qty = form.quantity.data
            item_id = form.item_id.data
            
            # 1. Deduct from source
            if form.from_location_type.data != 'none':
                update_stock(item_id, qty, form.from_location_type.data, 
                             form.from_warehouse_id.data, form.from_site_id.data, 'sub')
            
            # 2. Add to target
            if form.to_location_type.data != 'none':
                update_stock(item_id, qty, form.to_location_type.data, 
                             form.to_warehouse_id.data, form.to_site_id.data, 'add')
            
            # 3. Log movement
            movement = Movement(
                movement_type=form.movement_type.data,
                item_id=item_id,
                quantity=qty,
                from_location_type=form.from_location_type.data,
                from_warehouse_id=form.from_warehouse_id.data if form.from_warehouse_id.data != 0 else None,
                from_site_id=form.from_site_id.data if form.from_site_id.data != 0 else None,
                to_location_type=form.to_location_type.data,
                to_warehouse_id=form.to_warehouse_id.data if form.to_warehouse_id.data != 0 else None,
                to_site_id=form.to_site_id.data if form.to_site_id.data != 0 else None,
                reference=form.reference.data,
                notes=form.notes.data,
                user_id=current_user.id
            )
            db.session.add(movement)
            db.session.commit()
            flash('Transaction ledger updated successfully.')
            return redirect(url_for('main.movement_list'))
            
        except ValueError as e:
            db.session.rollback()
            flash(f'Transaction Failed: {str(e)}', 'danger')
            
    return render_template('inventory/movement_form.html', form=form, title='Authorize Transaction')

@main.route('/warehouses')
@login_required
def warehouse_list():
    warehouses = Warehouse.query.all()
    return render_template('inventory/warehouse_list.html', warehouses=warehouses)

@main.route('/sites')
@login_required
def site_list():
    sites = ProjectSite.query.all()
    return render_template('inventory/site_list.html', sites=sites)

@main.route('/movements')
@login_required
def movement_list():
    movements = Movement.query.order_by(Movement.date.desc()).all()
    return render_template('inventory/movement_list.html', movements=movements)

@main.route('/requests')
@login_required
def request_list():
    requests = Request.query.order_by(Request.created_at.desc()).all()
    return render_template('inventory/request_list.html', requests=requests)

@main.route('/requests/new', methods=['GET', 'POST'])
@login_required
def request_create():
    form = RequestForm()
    if form.validate_on_submit():
        request_obj = Request(site_id=form.site_id.data, notes=form.notes.data, 
                             user_id=current_user.id)
        db.session.add(request_obj)
        db.session.commit()
        flash('Material request created. Add items to the request below.')
        return redirect(url_for('main.request_detail', request_id=request_obj.id))
    return render_template('inventory/request_form.html', form=form, title='New Material Request')

@main.route('/requests/<int:request_id>', methods=['GET', 'POST'])
@login_required
def request_detail(request_id):
    from app.models import RequestItem
    request_obj = Request.query.get_or_404(request_id)
    form = RequestItemForm()
    if form.validate_on_submit():
        item = RequestItem(request_id=request_id, item_id=form.item_id.data, 
                           quantity_requested=form.quantity.data)
        db.session.add(item)
        db.session.commit()
        flash('Item added to requisition.')
        return redirect(url_for('main.request_detail', request_id=request_id))
    return render_template('inventory/request_detail.html', request=request_obj, form=form)

@main.route('/reports')
@login_required
def report_list():
    return render_template('inventory/report_list.html')
