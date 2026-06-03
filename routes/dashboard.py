from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime
from models import db, Property, Unit, Tenant, Lease, Payment

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    uid = current_user.id

    # Property stats
    total_properties = Property.query.filter_by(owner_id=uid).count()
    total_units = Unit.query.join(Property).filter(Property.owner_id == uid).count()
    occupied_units = db.session.query(func.count(Unit.id)).join(Property).filter(
        Property.owner_id == uid, Unit.status == 'occupied').scalar() or 0
    vacant_units = total_units - occupied_units
    occupancy_rate = round((occupied_units / total_units * 100) if total_units > 0 else 0, 1)

    # Financial stats
    active_leases = db.session.query(Lease).join(Unit).join(Property).filter(
        Property.owner_id == uid, Lease.status == 'active').all()

    monthly_expected = sum(l.monthly_rent for l in active_leases)
    total_owed = sum(l.total_owed for l in active_leases)
    overdue_leases = [l for l in active_leases if l.is_overdue]

    # Total collected this month
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)

    payments_this_month = db.session.query(func.sum(Payment.amount)).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == uid,
        Payment.payment_date >= month_start,
        Payment.payment_date < month_end,
        Payment.status == 'confirmed'
    ).scalar() or 0

    # Recent payments
    recent_payments = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == uid
    ).order_by(Payment.created_at.desc()).limit(5).all()

    # Monthly revenue chart (last 6 months)
    chart_labels = []
    chart_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        ms = date(y, m, 1)
        me = date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)
        rev = db.session.query(func.sum(Payment.amount)).join(Lease).join(Unit).join(Property).filter(
            Property.owner_id == uid,
            Payment.payment_date >= ms,
            Payment.payment_date < me,
            Payment.status == 'confirmed'
        ).scalar() or 0
        chart_labels.append(ms.strftime('%b %Y'))
        chart_data.append(float(rev))

    return render_template('dashboard.html',
        total_properties=total_properties,
        total_units=total_units,
        occupied_units=occupied_units,
        vacant_units=vacant_units,
        occupancy_rate=occupancy_rate,
        monthly_expected=monthly_expected,
        total_owed=total_owed,
        payments_this_month=payments_this_month,
        overdue_count=len(overdue_leases),
        overdue_leases=overdue_leases[:5],
        recent_payments=recent_payments,
        chart_labels=chart_labels,
        chart_data=chart_data
    )
