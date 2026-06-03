from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime
from calendar import monthrange
from models import db, Payment, Lease, Unit, Property, log_audit

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/')
@login_required
def list_payments():
    method = request.args.get('method', 'all')
    q = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id
    )
    if method != 'all':
        q = q.filter(Payment.payment_method == method)
    payments = q.order_by(Payment.payment_date.desc()).limit(100).all()
    return render_template('payments/list.html', payments=payments, current_method=method)


@payments_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    lease_id = request.args.get('lease_id', type=int)
    leases = db.session.query(Lease).join(Unit).join(Property).filter(
        Property.owner_id == current_user.id, Lease.status == 'active'
    ).all()

    if request.method == 'POST':
        lid = request.form.get('lease_id', type=int)
        amount = request.form.get('amount', type=float)
        payment_date = request.form.get('payment_date')
        method = request.form.get('payment_method', 'mpesa')
        receipt = request.form.get('mpesa_receipt', '').strip()
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        notes = request.form.get('notes', '').strip()

        if not lid or not amount or not payment_date or not period_start or not period_end:
            flash('All fields are required', 'danger')
            return render_template('payments/form.html', leases=leases, selected_lease_id=lid, payment=None)

        payment = Payment(
            lease_id=lid, amount=amount,
            payment_date=datetime.strptime(payment_date, '%Y-%m-%d').date(),
            payment_method=method, mpesa_receipt=receipt,
            period_start=datetime.strptime(period_start, '%Y-%m-%d').date(),
            period_end=datetime.strptime(period_end, '%Y-%m-%d').date(),
            status='confirmed', notes=notes
        )
        db.session.add(payment)
        db.session.commit()
        lease = Lease.query.get(lid)
        log_audit(current_user.id, 'create', 'payment', payment.id,
                 f'Payment: KES {amount:,.0f} from {lease.tenant.full_name if lease else "N/A"}')
        db.session.commit()
        flash(f'Payment of KES {amount:,.0f} recorded', 'success')
        return redirect(url_for('payments.list_payments'))

    return render_template('payments/form.html', leases=leases, selected_lease_id=lease_id, payment=None)


@payments_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    payment = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Payment.id == id, Property.owner_id == current_user.id
    ).first_or_404()

    if request.method == 'POST':
        payment.amount = request.form.get('amount', payment.amount, type=float)
        payment.payment_date = datetime.strptime(request.form.get('payment_date', str(payment.payment_date)), '%Y-%m-%d').date()
        payment.payment_method = request.form.get('payment_method', payment.payment_method)
        payment.mpesa_receipt = request.form.get('mpesa_receipt', '').strip()
        payment.period_start = datetime.strptime(request.form.get('period_start', str(payment.period_start)), '%Y-%m-%d').date()
        payment.period_end = datetime.strptime(request.form.get('period_end', str(payment.period_end)), '%Y-%m-%d').date()
        payment.status = request.form.get('status', payment.status)
        payment.notes = request.form.get('notes', '').strip()
        db.session.commit()
        log_audit(current_user.id, 'update', 'payment', payment.id, f'Updated payment #{payment.id}')
        db.session.commit()
        flash('Payment updated', 'success')
        return redirect(url_for('payments.list_payments'))

    return render_template('payments/form.html', leases=[], selected_lease_id=payment.lease_id, payment=payment)


@payments_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    payment = db.session.query(Payment).join(Lease).join(Unit).join(Property).filter(
        Payment.id == id, Property.owner_id == current_user.id
    ).first_or_404()
    db.session.delete(payment)
    db.session.commit()
    log_audit(current_user.id, 'delete', 'payment', id, f'Deleted payment #{id}')
    db.session.commit()
    flash('Payment deleted', 'success')
    return redirect(url_for('payments.list_payments'))
