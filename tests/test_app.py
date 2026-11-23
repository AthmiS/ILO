def register_and_setup(client, email="owner@example.com", business="Test Studio"):
    client.post("/register", data={
        "name": "Test Owner", "email": email,
        "password": "securepass123", "confirm_password": "securepass123"
    }, follow_redirects=True)
    return client.post("/setup", data={
        "business_name": business, "category": "Salon & Beauty",
        "phone": "9876543210", "business_email": email,
        "description": "A test business", "address": "Puttur"
    }, follow_redirects=True)

def test_home_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Interactive Local Organizer" in response.data or b"beautifully in sync" in response.data

def test_register_and_business_setup(client):
    response = register_and_setup(client)
    assert response.status_code == 200
    assert b"Your services" in response.data

def test_service_creation(client):
    register_and_setup(client)
    response = client.post("/services", data={
        "name": "Haircut", "description": "Basic haircut",
        "price": "200", "duration": "30", "buffer_time": "10"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Haircut" in response.data

def test_public_booking_requires_service(client):
    register_and_setup(client)
    response = client.get("/book/test-studio")
    assert response.status_code == 200
    assert b"Bookings opening soon" in response.data

def test_owner_pages_require_login(client):
    assert client.get("/dashboard").status_code in (302, 401)
    assert client.get("/management").status_code in (302, 401)
