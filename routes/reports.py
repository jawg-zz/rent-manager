import csv
import io
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from datetime import date
from models import db, Lease, Unit, Property, Payment, Tenant

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/rent-roll')
@login_required
def rent_roll():
    """Who owes what — current arrears by property/unit"""
    properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.name).all()
    return render_template('reports/rent_roll.html', properties=properties, report_type='rent_roll')


@reports_bp.route('/payment-history')
@login_required
def payment_history():
    """All payments with filters"""
    prop_id = request.args.get('property_id', type=int)
    q = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    )
    if prop_id:
        q = q.filter(Property.id == prop_id)
    payments = q.order_by(Payment.payment_date.desc()).all()

    properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.name).all()
    return render_template('reports/rent_roll.html', payments=payments, properties=properties,
                          report_type='payment_history', selected_property=prop_id)


@reports_bp.route('/arrears')
@login_required
def arrears():
    """Overdue payments report"""
    active_leases = db.session.query(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id, Lease.status == 'active'
    ).all()
    overdue = [l for l in active_leases if l.is_overdue]
    return render_template('reports/rent_roll.html', overdue=overdue, report_type='arrears')


@reports_bp.route('/export/payments')
@login_required
def export_payments():
    """CSV export of all payments"""
    payments = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    ).order_by(Payment.payment_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Tenant', 'Property', 'Unit', 'Amount', 'Method', 'Receipt', 'Period Start', 'Period End', 'Status'])
    for p in payments:
        writer.writerow([
            p.payment_date.strftime('%Y-%m-%d') if p.payment_date else '',
            p.lease.tenant.full_name if p.lease and p.lease.tenant else '',
            p.lease.unit.property.name if p.lease and p.lease.unit and p.lease.unit.property else '',
            p.lease.unit.unit_number if p.lease and p.lease.unit else '',
            p.amount,
            p.payment_method,
            p.mpesa_receipt or '',
            p.period_start.strftime('%Y-%m-%d') if p.period_start else '',
            p.period_end.strftime('%Y-%m-%d') if p.period_end else '',
            p.status
        ])
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=payments_{date.today().strftime("%Y%m%d")}.csv'})


@reports_bp.route('/export/rent-roll')
@login_required
def export_rent_roll():
    """CSV export of rent roll"""
    leases = db.session.query(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id, Lease.status == 'active'
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Property', 'Unit', 'Tenant', 'Phone', 'Monthly Rent', 'Lease Start', 'Lease End', 'Months Owed', 'Total Owed'])
    for l in leases:
        writer.writerow([
            l.unit.property.name if l.unit and l.unit.property else '',
            l.unit.unit_number if l.unit else '',
            l.tenant.full_name if l.tenant else '',
            l.tenant.phone if l.tenant else '',
            l.monthly_rent,
            l.start_date.strftime('%Y-%m-%d') if l.start_date else '',
            l.end_date.strftime('%Y-%m-%d') if l.end_date else '',
            l.months_owed,
            l.total_owed
        ])
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=rent_roll_{date.today().strftime("%Y%m%d")}.csv'})
