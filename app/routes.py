from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, abort, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import (Item, Warehouse, ProjectSite, Stock, Movement, Request,
                         RequestItem, Category, User, MOVEMENT_TYPES)
from app.forms import (ItemForm, WarehouseForm, ProjectSiteForm, MovementForm,
                        RequestForm, RequestItemForm, UserForm, CategoryForm,
                        ApproveRequestForm, RejectRequestForm, ReportFilterForm,
                        ChangePasswordForm)
from sqlalchemy import func, desc
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os

main = Blueprint('main', __name__)


def permission_required(perm):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.can(perm):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def _update_stock(item_id, location_type, warehouse_id, site_id, delta):
    if location_type in (None, 'none', 'external'):
        return
    q = Stock.query.filter_by(item_id=item_id, location_type=location_type)
    if location_type == 'warehouse':
        q = q.filter_by(warehouse_id=warehouse_id)
    else:
        q = q.filter_by(site_id=site_id)
    stock = q.first()
    if stock is None:
        stock = Stock(item_id=item_id, location_type=location_type,
                      warehouse_id=warehouse_id if location_type == 'warehouse' else None,
                      site_id=site_id if location_type == 'site' else None,
                      quantity=0)
        db.session.add(stock)
    stock.quantity = float(stock.quantity) + delta
    stock.last_updated = datetime.utcnow()


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    total_items = Item.query.filter_by(is_active=True).count()
    total_warehouses = Warehouse.query.filter_by(is_active=True).count()
    total_sites = ProjectSite.query.count()
    active_projects = ProjectSite.query.filter_by(status='active').count()
    pending_requests = Request.query.filter_by(status='pending').count()
    total_movements_today = Movement.query.filter(
        func.date(Movement.date) == date.today()).count()

    recent_movements = Movement.query.order_by(desc(Movement.date)).limit(8).all()
    recent_requests = Request.query.order_by(desc(Request.created_at)).limit(5).all()

    low_stock_items = []
    for item in Item.query.filter_by(is_active=True).all():
        total_qty = item.total_stock()
        if total_qty < float(item.reorder_level or 0):
            low_stock_items.append({'item': item, 'current_qty': total_qty})

    # Chart data: movements per day last 7 days
    chart_labels = []
    chart_inflow = []
    chart_outflow = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        chart_labels.append(d.strftime('%b %d'))
        inflow_types = ['delivery', 'return', 'pullout']
        outflow_types = ['transfer', 'consumption', 'scrap', 'adjustment']
        inflow = db.session.query(func.sum(Movement.quantity)).filter(
            func.date(Movement.date) == d,
            Movement.movement_type.in_(inflow_types)).scalar() or 0
        outflow = db.session.query(func.sum(Movement.quantity)).filter(
            func.date(Movement.date) == d,
            Movement.movement_type.in_(outflow_types)).scalar() or 0
        chart_inflow.append(float(inflow))
        chart_outflow.append(float(outflow))

    return render_template('inventory/dashboard.html',
        total_items=total_items, total_warehouses=total_warehouses,
        total_sites=total_sites, active_projects=active_projects,
        pending_requests=pending_requests, total_movements_today=total_movements_today,
        recent_movements=recent_movements, recent_requests=recent_requests,
        low_stock_items=low_stock_items[:5],
        chart_labels=chart_labels, chart_inflow=chart_inflow, chart_outflow=chart_outflow,
        now=datetime.now())


# ─── CATEGORIES ───────────────────────────────────────────────────────────────

@main.route('/categories')
@login_required
def category_list():
    categories = Category.query.order_by(Category.name).all()
    return render_template('inventory/category_list.html', categories=categories)


@main.route('/categories/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_categories')
def category_create():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data, description=form.description.data)
        db.session.add(cat)
        db.session.commit()
        flash('Category created successfully.', 'success')
        return redirect(url_for('main.category_list'))
    return render_template('inventory/category_form.html', form=form, title='New Category')


@main.route('/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_categories')
def category_edit(cat_id):
    cat = Category.query.get_or_404(cat_id)
    form = CategoryForm(obj=cat)
    if form.validate_on_submit():
        cat.name = form.name.data
        cat.description = form.description.data
        db.session.commit()
        flash('Category updated.', 'success')
        return redirect(url_for('main.category_list'))
    return render_template('inventory/category_form.html', form=form, title='Edit Category')


