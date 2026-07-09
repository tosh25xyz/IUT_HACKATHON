#!/usr/bin/env python3
"""Concurrency stress tests for CoWork API bug detection."""
import asyncio
import sys
from collections import Counter
from datetime import datetime, timedelta

import httpx


BASE_URL = "http://localhost:8000"


async def setup_test_env(client: httpx.AsyncClient):
    """Create org, users, and room for testing."""
    # Register admin
    resp = await client.post("/auth/register", json={
        "org_name": "StressOrg",
        "username": "admin1",
        "password": "pass123"
    })
    resp.raise_for_status()
    admin_data = resp.json()
    
    # Login admin
    resp = await client.post("/auth/login", json={
        "org_name": "StressOrg",
        "username": "admin1",
        "password": "pass123"
    })
    resp.raise_for_status()
    admin_token = resp.json()["access_token"]
    
    # Create room
    resp = await client.post("/rooms", 
        json={"name": "TestRoom", "capacity": 10, "hourly_rate_cents": 5000},
        headers={"Authorization": f"Bearer {admin_token}"})
    resp.raise_for_status()
    room_id = resp.json()["id"]
    
    # Register members
    members = []
    for i in range(5):
        await client.post("/auth/register", json={
            "org_name": "StressOrg",
            "username": f"member{i}",
            "password": "pass123"
        })
        resp = await client.post("/auth/login", json={
            "org_name": "StressOrg",
            "username": f"member{i}",
            "password": "pass123"
        })
        members.append(resp.json()["access_token"])
    
    return admin_token, members, room_id


async def test_double_booking(client: httpx.AsyncClient, tokens: list[str], room_id: int):
    """Test BR3: No double-booking under concurrent load."""
    print("\n=== Testing Double-Booking (BR3) ===")
    
    now = datetime.utcnow()
    start = now + timedelta(hours=2)
    end = start + timedelta(hours=1)
    
    async def book():
        try:
            resp = await client.post("/bookings",
                json={
                    "room_id": room_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                },
                headers={"Authorization": f"Bearer {tokens[0]}"})
            return resp.status_code, resp.json().get("code")
        except Exception as e:
            return None, str(e)
    
    results = await asyncio.gather(*[book() for _ in range(10)])
    status_counts = Counter(r[0] for r in results)
    
    success_count = status_counts.get(201, 0)
    conflict_count = status_counts.get(409, 0)
    
    print(f"Results: {success_count} created, {conflict_count} conflicts")
    if success_count == 1 and conflict_count == 9:
        print("✓ PASS: Exactly one booking succeeded")
        return True
    else:
        print(f"✗ FAIL: Expected 1 success, got {success_count}")
        return False


async def test_quota(client: httpx.AsyncClient, token: str, room_id: int):
    """Test BR4: Quota limit under concurrent load."""
    print("\n=== Testing Quota (BR4) ===")
    
    now = datetime.utcnow()
    
    async def book(offset_hours):
        start = now + timedelta(hours=offset_hours)
        end = start + timedelta(hours=1)
        try:
            resp = await client.post("/bookings",
                json={
                    "room_id": room_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                },
                headers={"Authorization": f"Bearer {token}"})
            return resp.status_code, resp.json().get("code")
        except Exception as e:
            return None, str(e)
    
    # Fire 6 concurrent requests within 24h window
    results = await asyncio.gather(*[book(i + 3) for i in range(6)])
    status_counts = Counter(r[0] for r in results)
    
    success_count = status_counts.get(201, 0)
    quota_exceeded = status_counts.get(409, 0)
    
    print(f"Results: {success_count} created, {quota_exceeded} quota exceeded")
    if success_count == 3 and quota_exceeded == 3:
        print("✓ PASS: Exactly 3 bookings succeeded")
        return True
    else:
        print(f"✗ FAIL: Expected 3 successes, got {success_count}")
        return False


async def test_rate_limit(client: httpx.AsyncClient, token: str, room_id: int):
    """Test BR5: Rate limiting under concurrent load."""
    print("\n=== Testing Rate Limit (BR5) ===")
    
    now = datetime.utcnow()
    
    async def book(i):
        start = now + timedelta(hours=100 + i)
        end = start + timedelta(hours=1)
        try:
            resp = await client.post("/bookings",
                json={
                    "room_id": room_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                },
                headers={"Authorization": f"Bearer {token}"})
            return resp.status_code
        except Exception:
            return None
    
    # Fire 25 concurrent requests
    results = await asyncio.gather(*[book(i) for i in range(25)])
    status_counts = Counter(results)
    
    success = status_counts.get(201, 0)
    rate_limited = status_counts.get(429, 0)
    
    print(f"Results: {success} created, {rate_limited} rate limited")
    if success <= 20 and rate_limited >= 5:
        print("✓ PASS: Rate limit enforced")
        return True
    else:
        print(f"✗ FAIL: Expected <=20 successes, got {success}")
        return False


