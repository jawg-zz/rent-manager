from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Property, Unit, log_audit

properties_bp = Blueprint('properties', __name__)


@properties_bp.route('/')
@login_required
def list_properties():
    props = Property.query.filter_by(owner_id=current_user.id).order_by(Property.name).all()
    return render_template('properties/list.html', properties=props)


@properties_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        prop_type = request.form.get('property_type', 'apartment')
        description = request.form.get('description', '').strip()

        if not name or not address:
            flash('Name and address are required', 'danger')
            return render_template('properties/form.html', property=None)

        prop = Property(owner_id=current_user.id, name=name, address=address,
                       city=city or 'Nairobi', property_type=prop_type, description=description)
        db.session.add(prop)
        db.session.commit()
        log_audit(current_user.id, 'create', 'property', prop.id, f'Added: {prop.name}')
        db.session.commit()
        flash(f'Property "{prop.name}" added', 'success')
        return redirect(url_for('properties.view', id=prop.id))
    return render_template('properties/form.html', property=None)


@properties_bp.route('/<int:id>')
@login_required
def view(id):
    prop = Property.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    units = prop.units.order_by(Unit.unit_number).all()
    return render_template('properties/view.html', property=prop, units=units)


@properties_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    prop = Property.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    if request.method == 'POST':
        prop.name = request.form.get('name', prop.name).strip()
        prop.address = request.form.get('address', prop.address).strip()
        prop.city = request.form.get('city', prop.city).strip()
        prop.property_type = request.form.get('property_type', prop.property_type)
        prop.description = request.form.get('description', '').strip()
        db.session.commit()
        log_audit(current_user.id, 'update', 'property', prop.id, f'Updated: {prop.name}')
        db.session.commit()
        flash('Property updated', 'success')
        return redirect(url_for('properties.view', id=prop.id))
    return render_template('properties/form.html', property=prop)


@properties_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    prop = Property.query.filter_by(id=id, owner_id=current_user.id).first_or_404()
    name = prop.name
    db.session.delete(prop)
    db.session.commit()
    log_audit(current_user.id, 'delete', 'property', id, f'Deleted: {name}')
    db.session.commit()
    flash(f'Property "{name}" deleted', 'success')
    return redirect(url_for('properties.list_properties'))


# Unit routes
@properties_bp.route('/<int:prop_id>/units/add', methods=['POST'])
@login_required
def add_unit(prop_id):
    prop = Property.query.filter_by(id=prop_id, owner_id=current_user.id).first_or_404()
    unit_number = request.form.get('unit_number', '').strip()
    if not unit_number:
        flash('Unit number is required', 'danger')
        return redirect(url_for('properties.view', id=prop_id))

    unit = Unit(
        property_id=prop_id,
        unit_number=unit_number,
        floor=request.form.get('floor', type=int),
        bedrooms=request.form.get('bedrooms', 1, type=int),
        bathrooms=request.form.get('bathrooms', 1, type=int),
        sqm=request.form.get('sqm', type=float),
        monthly_rent=request.form.get('monthly_rent', 0, type=float),
        status='vacant'
    )
    db.session.add(unit)
    db.session.commit()
    log_audit(current_user.id, 'create', 'unit', unit.id, f'Added unit {unit.unit_number} to {prop.name}')
    db.session.commit()
    flash(f'Unit {unit.unit_number} added', 'success')
    return redirect(url_for('properties.view', id=prop_id))


@properties_bp.route('/units/<int:unit_id>/edit', methods=['POST'])
@login_required
def edit_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    prop = Property.query.filter_by(id=unit.property_id, owner_id=current_user.id).first_or_404()
    unit.unit_number = request.form.get('unit_number', unit.unit_number).strip()
    unit.floor = request.form.get('floor', unit.floor, type=int)
    unit.bedrooms = request.form.get('bedrooms', unit.bedrooms, type=int)
    unit.bathrooms = request.form.get('bathrooms', unit.bathrooms, type=int)
    unit.sqm = request.form.get('sqm', unit.sqm, type=float)
    unit.monthly_rent = request.form.get('monthly_rent', unit.monthly_rent, type=float)
    unit.status = request.form.get('status', unit.status)
    db.session.commit()
    log_audit(current_user.id, 'update', 'unit', unit.id, f'Updated unit {unit.unit_number}')
    db.session.commit()
    flash('Unit updated', 'success')
    return redirect(url_for('properties.view', id=prop.id))


@properties_bp.route('/units/<int:unit_id>/delete', methods=['POST'])
@login_required
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    prop = Property.query.filter_by(id=unit.property_id, owner_id=current_user.id).first_or_404()
    num = unit.unit_number
    db.session.delete(unit)
    db.session.commit()
    log_audit(current_user.id, 'delete', 'unit', unit_id, f'Deleted unit {num}')
    db.session.commit()
    flash(f'Unit {num} deleted', 'success')
    return redirect(url_for('properties.view', id=prop.id))
