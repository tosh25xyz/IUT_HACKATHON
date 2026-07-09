#!/usr/bin/env python3
"""Contract verification - ensures API endpoints maintain exact paths, status codes, and field names."""
import sys
from datetime import datetime, timedelta

import httpx


BASE_URL = "http://localhost:8000"


def check_health(client: httpx.Client):
    """GET /health → 200 with status field."""
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data, "Missing 'status' field"
    print("✓ GET /health - 200 OK")


def check_register(client: httpx.Client):
    """POST /auth/register → 201 with expected fields."""
    org_name = f"ContractOrg{datetime.utcnow().timestamp()}"
    resp = client.post("/auth/register", json={
        "org_name": org_name,
        "username": "admin1",
        "password": "test123"
    })
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["user_id", "org_id", "username", "role"]), \
        f"Missing fields in response: {data.keys()}"
    print("✓ POST /auth/register - 201 Created")
    
    # Test duplicate username → 409 USERNAME_TAKEN
    resp = client.post("/auth/register", json={
        "org_name": org_name,
        "username": "admin1",
        "password": "test456"
    })
    assert resp.status_code == 409, f"Expected 409 for duplicate, got {resp.status_code}"
    data = resp.json()
    assert data.get("code") == "USERNAME_TAKEN", f"Expected USERNAME_TAKEN, got {data.get('code')}"
    print("✓ POST /auth/register - 409 USERNAME_TAKEN for duplicate")
    
    return org_name


def check_login(client: httpx.Client, org_name: str):
    """POST /auth/login → 200 with tokens."""
    resp = client.post("/auth/login", json={
        "org_name": org_name,
        "username": "admin1",
        "password": "test123"
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["access_token", "refresh_token", "token_type"]), \
        f"Missing fields: {data.keys()}"
    print("✓ POST /auth/login - 200 OK")
    
    # Test invalid credentials → 401 INVALID_CREDENTIALS
    resp = client.post("/auth/login", json={
        "org_name": org_name,
        "username": "admin1",
        "password": "wrongpass"
    })
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    data = resp.json()
    assert data.get("code") == "INVALID_CREDENTIALS", f"Expected INVALID_CREDENTIALS, got {data.get('code')}"
    print("✓ POST /auth/login - 401 INVALID_CREDENTIALS")
    
    # Return token for subsequent tests
    resp = client.post("/auth/login", json={
        "org_name": org_name,
        "username": "admin1",
        "password": "test123"
    })
    return resp.json()["access_token"], resp.json()["refresh_token"]


def check_refresh(client: httpx.Client, refresh_token: str):
    """POST /auth/refresh → 200 with new tokens."""
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["access_token", "refresh_token", "token_type"]), \
        f"Missing fields: {data.keys()}"
    print("✓ POST /auth/refresh - 200 OK")
    
    # Test reuse of same refresh token → 401
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401, f"Expected 401 for reuse, got {resp.status_code}"
    print("✓ POST /auth/refresh - 401 on reuse")


def check_logout(client: httpx.Client, token: str):
    """POST /auth/logout → 200."""
    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data, "Missing 'status' field"
    print("✓ POST /auth/logout - 200 OK")


