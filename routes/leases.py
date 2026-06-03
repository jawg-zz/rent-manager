from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime
from models import db, Lease, Tenant, Unit, Property, log_audit

leases_bp = Blueprint('leases', __name__)


@leases_bp.route('/')
@login_required
def list_leases():
    status = request.args.get('status', 'all')
    q = db.session.query(Lease).join(Unit).join(Property).filter(Property.owner_id == current_user.id)
    if status != 'all':
        q = q.filter(Lease.status == status)
    leases = q.order_by(Lease.start_date.desc()).all()
    return render_template('leases/list.html', leases=leases, current_status=status)


@leases_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Get available units (vacant or selected for new lease)
    units = db.session.query(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    ).order_by(Property.name, Unit.unit_number).all()

    # Get all tenants (user may need to create new ones)
    tenants = Tenant.query.join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    ).distinct().all()
    # Also include tenants not yet leased (from previous additions)
    all_tenants = Tenant.query.order_by(Tenant.full_name).all()

    if request.method == 'POST':
        tenant_id = request.form.get('tenant_id', type=int)
        unit_id = request.form.get('unit_id', type=int)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        monthly_rent = request.form.get('monthly_rent', type=float)
        deposit_amount = request.form.get('deposit_amount', 0, type=float)
        deposit_paid = request.form.get('deposit_paid') == 'on'
        payment_day = request.form.get('payment_day', 1, type=int)
        notes = request.form.get('notes', '').strip()

        if not tenant_id or not unit_id or not start_date or not end_date or not monthly_rent:
            flash('Tenant, unit, dates and rent are required', 'danger')
            return render_template('leases/form.html', lease=None, units=units, tenants=all_tenants)

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        if end <= start:
            flash('End date must be after start date', 'danger')
            return render_template('leases/form.html', lease=None, units=units, tenants=all_tenants)

        lease = Lease(tenant_id=tenant_id, unit_id=unit_id, start_date=start, end_date=end,
                     monthly_rent=monthly_rent, deposit_amount=deposit_amount,
                     deposit_paid=deposit_paid, payment_day=payment_day, notes=notes,
                     status='active')
        db.session.add(lease)

        # Update unit status
        unit = Unit.query.get(unit_id)
        if unit:
            unit.status = 'occupied'

        db.session.commit()
        log_audit(current_user.id, 'create', 'lease', lease.id,
                 f'Lease: {lease.tenant.full_name} → {unit.unit_number} @ {unit.property.name}')
        db.session.commit()
        flash('Lease created', 'success')
        return redirect(url_for('leases.view', id=lease.id))

    return render_template('leases/form.html', lease=None, units=units, tenants=all_tenants)


@leases_bp.route('/<int:id>')
@login_required
def view(id):
    lease = db.session.query(Lease).join(Unit).join(Property).filter(
        Lease.id == id, Property.owner_id == current_user.id
    ).first_or_404()
    payments = lease.payments.order_by(Payment.payment_date.desc()).all()
    return render_template('leases/view.html', lease=lease, payments=payments)


@leases_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    lease = db.session.query(Lease).join(Unit).join(Property).filter(
        Lease.id == id, Property.owner_id == current_user.id
    ).first_or_404()

    units = db.session.query(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    ).order_by(Property.name, Unit.unit_number).all()
    all_tenants = Tenant.query.order_by(Tenant.full_name).all()

    if request.method == 'POST':
        lease.tenant_id = request.form.get('tenant_id', lease.tenant_id, type=int)
        new_unit_id = request.form.get('unit_id', lease.unit_id, type=int)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        lease.monthly_rent = request.form.get('monthly_rent', lease.monthly_rent, type=float)
        lease.deposit_amount = request.form.get('deposit_amount', lease.deposit_amount, type=float)
        lease.deposit_paid = request.form.get('deposit_paid') == 'on'
        lease.payment_day = request.form.get('payment_day', lease.payment_day, type=int)
        lease.notes = request.form.get('notes', '').strip()
        lease.status = request.form.get('status', lease.status)

        if start_date:
            lease.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            lease.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Handle unit change
        if new_unit_id != lease.unit_id:
            old_unit = Unit.query.get(lease.unit_id)
            new_unit = Unit.query.get(new_unit_id)
            if old_unit and old_unit.status == 'occupied':
                old_unit.status = 'vacant'
            lease.unit_id = new_unit_id
            if new_unit:
                new_unit.status = 'occupied'

        # If lease terminated/expired, free the unit
        if lease.status in ('terminated', 'expired'):
            unit = Unit.query.get(lease.unit_id)
            if unit:
                unit.status = 'vacant'

        db.session.commit()
        log_audit(current_user.id, 'update', 'lease', lease.id, f'Updated lease #{lease.id}')
        db.session.commit()
        flash('Lease updated', 'success')
        return redirect(url_for('leases.view', id=lease.id))

    return render_template('leases/form.html', lease=lease, units=units, tenants=all_tenants)


@leases_bp.route('/<int:id>/terminate', methods=['POST'])
@login_required
def terminate(id):
    lease = db.session.query(Lease).join(Unit).join(Property).filter(
        Lease.id == id, Property.owner_id == current_user.id
    ).first_or_404()
    lease.status = 'terminated'
    unit = Unit.query.get(lease.unit_id)
    if unit:
        unit.status = 'vacant'
    db.session.commit()
    log_audit(current_user.id, 'update', 'lease', lease.id, f'Terminated lease #{lease.id}')
    db.session.commit()
    flash('Lease terminated', 'success')
    return redirect(url_for('leases.list_leases'))


# Need Payment import for view route
from models import Payment
