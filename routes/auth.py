from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import db, User, log_audit

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            log_audit(user.id, 'login', 'user', user.id, f'{user.email} logged in')
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid email or password', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            flash('Name, email and password are required', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('auth/register.html')

        user = User(full_name=full_name, email=email, phone=phone, role='landlord')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_audit(user.id, 'create', 'user', user.id, f'Registered: {user.email}')
        db.session.commit()
        login_user(user)
        flash('Welcome! Your account has been created.', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_audit(None, 'logout', 'user', None, 'User logged out')
    db.session.commit()
    logout_user()
    return redirect(url_for('auth.login'))


# Need import for login_user in register
from flask_login import login_user as _login_user
