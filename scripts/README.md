# Test Scripts

This directory contains stress tests and contract verification scripts for the CoWork API.

## Prerequisites

```bash
pip install httpx
```

## Running the Tests

### 1. Start the API Server

First, start the CoWork API in a separate terminal:

```bash
# Install dependencies
pip install fastapi sqlalchemy pyjwt uvicorn

# Run the server
uvicorn app.main:app --reload
```

### 2. Run Contract Verification

This ensures all API endpoints maintain their exact contracts (paths, status codes, error codes, field names):

```bash
python scripts/contract_check.py
```

Expected output: All checks should pass with ✓ marks.

### 3. Run Concurrency Stress Tests

This tests all six business rules that must hold under concurrent load:

```bash
python scripts/stress_test.py
```

Expected output: All 6 tests should pass.

**Note:** For best results, run the stress test 3-5 times to catch flaky race conditions:

```bash
for i in {1..5}; do
    echo "=== Run $i ==="
    python scripts/stress_test.py
    if [ $? -ne 0 ]; then
        echo "FAILED on run $i"
        exit 1
    fi
    # Clean up database between runs
    rm -f cowork.db
done
```

## What the Tests Verify

### Contract Verification (`contract_check.py`)
- Exact HTTP status codes (200, 201, 400, 401, 409, 429)
- Exact error code strings (INVALID_CREDENTIALS, ROOM_CONFLICT, etc.)
- Exact JSON field names in responses
- CSV header format for exports
- Authentication flow (register, login, refresh, logout)
- Room CRUD operations
- Booking lifecycle (create, list, get, cancel)
- Admin reporting

### Concurrency Stress Tests (`stress_test.py`)
1. **Double-booking (BR3):** 10 concurrent requests for same slot → exactly 1 succeeds
2. **Quota (BR4):** 6 concurrent requests within 24h window → exactly 3 succeed
3. **Rate limit (BR5):** 25 concurrent requests → at most 20 succeed
4. **Reference uniqueness (BR7):** 20 concurrent bookings → all codes unique
5. **Cancel idempotency (BR6):** 10 concurrent cancels → exactly 1 succeeds, consistent refund
6. **Stats consistency (BR14):** Concurrent creates → stats match actual DB state

## Interpreting Results

### Success
All tests show ✓ PASS with expected counts matching actual results.

### Failure Examples
- `✗ FAIL: Expected 1 success, got 3` → Race condition in double-booking check
- `✗ FAIL: 2 duplicate codes` → Reference code generator not atomic
- `✗ FAIL: Stats mismatch` → Counter updates losing increments

If any concurrency test fails, it indicates a race condition that needs database-level locking or thread synchronization.
