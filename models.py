import os
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='landlord')  # landlord, manager, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    properties = db.relationship('Property', backref='owner', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Property(db.Model):
    __tablename__ = 'properties'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(80), nullable=False, default='Nairobi')
    property_type = db.Column(db.String(30), nullable=False, default='apartment')  # apartment, house, office, commercial
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    units = db.relationship('Unit', backref='property', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_units(self):
        return self.units.count()

    @property
    def occupied_units(self):
        return self.units.filter_by(status='occupied').count()

    @property
    def vacant_units(self):
        return self.units.filter_by(status='vacant').count()

    @property
    def monthly_revenue(self):
        total = 0
        for unit in self.units.filter_by(status='occupied'):
            lease = unit.active_lease
            if lease:
                total += lease.monthly_rent
        return total


class Unit(db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False, index=True)
    unit_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer)
    bedrooms = db.Column(db.Integer, default=1)
    bathrooms = db.Column(db.Integer, default=1)
    sqm = db.Column(db.Float)
    monthly_rent = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='vacant')  # vacant, occupied, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leases = db.relationship('Lease', backref='unit', lazy='dynamic')
    maintenance_requests = db.relationship('MaintenanceRequest', backref='unit', lazy='dynamic')

    @property
    def active_lease(self):
        return self.leases.filter_by(status='active').first()

    @property
    def current_tenant(self):
        lease = self.active_lease
        return lease.tenant if lease else None


class Tenant(db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    id_type = db.Column(db.String(30), default='national_id')  # national_id, passport, alien_id
    id_number = db.Column(db.String(30))
    employer = db.Column(db.String(120))
    emergency_contact = db.Column(db.String(120))
    emergency_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leases = db.relationship('Lease', backref='tenant', lazy='dynamic')

    @property
    def active_lease(self):
        return self.leases.filter_by(status='active').first()


class Lease(db.Model):
    __tablename__ = 'leases'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    monthly_rent = db.Column(db.Float, nullable=False)
    deposit_amount = db.Column(db.Float, default=0)
    deposit_paid = db.Column(db.Boolean, default=False)
    payment_day = db.Column(db.Integer, default=1)  # day of month rent is due
    status = db.Column(db.String(20), nullable=False, default='active')  # active, expired, terminated
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship('Payment', backref='lease', lazy='dynamic')

    @property
    def is_overdue(self):
        if self.status != 'active':
            return False
        today = date.today()
        last_payment = self.payments.order_by(Payment.period_end.desc()).first()
        if not last_payment:
            # No payments at all — overdue if past start_date
            return today > self.start_date
        # Overdue if current month not covered
        next_period_start = date(today.year, today.month, self.payment_day)
        if today.day >= self.payment_day:
            next_period_start = date(today.year, today.month, self.payment_day)
        else:
            # Haven't reached payment day this month yet
            return False
        return last_payment.period_end < next_period_start

    @property
    def months_owed(self):
        if self.status != 'active':
            return 0
        today = date.today()
        last_payment = self.payments.order_by(Payment.period_end.desc()).first()
        if not last_payment:
            months = (today.year - self.start_date.year) * 12 + today.month - self.start_date.month
            return max(0, months)
        months = (today.year - last_payment.period_end.year) * 12 + today.month - last_payment.period_end.month
        return max(0, months - 1)  # -1 because current month may not be due yet

    @property
    def total_owed(self):
        return self.months_owed * self.monthly_rent

    @property
    def total_paid(self):
        return sum(p.amount for p in self.payments.filter_by(status='confirmed').all())

    @property
    def property_name(self):
        return self.unit.property.name if self.unit else ''


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey('leases.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    payment_method = db.Column(db.String(20), nullable=False, default='mpesa')  # mpesa, bank, cash
    mpesa_receipt = db.Column(db.String(30))
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='confirmed')  # confirmed, pending, disputed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MaintenanceRequest(db.Model):
    __tablename__ = 'maintenance_requests'
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False, index=True)
    reported_by = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)


class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(20), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


def log_audit(user_id, action, entity, entity_id=None, details=None):
    from flask import request
    entry = AuditLog(
        user_id=user_id, action=action, entity=entity,
        entity_id=entity_id, details=details,
        ip_address=request.remote_addr if request else None
    )
    db.session.add(entry)
    db.session.flush()
