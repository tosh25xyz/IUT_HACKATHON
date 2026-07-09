# Quick Start Guide

## Installation & Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Additional dependency for test scripts
pip install httpx
```

## Running the API

```bash
# Start the server (default port 8000)
uvicorn app.main:app --reload

# Or specify a different port
uvicorn app.main:app --reload --port 8080
```

The API will be available at `http://localhost:8000`

## Verify Fixes

### Step 1: Check Code Compiles
```bash
python -m py_compile app/*.py app/routers/*.py app/services/*.py
```

### Step 2: Run Contract Verification
```bash
# In terminal 1: Start server
uvicorn app.main:app

# In terminal 2: Run tests
python scripts/contract_check.py
```

Expected output: All checks pass with ✓ marks

### Step 3: Run Concurrency Tests
```bash
# Clean database and run (repeat 3-5 times)
rm -f cowork.db && python scripts/stress_test.py
```

Expected output: 6/6 tests pass

## API Endpoints Quick Reference

### Health
- `GET /health` - Liveness check

### Authentication
- `POST /auth/register` - Create user/org
- `POST /auth/login` - Get tokens
- `POST /auth/refresh` - Rotate tokens (single-use)
- `POST /auth/logout` - Revoke access token

### Rooms
- `GET /rooms` - List org rooms
- `POST /rooms` - Create room (admin)
- `GET /rooms/{id}/availability?date=YYYY-MM-DD` - Check availability
- `GET /rooms/{id}/stats` - Live booking count/revenue

### Bookings
- `POST /bookings` - Create booking (rate limited)
- `GET /bookings?page=1&limit=10` - List own bookings (paginated)
- `GET /bookings/{id}` - Get booking detail + refunds
- `POST /bookings/{id}/cancel` - Cancel booking (with refund)

### Admin
- `GET /admin/usage-report?from=YYYY-MM-DD&to=YYYY-MM-DD` - Usage report
- `GET /admin/export?room_id=X&include_all=true` - CSV export

## Example Usage

```bash
# Register admin
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"org_name":"TestCo","username":"admin","password":"pass123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"org_name":"TestCo","username":"admin","password":"pass123"}'
# Returns: {"access_token":"...", "refresh_token":"...", "token_type":"bearer"}

# Create room (use token from login)
curl -X POST http://localhost:8000/rooms \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Conference A","capacity":10,"hourly_rate_cents":5000}'

# Create booking
curl -X POST http://localhost:8000/bookings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id":1,
    "start_time":"2026-07-10T10:00:00",
    "end_time":"2026-07-10T11:00:00"
  }'

# List bookings
curl http://localhost:8000/bookings?page=1&limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Cancel booking
curl -X POST http://localhost:8000/bookings/1/cancel \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Testing Specific Bugs

### Test Double-Booking Prevention (Bug #5, #6)
```python
# Create booking at 10:00-11:00
# Try second booking at 10:00-11:00 → should get 409 ROOM_CONFLICT
# Try booking at 11:00-12:00 → should succeed (back-to-back allowed)
```

### Test Quota Enforcement (Bug #7)
```python
# Create 3 bookings within next 24h → all succeed
# Try 4th booking within next 24h → should get 409 QUOTA_EXCEEDED
```

### Test Rate Limiting (Bug #8)
```python
# Make 20 booking requests in 60 seconds → all succeed
# Make 21st request → should get 429 RATE_LIMITED
```

### Test Refund Policy (Bug #9, #10)
```python
# Book 100 hours in future → cancel → 100% refund
# Book 36 hours in future → cancel → 50% refund  
# Book 12 hours in future → cancel → 0% refund
# Verify half-cent rounding: 5001 cents * 50% = 2501 cents (rounded up from 2500.5)
```

### Test Pagination (Bug #17, #18, #19)
```python
# Create 25 bookings
# GET /bookings?page=1&limit=10 → items 1-10, ascending by start_time
# GET /bookings?page=2&limit=10 → items 11-20 (no overlap with page 1)
# GET /bookings?page=3&limit=10 → items 21-25
```

## Debugging

### Check Database
```bash
sqlite3 cowork.db

# Useful queries
SELECT * FROM bookings;
SELECT * FROM refund_logs;
SELECT reference_code, COUNT(*) FROM bookings GROUP BY reference_code HAVING COUNT(*) > 1; # Should be empty
```

### Reset Database
```bash
rm -f cowork.db
# Restart server - tables will be recreated
```

## Documentation

- `bug_report.md` - Complete bug catalog with line numbers
- `FIXES_CHECKLIST.md` - Quick verification checklist
- `SUBMISSION_SUMMARY.md` - High-level overview
- `scripts/README.md` - Test script documentation
