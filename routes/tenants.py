from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Tenant, Lease, log_audit

tenants_bp = Blueprint('tenants', __name__)


@tenants_bp.route('/')
@login_required
def list_tenants():
    tenants = Tenant.query.join(Lease).join('unit', 'property').filter(
        # All tenants who have leases on this user's properties
    ).distinct().all() if False else []  # simplified below

    # Get tenants linked to this user's properties via leases
    from models import Unit, Property
    from sqlalchemy import select
    tenant_ids = select(Tenant.id).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    ).distinct().subquery()
    tenants = Tenant.query.filter(Tenant.id.in_(select(tenant_ids.c.id))).order_by(Tenant.full_name).all()

    return render_template('tenants/list.html', tenants=tenants)


@tenants_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        id_type = request.form.get('id_type', 'national_id')
        id_number = request.form.get('id_number', '').strip()
        employer = request.form.get('employer', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()
        emergency_phone = request.form.get('emergency_phone', '').strip()

        if not full_name or not phone:
            flash('Name and phone are required', 'danger')
            return render_template('tenants/form.html', tenant=None)

        tenant = Tenant(full_name=full_name, phone=phone, email=email,
                       id_type=id_type, id_number=id_number, employer=employer,
                       emergency_contact=emergency_contact, emergency_phone=emergency_phone)
        db.session.add(tenant)
        db.session.commit()
        log_audit(current_user.id, 'create', 'tenant', tenant.id, f'Added: {tenant.full_name}')
        db.session.commit()
        flash(f'Tenant "{tenant.full_name}" added', 'success')
        return redirect(url_for('tenants.list_tenants'))
    return render_template('tenants/form.html', tenant=None)


@tenants_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    tenant = Tenant.query.get_or_404(id)
    if request.method == 'POST':
        tenant.full_name = request.form.get('full_name', tenant.full_name).strip()
        tenant.phone = request.form.get('phone', tenant.phone).strip()
        tenant.email = request.form.get('email', '').strip()
        tenant.id_type = request.form.get('id_type', tenant.id_type)
        tenant.id_number = request.form.get('id_number', '').strip()
        tenant.employer = request.form.get('employer', '').strip()
        tenant.emergency_contact = request.form.get('emergency_contact', '').strip()
        tenant.emergency_phone = request.form.get('emergency_phone', '').strip()
        db.session.commit()
        log_audit(current_user.id, 'update', 'tenant', tenant.id, f'Updated: {tenant.full_name}')
        db.session.commit()
        flash('Tenant updated', 'success')
        return redirect(url_for('tenants.list_tenants'))
    return render_template('tenants/form.html', tenant=tenant)


@tenants_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    tenant = Tenant.query.get_or_404(id)
    name = tenant.full_name
    db.session.delete(tenant)
    db.session.commit()
    log_audit(current_user.id, 'delete', 'tenant', id, f'Deleted: {name}')
    db.session.commit()
    flash(f'Tenant "{name}" deleted', 'success')
    return redirect(url_for('tenants.list_tenants'))
