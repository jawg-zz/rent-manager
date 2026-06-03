from datetime import date, timedelta
import random


def seed_demo_data(db, User, Property, Unit, Tenant, Lease, Payment):
    """Seed realistic demo data for Kenyan property market"""

    # Create landlord user
    landlord = User(email='landlord@demo.com', full_name='James Mwangi', phone='0712345678', role='landlord')
    landlord.set_password('demo123')
    db.session.add(landlord)
    db.session.flush()

    # Create properties
    props_data = [
        ('Sunrise Apartments', 'Kenyatta Avenue, Nairobi', 'Nairobi', 'apartment'),
        ('Westlands Heights', 'Waiyaki Way, Westlands', 'Nairobi', 'apartment'),
        ('Coast View Villas', 'Nyali Road, Mombasa', 'Mombasa', 'house'),
    ]
    properties = []
    for name, addr, city, ptype in props_data:
        p = Property(owner_id=landlord.id, name=name, address=addr, city=city, property_type=ptype)
        db.session.add(p)
        properties.append(p)
    db.session.flush()

    # Create units
    units = []
    unit_configs = [
        # Sunrise Apartments — 5 units
        (properties[0], [('A1', 1, 2, 1, 45, 25000), ('A2', 1, 1, 1, 30, 18000),
                         ('B1', 2, 2, 1, 50, 30000), ('B2', 2, 1, 1, 28, 16000),
                         ('C1', 3, 3, 2, 75, 45000)]),
        # Westlands Heights — 4 units
        (properties[1], [('1A', 1, 2, 2, 55, 35000), ('1B', 1, 1, 1, 32, 22000),
                         ('2A', 2, 2, 1, 48, 28000), ('2B', 2, 3, 2, 70, 50000)]),
        # Coast View — 3 villas
        (properties[2], [('Villa 1', None, 3, 2, 120, 65000), ('Villa 2', None, 4, 3, 150, 85000),
                         ('Villa 3', None, 2, 1, 80, 45000)]),
    ]
    for prop, u_list in unit_configs:
        for num, floor, beds, baths, sqm, rent in u_list:
            u = Unit(property_id=prop.id, unit_number=num, floor=floor, bedrooms=beds,
                    bathrooms=baths, sqm=sqm, monthly_rent=rent, status='vacant')
            db.session.add(u)
            units.append(u)
    db.session.flush()

    # Create tenants
    tenants_data = [
        ('Grace Wanjiku', '0722123456', 'grace.w@email.com', 'national_id', '34567890', 'Safaricom'),
        ('Peter Ochieng', '0733987654', 'peter.o@email.com', 'national_id', '23456789', 'KCB Bank'),
        ('Fatima Hassan', '0712456789', 'fatima.h@email.com', 'national_id', '45678901', 'Equity Bank'),
        ('David Kamau', '0745678901', 'david.k@email.com', 'national_id', '56789012', 'KEMSA'),
        ('Sarah Akinyi', '0723567890', 'sarah.a@email.com', 'passport', 'A1234567', 'UN Kenya'),
        ('John Maina', '0710987654', 'john.m@email.com', 'national_id', '67890123', 'G4S Security'),
        ('Mary Njeri', '0734123098', 'mary.n@email.com', 'national_id', '78901234', 'Safaricom'),
        ('Ali Mohamed', '0726789012', 'ali.m@email.com', 'alien_id', 'ALI901234', 'Mombasa County'),
        ('Esther Wambui', '0715432109', 'esther.w@email.com', 'national_id', '89012345', 'Equity Bank'),
        ('Michael Odhiambo', '0738901234', 'michael.o@email.com', 'national_id', '90123456', 'Kenya Airways'),
    ]
    tenants = []
    for name, phone, email, id_type, id_num, employer in tenants_data:
        t = Tenant(full_name=name, phone=phone, email=email, id_type=id_type,
                  id_number=id_num, employer=employer)
        db.session.add(t)
        tenants.append(t)
    db.session.flush()

    # Create leases (8 active)
    today = date.today()
    leases_data = [
        # tenant_idx, unit_idx, months_back, months_forward, rent, deposit
        (0, 0, 6, 12, 25000, 50000),   # Grace → A1
        (1, 2, 4, 12, 30000, 60000),   # Peter → B1
        (2, 5, 8, 6, 35000, 70000),    # Fatima → 1A
        (3, 7, 2, 12, 50000, 100000),  # David → 2B
        (4, 4, 10, 8, 45000, 90000),   # Sarah → C1
        (5, 9, 3, 12, 65000, 130000),  # John → Villa 1
        (7, 10, 5, 6, 85000, 170000),  # Ali → Villa 2
        (8, 1, 1, 12, 18000, 36000),   # Esther → A2
    ]
    leases = []
    for t_idx, u_idx, mb, mf, rent, deposit in leases_data:
        start = today - timedelta(days=mb * 30)
        end = today + timedelta(days=mf * 30)
        l = Lease(tenant_id=tenants[t_idx].id, unit_id=units[u_idx].id,
                 start_date=start, end_date=end, monthly_rent=rent,
                 deposit_amount=deposit, deposit_paid=True, payment_day=1, status='active')
        db.session.add(l)
        leases.append(l)
        # Update unit status
        units[u_idx].status = 'occupied'
    db.session.flush()

    # Create payments (15 total, some with gaps for arrears)
    payments_data = [
        # lease_idx, months_back, amount, method
        (0, 1, 25000, 'mpesa'),
        (0, 2, 25000, 'mpesa'),
        (0, 3, 25000, 'mpesa'),
        (0, 4, 25000, 'mpesa'),
        (1, 1, 30000, 'mpesa'),
        (1, 2, 30000, 'bank'),
        (2, 1, 35000, 'mpesa'),
        (2, 2, 35000, 'mpesa'),
        (2, 3, 35000, 'mpesa'),
        (3, 1, 50000, 'mpesa'),
        (4, 1, 45000, 'cash'),
        (4, 2, 45000, 'mpesa'),
        (5, 1, 65000, 'mpesa'),
        (6, 1, 85000, 'mpesa'),
        (6, 2, 85000, 'bank'),
    ]
    for l_idx, mb, amount, method in payments_data:
        l = leases[l_idx]
        p_date = today - timedelta(days=mb * 30)
        period_start = date(p_date.year, p_date.month, 1)
        days_in_month = 30  # simplified
        period_end = date(p_date.year, p_date.month, min(p_date.day + days_in_month - 1, 28))

        receipt = f'QGH{random.randint(100000, 999999)}' if method == 'mpesa' else ''
        p = Payment(lease_id=l.id, amount=amount, payment_date=p_date, payment_method=method,
                   mpesa_receipt=receipt, period_start=period_start, period_end=period_end,
                   status='confirmed')
        db.session.add(p)

    db.session.commit()