# ─── ITEMS ────────────────────────────────────────────────────────────────────

@main.route('/items')
@login_required
def item_list():
    items = Item.query.filter_by(is_active=True).order_by(Item.name).all()
    item_stats = []
    for item in items:
        total_qty = item.total_stock()
        item_stats.append({'item': item, 'total_qty': total_qty, 'low': item.is_low_stock()})
    return render_template('inventory/item_list.html', item_stats=item_stats)


@main.route('/items/<int:item_id>')
@login_required
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    stocks = Stock.query.filter_by(item_id=item_id).all()
    movements = Movement.query.filter_by(item_id=item_id).order_by(desc(Movement.date)).limit(20).all()
    return render_template('inventory/item_detail.html', item=item, stocks=stocks, movements=movements)


@main.route('/items/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_inventory')
def item_create():
    form = ItemForm()
    if form.validate_on_submit():
        filename = None
        if form.photo.data and form.photo.data.filename:
            filename = secure_filename(form.photo.data.filename)
            form.photo.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        item = Item(sku=form.sku.data, name=form.name.data, description=form.description.data,
                    category_id=form.category_id.data, unit=form.unit.data,
                    unit_cost=form.unit_cost.data or 0,
                    reorder_level=form.reorder_level.data or 0,
                    photo=filename, is_active=form.is_active.data)
        db.session.add(item)
        db.session.commit()
        flash('Item registered successfully.', 'success')
        return redirect(url_for('main.item_list'))
    return render_template('inventory/item_form.html', form=form, title='New Item')


@main.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_inventory')
def item_edit(item_id):
    item = Item.query.get_or_404(item_id)
    form = ItemForm(obj=item)
    if form.validate_on_submit():
        if form.photo.data and form.photo.data.filename:
            filename = secure_filename(form.photo.data.filename)
            form.photo.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            item.photo = filename
        item.sku = form.sku.data
        item.name = form.name.data
        item.description = form.description.data
        item.category_id = form.category_id.data
        item.unit = form.unit.data
        item.unit_cost = form.unit_cost.data or 0
        item.reorder_level = form.reorder_level.data or 0
        item.is_active = form.is_active.data
        db.session.commit()
        flash('Item updated.', 'success')
        return redirect(url_for('main.item_detail', item_id=item_id))
    return render_template('inventory/item_form.html', form=form, title='Edit Item', item=item)


# ─── ITEMS BULK IMPORT ────────────────────────────────────────────────────────

ALLOWED_IMPORT_EXTS = {'xlsx', 'xls', 'csv'}

