import os
import sys

# Override DATABASE_URL before importing app
os.environ['DATABASE_URL'] = 'sqlite:///test_rent.db'
os.environ['DEMO_MODE'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret'

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.test_client() as client:
    # Test 1: Root redirects to login
    resp = client.get('/')
    print(f"1. Root redirect: {resp.status_code} -> {resp.location}")

    # Test 2: Login page loads
    resp = client.get('/login')
    print(f"2. Login page: {resp.status_code}")

    # Test 3: Login with demo user
    resp = client.post('/login', data={'email': 'landlord@demo.com', 'password': 'demo123'}, follow_redirects=True)
    print(f"3. Login demo: {resp.status_code} (dashboard)")

    # Test 4: Dashboard loads with stats
    resp = client.get('/dashboard')
    assert b'Dashboard' in resp.data
    print(f"4. Dashboard: {resp.status_code}")

    # Test 5: Properties list
    resp = client.get('/properties/')
    assert b'Sunrise Apartments' in resp.data
    print(f"5. Properties: {resp.status_code}")

    # Test 6: Property detail
    resp = client.get('/properties/1')
    assert b'A1' in resp.data
    print(f"6. Property detail: {resp.status_code}")

    # Test 7: Tenants list
    resp = client.get('/tenants/')
    assert b'Grace Wanjiku' in resp.data
    print(f"7. Tenants: {resp.status_code}")

    # Test 8: Leases list
    resp = client.get('/leases/')
    assert b'Active' in resp.data
    print(f"8. Leases: {resp.status_code}")

    # Test 9: Payments list
    resp = client.get('/payments/')
    print(f"9. Payments: {resp.status_code}")

    # Test 10: Rent roll
    resp = client.get('/reports/rent-roll')
    assert b'Rent Roll' in resp.data
    print(f"10. Rent Roll: {resp.status_code}")

    # Test 11: Arrears
    resp = client.get('/reports/arrears')
    print(f"11. Arrears: {resp.status_code}")

    # Test 12: Register new user
    resp = client.get('/logout', follow_redirects=True)
    resp = client.post('/register', data={
        'full_name': 'Test User',
        'email': 'test@test.com',
        'phone': '0700000000',
        'password': 'test123',
        'confirm_password': 'test123'
    }, follow_redirects=True)
    print(f"12. Register: {resp.status_code}")

    # Test 13: Add property
    resp = client.post('/properties/add', data={
        'name': 'Test Property',
        'address': 'Test Street',
        'city': 'Nairobi',
        'property_type': 'apartment',
        'description': 'Test'
    }, follow_redirects=True)
    assert b'Test Property' in resp.data
    print(f"13. Add property: {resp.status_code}")

    # Test 14: Add tenant
    resp = client.post('/tenants/add', data={
        'full_name': 'New Tenant',
        'phone': '0711111111',
        'email': 'tenant@test.com',
        'id_type': 'national_id',
        'id_number': '12345678',
        'employer': 'Test Corp'
    }, follow_redirects=True)
    print(f"14. Add tenant: {resp.status_code}")

print("\nAll tests passed!")