def check_rooms(client: httpx.Client, token: str):
    """Room endpoints contract verification."""
    # Create room - POST /rooms → 201
    resp = client.post("/rooms", 
        json={"name": "Conference A", "capacity": 10, "hourly_rate_cents": 5000},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["id", "org_id", "name", "capacity", "hourly_rate_cents"]), \
        f"Missing fields: {data.keys()}"
    room_id = data["id"]
    print("✓ POST /rooms - 201 Created")
    
    # List rooms - GET /rooms → 200
    resp = client.get("/rooms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert isinstance(resp.json(), list), "Expected list response"
    print("✓ GET /rooms - 200 OK")
    
    # Availability - GET /rooms/{id}/availability → 200
    date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(f"/rooms/{room_id}/availability?date={date}",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["room_id", "date", "busy"]), f"Missing fields: {data.keys()}"
    print("✓ GET /rooms/{id}/availability - 200 OK")
    
    # Stats - GET /rooms/{id}/stats → 200
    resp = client.get(f"/rooms/{room_id}/stats",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["room_id", "total_confirmed_bookings", "total_revenue_cents"]), \
        f"Missing fields: {data.keys()}"
    print("✓ GET /rooms/{id}/stats - 200 OK")
    
    return room_id


def check_bookings(client: httpx.Client, token: str, room_id: int):
    """Booking endpoints contract verification."""
    now = datetime.utcnow()
    start = now + timedelta(hours=2)
    end = start + timedelta(hours=1)
    
    # Create booking - POST /bookings → 201
    resp = client.post("/bookings",
        json={
            "room_id": room_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    data = resp.json()
    expected_fields = ["id", "reference_code", "room_id", "user_id", 
                      "start_time", "end_time", "status", "price_cents", "created_at"]
    assert all(k in data for k in expected_fields), f"Missing fields: {data.keys()}"
    booking_id = data["id"]
    print("✓ POST /bookings - 201 Created")
    
    # Test invalid booking → 400 INVALID_BOOKING_WINDOW
    resp = client.post("/bookings",
        json={
            "room_id": room_id,
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": now.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    data = resp.json()
    assert data.get("code") == "INVALID_BOOKING_WINDOW", \
        f"Expected INVALID_BOOKING_WINDOW, got {data.get('code')}"
    print("✓ POST /bookings - 400 INVALID_BOOKING_WINDOW")
    
    # Test room conflict → 409 ROOM_CONFLICT
    resp = client.post("/bookings",
        json={
            "room_id": room_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
    data = resp.json()
    assert data.get("code") == "ROOM_CONFLICT", f"Expected ROOM_CONFLICT, got {data.get('code')}"
    print("✓ POST /bookings - 409 ROOM_CONFLICT")
    
    # List bookings - GET /bookings → 200
    resp = client.get("/bookings?page=1&limit=10",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["items", "page", "limit", "total"]), \
        f"Missing fields: {data.keys()}"
    print("✓ GET /bookings - 200 OK")
    
    # Get booking detail - GET /bookings/{id} → 200
    resp = client.get(f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "refunds" in data, "Missing 'refunds' field"
    print("✓ GET /bookings/{id} - 200 OK")
    
    # Cancel booking - POST /bookings/{id}/cancel → 200
    resp = client.post(f"/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["id", "status", "refund_percent", "refund_amount_cents"]), \
        f"Missing fields: {data.keys()}"
    print("✓ POST /bookings/{id}/cancel - 200 OK")
    
    # Test already cancelled → 409 ALREADY_CANCELLED
    resp = client.post(f"/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
    data = resp.json()
    assert data.get("code") == "ALREADY_CANCELLED", \
        f"Expected ALREADY_CANCELLED, got {data.get('code')}"
    print("✓ POST /bookings/{id}/cancel - 409 ALREADY_CANCELLED")
    
    return booking_id


def check_admin(client: httpx.Client, token: str):
    """Admin endpoints contract verification."""
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Usage report - GET /admin/usage-report → 200
    resp = client.get(f"/admin/usage-report?from={yesterday.isoformat()}&to={today.isoformat()}",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert all(k in data for k in ["from", "to", "rooms"]), f"Missing fields: {data.keys()}"
    print("✓ GET /admin/usage-report - 200 OK")
    
    # Export - GET /admin/export → 200 CSV
    resp = client.get("/admin/export",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.headers.get("content-type") == "text/csv; charset=utf-8", \
        f"Expected CSV content-type, got {resp.headers.get('content-type')}"
    csv_lines = resp.text.strip().split('\n')
    header = csv_lines[0].split(',')
    expected_header = ["id", "reference_code", "room_id", "user_id", 
                      "start_time", "end_time", "status", "price_cents"]
    assert header == expected_header, f"CSV header mismatch: {header}"
    print("✓ GET /admin/export - 200 OK with correct CSV format")


def main():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        print("=== API Contract Verification ===\n")
        
        try:
            check_health(client)
            org_name = check_register(client)
            access_token, refresh_token = check_login(client, org_name)
            check_refresh(client, refresh_token)
            
            # Get new token since refresh invalidated old one
            access_token, _ = check_login(client, org_name)
            
            room_id = check_rooms(client, access_token)
            check_bookings(client, access_token, room_id)
            check_admin(client, access_token)
            
            # Logout at end
            check_logout(client, access_token)
            
            print("\n" + "="*50)
            print("✓ All contract checks passed!")
            print("="*50)
            return 0
            
        except AssertionError as e:
            print(f"\n✗ Contract check failed: {e}")
            return 1
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