async def test_reference_uniqueness(client: httpx.AsyncClient, tokens: list[str], room_id: int):
    """Test BR7: Reference codes must be unique under concurrent creation."""
    print("\n=== Testing Reference Code Uniqueness (BR7) ===")
    
    now = datetime.utcnow()
    
    async def book(i):
        start = now + timedelta(hours=200 + i)
        end = start + timedelta(hours=1)
        try:
            resp = await client.post("/bookings",
                json={
                    "room_id": room_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                },
                headers={"Authorization": f"Bearer {tokens[i % len(tokens)]}"})
            if resp.status_code == 201:
                return resp.json().get("reference_code")
        except Exception:
            pass
        return None
    
    results = await asyncio.gather(*[book(i) for i in range(20)])
    codes = [r for r in results if r]
    
    unique_codes = len(set(codes))
    total_codes = len(codes)
    
    print(f"Results: {total_codes} bookings, {unique_codes} unique codes")
    if unique_codes == total_codes:
        print("✓ PASS: All reference codes unique")
        return True
    else:
        print(f"✗ FAIL: {total_codes - unique_codes} duplicate codes")
        return False


async def test_cancel_idempotency(client: httpx.AsyncClient, token: str, room_id: int):
    """Test BR6: Concurrent cancels must create exactly one RefundLog."""
    print("\n=== Testing Cancel Idempotency (BR6) ===")
    
    # Create a booking
    now = datetime.utcnow()
    start = now + timedelta(hours=300)
    end = start + timedelta(hours=1)
    
    resp = await client.post("/bookings",
        json={
            "room_id": room_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"})
    booking_id = resp.json()["id"]
    
    # Concurrent cancels
    async def cancel():
        try:
            resp = await client.post(f"/bookings/{booking_id}/cancel",
                headers={"Authorization": f"Bearer {token}"})
            return resp.status_code, resp.json().get("refund_amount_cents")
        except Exception:
            return None, None
    
    results = await asyncio.gather(*[cancel() for _ in range(10)])
    status_counts = Counter(r[0] for r in results)
    refund_amounts = [r[1] for r in results if r[1] is not None]
    
    success = status_counts.get(200, 0)
    already_cancelled = status_counts.get(409, 0)
    
    print(f"Results: {success} cancelled, {already_cancelled} already cancelled")
    print(f"Refund amounts: {refund_amounts}")
    
    if success == 1 and already_cancelled == 9 and len(set(refund_amounts)) == 1:
        print("✓ PASS: Exactly one cancel succeeded, consistent refund")
        return True
    else:
        print(f"✗ FAIL: Expected 1 success, got {success}")
        return False


async def test_stats_consistency(client: httpx.AsyncClient, tokens: list[str], room_id: int):
    """Test BR14: Stats must be consistent after concurrent operations."""
    print("\n=== Testing Stats Consistency (BR14) ===")
    
    # Get initial stats
    resp = await client.get(f"/rooms/{room_id}/stats",
        headers={"Authorization": f"Bearer {tokens[0]}"})
    initial_stats = resp.json()
    initial_count = initial_stats["total_confirmed_bookings"]
    
    # Create 10 concurrent bookings
    now = datetime.utcnow()
    
    async def book(i):
        start = now + timedelta(hours=400 + i)
        end = start + timedelta(hours=1)
        try:
            resp = await client.post("/bookings",
                json={
                    "room_id": room_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat()
                },
                headers={"Authorization": f"Bearer {tokens[i % len(tokens)]}"})
            return resp.status_code == 201
        except Exception:
            return False
    
    results = await asyncio.gather(*[book(i) for i in range(10)])
    created_count = sum(results)
    
    # Check stats
    resp = await client.get(f"/rooms/{room_id}/stats",
        headers={"Authorization": f"Bearer {tokens[0]}"})
    final_stats = resp.json()
    final_count = final_stats["total_confirmed_bookings"]
    
    expected = initial_count + created_count
    print(f"Initial: {initial_count}, Created: {created_count}, Final: {final_count}, Expected: {expected}")
    
    if final_count == expected:
        print("✓ PASS: Stats consistent")
        return True
    else:
        print(f"✗ FAIL: Stats mismatch")
        return False


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print("Setting up test environment...")
        admin_token, member_tokens, room_id = await setup_test_env(client)
        
        results = []
        results.append(await test_double_booking(client, member_tokens, room_id))
        results.append(await test_quota(client, member_tokens[0], room_id))
        results.append(await test_rate_limit(client, member_tokens[1], room_id))
        results.append(await test_reference_uniqueness(client, member_tokens, room_id))
        results.append(await test_cancel_idempotency(client, member_tokens[2], room_id))
        results.append(await test_stats_consistency(client, member_tokens, room_id))
        
        print(f"\n{'='*50}")
        print(f"Results: {sum(results)}/{len(results)} tests passed")
        print(f"{'='*50}")
        
        return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