def _allowed_import(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMPORT_EXTS


@main.route('/items/import/template')
@login_required
@permission_required('manage_inventory')
def item_import_template():
    """Download a blank Excel template for bulk item import."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from flask import send_file
    import io

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Items Import'

    headers = ['SKU*', 'Name*', 'Category', 'Unit*', 'Unit Cost', 'Reorder Level', 'Description']
    col_widths = [18, 40, 25, 12, 14, 16, 45]

    header_fill = PatternFill(start_color='1a6fd4', end_color='1a6fd4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    thin = Side(style='thin', color='D0D0D0')
    border = Border(left=thin, right=thin, bottom=thin)

    for col_idx, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[chr(64 + col_idx)].width = width

    ws.row_dimensions[1].height = 28

    # Sample rows
    cats = [c.name for c in Category.query.order_by('name').limit(5).all()]
    samples = [
        ['TOOL-001', 'Safety Helmet (White)', cats[0] if cats else 'Safety Gear', 'pcs', 350.00, 20, 'Standard white hard hat'],
        ['TOOL-002', 'Work Gloves (Leather)', cats[0] if cats else 'Safety Gear', 'pairs', 120.00, 30, 'Heavy duty leather gloves'],
        ['MAT-001', 'Portland Cement', cats[1] if len(cats) > 1 else 'Materials', 'bags', 280.00, 50, '40kg bag Portland Type I'],
        ['MAT-002', 'Steel Rebar 10mm x 6m', cats[1] if len(cats) > 1 else 'Materials', 'pcs', 180.00, 100, 'Grade 60 deformed bar'],
        ['ELEC-001', 'THHN Wire 3.5mm', cats[2] if len(cats) > 2 else 'Electrical', 'm', 75.00, 200, 'THHN/THWN stranded wire'],
    ]
    alt_fill = PatternFill(start_color='EEF4FF', end_color='EEF4FF', fill_type='solid')

    for row_idx, row_data in enumerate(samples, 2):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = border
            cell.alignment = Alignment(vertical='center')
            if row_idx % 2 == 0:
                cell.fill = alt_fill

    # Instructions sheet
    ws_info = wb.create_sheet('Instructions')
    ws_info.column_dimensions['A'].width = 60
    notes = [
        ('PhilAsia Pro — Items Import Template', True),
        ('', False),
        ('COLUMN GUIDE:', True),
        ('SKU* — Unique item code (required). Will be skipped if already exists.', False),
        ('Name* — Item display name (required).', False),
        ('Category — Must match an existing category name exactly. Leave blank for none.', False),
        ('Unit* — Unit of measure (pcs, kg, bags, m, liters, etc.) — required.', False),
        ('Unit Cost — Cost per unit in Philippine Peso. Default 0.', False),
        ('Reorder Level — Low stock alert threshold. Default 0.', False),
        ('Description — Optional. Additional details about the item.', False),
        ('', False),
        ('TIPS:', True),
        ('• Rows with duplicate SKUs are skipped (existing items not overwritten).', False),
        ('• Rows missing SKU, Name, or Unit are skipped.', False),
        ('• Import supports .xlsx, .xls, and .csv formats.', False),
        ('• A summary of created / skipped rows is shown after import.', False),
    ]
    title_fill = PatternFill(start_color='1a6fd4', end_color='1a6fd4', fill_type='solid')
    for r, (text, bold) in enumerate(notes, 1):
        cell = ws_info.cell(row=r, column=1, value=text)
        cell.font = Font(bold=bold, color='FFFFFF' if r == 1 else '111111', size=11 if bold else 10)
        if r == 1:
            cell.fill = title_fill
            ws_info.row_dimensions[r].height = 26

    # Freeze header row on import sheet
    ws.freeze_panes = 'A2'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name='philasia_items_import_template.xlsx', as_attachment=True)


@main.route('/items/import', methods=['GET', 'POST'])
@login_required
@permission_required('manage_inventory')
def item_import():
    categories = Category.query.order_by('name').all()

    if request.method == 'POST':
        file = request.files.get('import_file')
        if not file or not file.filename:
            flash('Please select a file to import.', 'danger')
            return redirect(url_for('main.item_import'))
        if not _allowed_import(file.filename):
            flash('Unsupported file format. Please upload .xlsx, .xls, or .csv.', 'danger')
            return redirect(url_for('main.item_import'))

        ext = file.filename.rsplit('.', 1)[1].lower()
        created, skipped, errors = [], [], []

        try:
            if ext == 'csv':
                import csv, io
                stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
                reader = csv.DictReader(stream)
                rows = [r for r in reader]
            else:
                import openpyxl
                wb = openpyxl.load_workbook(file, data_only=True)
                ws = wb.active
                raw_headers = [str(c.value).strip().rstrip('*') if c.value else '' for c in ws[1]]
                # Normalize headers
                header_map = {h.lower(): i for i, h in enumerate(raw_headers)}
                def get_col(row, name):
                    idx = header_map.get(name.lower())
                    return str(row[idx].value).strip() if idx is not None and row[idx].value is not None else ''
                rows = [{'sku': get_col(r, 'sku'), 'name': get_col(r, 'name'),
                         'category': get_col(r, 'category'), 'unit': get_col(r, 'unit'),
                         'unit cost': get_col(r, 'unit cost'), 'reorder level': get_col(r, 'reorder level'),
                         'description': get_col(r, 'description')}
                        for r in ws.iter_rows(min_row=2) if any(c.value for c in r)]

            cat_map = {c.name.lower(): c.id for c in categories}

            for i, row in enumerate(rows, 2):
                sku = (row.get('sku') or row.get('SKU') or row.get('SKU*') or '').strip()
                name = (row.get('name') or row.get('Name') or row.get('Name*') or '').strip()
                unit = (row.get('unit') or row.get('Unit') or row.get('Unit*') or '').strip()

                if not sku or not name or not unit:
                    skipped.append({'row': i, 'reason': 'Missing SKU, Name, or Unit', 'sku': sku or '(blank)'})
                    continue

                if Item.query.filter_by(sku=sku).first():
                    skipped.append({'row': i, 'reason': f'SKU already exists', 'sku': sku})
                    continue

                cat_name = (row.get('category') or row.get('Category') or '').strip().lower()
                cat_id = cat_map.get(cat_name)

                try:
                    unit_cost = float(row.get('unit cost') or row.get('Unit Cost') or row.get('unit_cost') or 0)
                except (ValueError, TypeError):
                    unit_cost = 0
                try:
                    reorder = float(row.get('reorder level') or row.get('Reorder Level') or row.get('reorder_level') or 0)
                except (ValueError, TypeError):
                    reorder = 0

                desc = (row.get('description') or row.get('Description') or '').strip()

                item = Item(sku=sku, name=name, unit=unit, unit_cost=unit_cost,
                            reorder_level=reorder, description=desc,
                            category_id=cat_id, is_active=True)
                db.session.add(item)
                created.append({'sku': sku, 'name': name})

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash(f'Import failed: {str(e)}', 'danger')
            return redirect(url_for('main.item_import'))

        result = {'created': created, 'skipped': skipped}
        flash(f'{len(created)} items imported successfully. {len(skipped)} rows skipped.', 'success' if created else 'warning')
        return render_template('inventory/item_import_result.html', result=result)

    return render_template('inventory/item_import.html', categories=categories)


@main.route('/items/quick-add', methods=['POST'])
@login_required
@permission_required('manage_inventory')
def item_quick_add():
    """API endpoint for inline quick-add of multiple items."""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'success': False, 'error': 'Invalid data'}), 400

    cat_map = {c.name.lower(): c.id for c in Category.query.all()}
    created, errors = [], []

    for i, row in enumerate(data):
        sku = (row.get('sku') or '').strip()
        name = (row.get('name') or '').strip()
        unit = (row.get('unit') or '').strip()

        if not sku or not name or not unit:
            errors.append({'row': i + 1, 'error': 'SKU, Name, and Unit are required'})
            continue
        if Item.query.filter_by(sku=sku).first():
            errors.append({'row': i + 1, 'error': f'SKU "{sku}" already exists'})
            continue

        cat_name = (row.get('category') or '').strip().lower()
        try:
            item = Item(
                sku=sku, name=name, unit=unit,
                unit_cost=float(row.get('unit_cost') or 0),
                reorder_level=float(row.get('reorder_level') or 0),
                description=(row.get('description') or '').strip(),
                category_id=cat_map.get(cat_name),
                is_active=True
            )
            db.session.add(item)
            created.append({'sku': sku, 'name': name})
        except Exception as e:
            errors.append({'row': i + 1, 'error': str(e)})

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'created': created, 'errors': errors})


# ─── WAREHOUSES ───────────────────────────────────────────────────────────────

@main.route('/warehouses')
@login_required
def warehouse_list():
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    wh_data = []
    for wh in warehouses:
        items_count = db.session.query(func.count(Stock.id)).filter_by(
            warehouse_id=wh.id, location_type='warehouse').scalar() or 0
        total_value = db.session.query(func.sum(Stock.quantity * Item.unit_cost)).join(
            Item, Stock.item_id == Item.id).filter(
            Stock.warehouse_id == wh.id, Stock.location_type == 'warehouse').scalar() or 0
        wh_data.append({'wh': wh, 'items_count': items_count, 'total_value': float(total_value)})
    return render_template('inventory/warehouse_list.html', wh_data=wh_data)


@main.route('/warehouses/<int:wh_id>')
@login_required
def warehouse_detail(wh_id):
    wh = Warehouse.query.get_or_404(wh_id)
    stocks = Stock.query.filter_by(warehouse_id=wh_id, location_type='warehouse').all()
    return render_template('inventory/warehouse_detail.html', wh=wh, stocks=stocks)


@main.route('/warehouses/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouses')
def warehouse_create():
    form = WarehouseForm()
    if form.validate_on_submit():
        wh = Warehouse(name=form.name.data, location=form.location.data,
                       contact_person=form.contact_person.data,
                       contact_info=form.contact_info.data,
                       is_active=form.is_active.data)
        db.session.add(wh)
        db.session.commit()
        flash('Warehouse registered.', 'success')
        return redirect(url_for('main.warehouse_list'))
    return render_template('inventory/warehouse_form.html', form=form, title='New Warehouse')


@main.route('/warehouses/<int:wh_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouses')
def warehouse_edit(wh_id):
    wh = Warehouse.query.get_or_404(wh_id)
    form = WarehouseForm(obj=wh)
    if form.validate_on_submit():
        wh.name = form.name.data
        wh.location = form.location.data
        wh.contact_person = form.contact_person.data
        wh.contact_info = form.contact_info.data
        wh.is_active = form.is_active.data
        db.session.commit()
        flash('Warehouse updated.', 'success')
        return redirect(url_for('main.warehouse_detail', wh_id=wh_id))
    return render_template('inventory/warehouse_form.html', form=form, title='Edit Warehouse', wh=wh)


# ─── PROJECT SITES ────────────────────────────────────────────────────────────

@main.route('/sites')
@login_required
def site_list():
    if current_user.role in ('admin', 'project_manager', 'accounting', 'finance_manager'):
        sites = ProjectSite.query.order_by(ProjectSite.name).all()
    else:
        sites = current_user.managed_sites
    site_data = []
    for site in sites:
        items_count = db.session.query(func.count(Stock.id)).filter_by(
            site_id=site.id, location_type='site').scalar() or 0
        pending_req = Request.query.filter_by(site_id=site.id, status='pending').count()
        site_data.append({'site': site, 'items_count': items_count, 'pending_req': pending_req})
    return render_template('inventory/site_list.html', site_data=site_data)


@main.route('/sites/<int:site_id>')
@login_required
def site_detail(site_id):
    site = ProjectSite.query.get_or_404(site_id)
    stocks = Stock.query.filter_by(site_id=site_id, location_type='site').all()
    requests = Request.query.filter_by(site_id=site_id).order_by(desc(Request.created_at)).limit(10).all()
    movements = Movement.query.filter(
        (Movement.from_site_id == site_id) | (Movement.to_site_id == site_id)
    ).order_by(desc(Movement.date)).limit(15).all()
    return render_template('inventory/site_detail.html', site=site, stocks=stocks,
                           requests=requests, movements=movements)


@main.route('/sites/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_sites')
def site_create():
    form = ProjectSiteForm()
    if form.validate_on_submit():
        site = ProjectSite(
            name=form.name.data, address=form.address.data, client=form.client.data,
            start_date=form.start_date.data, end_date=form.end_date.data,
            status=form.status.data, contact_person=form.contact_person.data,
            contact_phone=form.contact_phone.data,
            budget=form.budget.data or 0, notes=form.notes.data)
        db.session.add(site)
        db.session.commit()
        flash('Project site created.', 'success')
        return redirect(url_for('main.site_list'))
    return render_template('inventory/site_form.html', form=form, title='New Project Site')


@main.route('/sites/<int:site_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_sites')
def site_edit(site_id):
    site = ProjectSite.query.get_or_404(site_id)
    form = ProjectSiteForm(obj=site)
    if form.validate_on_submit():
        site.name = form.name.data
        site.address = form.address.data
        site.client = form.client.data
        site.start_date = form.start_date.data
        site.end_date = form.end_date.data
        site.status = form.status.data
        site.contact_person = form.contact_person.data
        site.contact_phone = form.contact_phone.data
        site.budget = form.budget.data or 0
        site.notes = form.notes.data
        db.session.commit()
        flash('Project site updated.', 'success')
        return redirect(url_for('main.site_detail', site_id=site_id))
    return render_template('inventory/site_form.html', form=form, title='Edit Project Site', site=site)


# ─── MOVEMENTS ────────────────────────────────────────────────────────────────

@main.route('/movements')
@login_required
def movement_list():
    page = request.args.get('page', 1, type=int)
    mtype = request.args.get('type', '')
    q = Movement.query.order_by(desc(Movement.date))
    if mtype:
        q = q.filter_by(movement_type=mtype)
    movements = q.paginate(page=page, per_page=25)
    return render_template('inventory/movement_list.html', movements=movements,
                           mtype=mtype, movement_types=MOVEMENT_TYPES)


@main.route('/movements/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_movements')
def movement_create():
    form = MovementForm()
    if form.validate_on_submit():
        qty = float(form.quantity.data)
        mtype = form.movement_type.data
        from_type = form.from_location_type.data
        to_type = form.to_location_type.data
        from_wh = form.from_warehouse_id.data or None
        from_st = form.from_site_id.data or None
        to_wh = form.to_warehouse_id.data or None
        to_st = form.to_site_id.data or None

        # Validate source stock
        if from_type in ('warehouse', 'site'):
            q = Stock.query.filter_by(item_id=form.item_id.data, location_type=from_type)
            if from_type == 'warehouse':
                q = q.filter_by(warehouse_id=from_wh)
            else:
                q = q.filter_by(site_id=from_st)
            src_stock = q.first()
            if src_stock and float(src_stock.quantity) < qty:
                flash('Insufficient stock at the source location.', 'danger')
                return render_template('inventory/movement_form.html', form=form, title='New Transaction')

        movement = Movement(
            movement_type=mtype,
            item_id=form.item_id.data,
            quantity=qty,
            unit_cost=form.unit_cost.data or 0,
            from_location_type=from_type if from_type != 'none' else None,
            from_warehouse_id=from_wh if from_type == 'warehouse' else None,
            from_site_id=from_st if from_type == 'site' else None,
            to_location_type=to_type if to_type != 'none' else None,
            to_warehouse_id=to_wh if to_type == 'warehouse' else None,
            to_site_id=to_st if to_type == 'site' else None,
            reference=form.reference.data,
            notes=form.notes.data,
            user_id=current_user.id,
        )
        db.session.add(movement)

        # Update stock
        _update_stock(form.item_id.data, from_type,
                      from_wh if from_type == 'warehouse' else None,
                      from_st if from_type == 'site' else None, -qty)
        _update_stock(form.item_id.data, to_type,
                      to_wh if to_type == 'warehouse' else None,
                      to_st if to_type == 'site' else None, qty)

        db.session.commit()
        flash('Transaction posted successfully.', 'success')
        return redirect(url_for('main.movement_list'))
    return render_template('inventory/movement_form.html', form=form, title='New Transaction')


@main.route('/movements/<int:mov_id>')
@login_required
def movement_detail(mov_id):
    mov = Movement.query.get_or_404(mov_id)
    return render_template('inventory/movement_detail.html', mov=mov)


# ─── MATERIAL REQUESTS ────────────────────────────────────────────────────────

@main.route('/requests')
@login_required
def request_list():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    q = Request.query.order_by(desc(Request.created_at))
    if status_filter:
        q = q.filter_by(status=status_filter)
    if current_user.role in ('project_manager',):
        # Show requests for sites they manage
        site_ids = [s.id for s in current_user.managed_sites]
        q = q.filter(Request.site_id.in_(site_ids))
    elif current_user.role == 'viewer':
        q = q.filter_by(user_id=current_user.id)
    reqs = q.paginate(page=page, per_page=20)
    return render_template('inventory/request_list.html', reqs=reqs, status_filter=status_filter)


@main.route('/requests/new', methods=['GET', 'POST'])
@login_required
def request_create():
    form = RequestForm()
    if form.validate_on_submit():
        req = Request(site_id=form.site_id.data, user_id=current_user.id,
                      date_needed=form.date_needed.data, priority=form.priority.data,
                      notes=form.notes.data)
        db.session.add(req)
        db.session.commit()
        flash('Requisition submitted. Add items below.', 'success')
        return redirect(url_for('main.request_detail', req_id=req.id))
    return render_template('inventory/request_form.html', form=form, title='New Material Requisition')


@main.route('/requests/<int:req_id>', methods=['GET', 'POST'])
@login_required
def request_detail(req_id):
    req = Request.query.get_or_404(req_id)
    item_form = RequestItemForm()
    approve_form = ApproveRequestForm()
    reject_form = RejectRequestForm()

    if item_form.validate_on_submit() and 'item_id' in request.form:
        if req.status == 'pending':
            ri = RequestItem(request_id=req_id, item_id=item_form.item_id.data,
                             quantity_requested=item_form.quantity_requested.data,
                             notes=item_form.notes.data)
            db.session.add(ri)
            db.session.commit()
            flash('Item added to requisition.', 'success')
        else:
            flash('Cannot modify an approved or fulfilled requisition.', 'warning')
        return redirect(url_for('main.request_detail', req_id=req_id))
    return render_template('inventory/request_detail.html', req=req, item_form=item_form,
                           approve_form=approve_form, reject_form=reject_form)


@main.route('/requests/<int:req_id>/approve', methods=['POST'])
@login_required
@permission_required('approve_requests')
def request_approve(req_id):
    req = Request.query.get_or_404(req_id)
    if req.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('main.request_detail', req_id=req_id))
    req.status = 'approved'
    req.approved_by_id = current_user.id
    req.approved_at = datetime.utcnow()
    db.session.commit()
    flash('Requisition approved.', 'success')
    return redirect(url_for('main.request_detail', req_id=req_id))


@main.route('/requests/<int:req_id>/reject', methods=['POST'])
@login_required
@permission_required('approve_requests')
def request_reject(req_id):
    req = Request.query.get_or_404(req_id)
    reason = request.form.get('rejection_reason', '')
    if req.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('main.request_detail', req_id=req_id))
    req.status = 'rejected'
    req.rejection_reason = reason
    db.session.commit()
    flash('Requisition rejected.', 'warning')
    return redirect(url_for('main.request_detail', req_id=req_id))


@main.route('/requests/<int:req_id>/fulfill', methods=['POST'])
@login_required
@permission_required('manage_movements')
def request_fulfill(req_id):
    req = Request.query.get_or_404(req_id)
    if req.status not in ('approved', 'partial'):
        flash('Requisition must be approved before fulfillment.', 'warning')
        return redirect(url_for('main.request_detail', req_id=req_id))
    all_fulfilled = True
    for ri in req.items:
        remaining = float(ri.quantity_requested) - float(ri.quantity_delivered or 0)
        if remaining <= 0:
            continue
        # Check available stock across all warehouses
        avail = db.session.query(func.sum(Stock.quantity)).filter_by(
            item_id=ri.item_id, location_type='warehouse').scalar() or 0
        deliver_qty = min(float(avail), remaining)
        if deliver_qty <= 0:
            all_fulfilled = False
            continue
        # Find warehouse with stock
        src = Stock.query.filter_by(item_id=ri.item_id, location_type='warehouse').filter(
            Stock.quantity > 0).first()
        if not src:
            all_fulfilled = False
            continue
        mov = Movement(
            movement_type='transfer',
            item_id=ri.item_id, quantity=deliver_qty,
            from_location_type='warehouse', from_warehouse_id=src.warehouse_id,
            to_location_type='site', to_site_id=req.site_id,
            reference=f'REQ-{req.id}', notes=f'Fulfillment of Requisition #{req.id}',
            user_id=current_user.id, request_id=req_id)
        db.session.add(mov)
        _update_stock(ri.item_id, 'warehouse', src.warehouse_id, None, -deliver_qty)
        _update_stock(ri.item_id, 'site', None, req.site_id, deliver_qty)
        ri.quantity_delivered = float(ri.quantity_delivered or 0) + deliver_qty
        if float(ri.quantity_delivered) < float(ri.quantity_requested):
            all_fulfilled = False
    req.status = 'fulfilled' if all_fulfilled else 'partial'
    db.session.commit()
    flash('Requisition fulfilled.' if all_fulfilled else 'Partial fulfillment. Some items had insufficient stock.', 'success' if all_fulfilled else 'warning')
    return redirect(url_for('main.request_detail', req_id=req_id))


# ─── REPORTS ──────────────────────────────────────────────────────────────────

@main.route('/reports')
@login_required
def report_list():
    return render_template('reports/report_list.html')


@main.route('/reports/stock')
@login_required
def report_stock():
    form = ReportFilterForm(request.args, meta={'csrf': False})
    items = Item.query.filter_by(is_active=True).order_by(Item.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    sites = ProjectSite.query.all()

    stock_data = []
    for item in items:
        row = {'item': item, 'warehouses': {}, 'sites': {}, 'total': 0}
        for wh in warehouses:
            s = Stock.query.filter_by(item_id=item.id, warehouse_id=wh.id, location_type='warehouse').first()
            qty = float(s.quantity) if s else 0
            row['warehouses'][wh.id] = qty
            row['total'] += qty
        for site in sites:
            s = Stock.query.filter_by(item_id=item.id, site_id=site.id, location_type='site').first()
            qty = float(s.quantity) if s else 0
            row['sites'][site.id] = qty
            row['total'] += qty
        stock_data.append(row)
    return render_template('reports/stock_report.html', stock_data=stock_data,
                           warehouses=warehouses, sites=sites, items=items)


@main.route('/reports/movements')
@login_required
def report_movements():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    mtype = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    q = Movement.query.order_by(desc(Movement.date))
    if date_from:
        try:
            q = q.filter(Movement.date >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(Movement.date <= datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59))
        except ValueError:
            pass
    if mtype:
        q = q.filter_by(movement_type=mtype)

    total_qty = q.with_entities(func.sum(Movement.quantity)).order_by(None).scalar() or 0
    movements = q.paginate(page=page, per_page=30)
    return render_template('reports/movements_report.html', movements=movements,
                           movement_types=MOVEMENT_TYPES, mtype=mtype,
                           date_from=date_from, date_to=date_to, total_qty=float(total_qty))


@main.route('/reports/low-stock')
@login_required
def report_low_stock():
    alerts = []
    for item in Item.query.filter_by(is_active=True).all():
        total = item.total_stock()
        if total < float(item.reorder_level or 0):
            alerts.append({'item': item, 'current': total, 'threshold': float(item.reorder_level or 0)})
    alerts.sort(key=lambda x: x['current'] / max(x['threshold'], 0.001))
    return render_template('reports/low_stock_report.html', alerts=alerts)


# ─── USER MANAGEMENT ─────────────────────────────────────────────────────────

@main.route('/users')
@login_required
@permission_required('manage_users')
def user_list():
    users = User.query.order_by(User.username).all()
    return render_template('users/user_list.html', users=users)


@main.route('/users/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
            return render_template('users/user_form.html', form=form, title='New User')
        user = User(username=form.username.data, email=form.email.data,
                    full_name=form.full_name.data, role=form.role.data,
                    is_active=form.is_active.data)
        if form.password.data:
            user.set_password(form.password.data)
        else:
            user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created.', 'success')
        return redirect(url_for('main.user_list'))
    return render_template('users/user_form.html', form=form, title='New User')


@main.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing and existing.id != user_id:
            flash('Username already taken.', 'danger')
            return render_template('users/user_form.html', form=form, title='Edit User', user=user)
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('User updated.', 'success')
        return redirect(url_for('main.user_list'))
    return render_template('users/user_form.html', form=form, title='Edit User', user=user)


@main.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@permission_required('manage_users')
def user_deactivate(user_id):
    if user_id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('main.user_list'))
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('main.user_list'))


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('users/profile.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('users/profile.html', form=form)


# ─── INVENTORY OVERVIEW (Stocks) ──────────────────────────────────────────────

@main.route('/inventory')
@login_required
def inventory_overview():
    stocks = Stock.query.filter(Stock.quantity > 0).all()
    return render_template('inventory/inventory_overview.html', stocks=stocks)


# ─── API (JSON) ───────────────────────────────────────────────────────────────

@main.route('/api/stock/<int:item_id>')
@login_required
def api_item_stock(item_id):
    stocks = Stock.query.filter_by(item_id=item_id).all()
    return jsonify([{
        'location_type': s.location_type,
        'location': s.location_name(),
        'quantity': float(s.quantity),
    } for s in stocks])
