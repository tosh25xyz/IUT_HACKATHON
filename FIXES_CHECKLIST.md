# Bug Fixes Checklist

This document provides a quick reference for all 24 bugs fixed in the CoWork API.

## ✅ Deterministic Bugs (Can verify with single requests)

### Datetime & Validation
- [x] **Bug #1** - Timezone offset normalized to UTC (`app/timeutils.py`)
- [x] **Bug #2** - Start time must be strictly in future, no grace period (`app/routers/bookings.py`)
- [x] **Bug #3** - Minimum duration validation added (`app/routers/bookings.py`)
- [x] **Bug #4** - End time must be after start time (`app/routers/bookings.py`)

### Business Logic
- [x] **Bug #5** - Overlap logic uses strict `<` not `<=` for back-to-back bookings (`app/routers/bookings.py`)
- [x] **Bug #9** - <24h notice gets 0% refund, not 50% (`app/routers/bookings.py`)
- [x] **Bug #10** - Refund rounding uses half-up, not banker's rounding (`app/routers/bookings.py`, `app/services/refunds.py`)

### Authentication
- [x] **Bug #13** - Access token expires in 900 seconds (15 min), not 900 minutes (`app/auth.py`)
- [x] **Bug #14** - Token revocation checks JTI not sub (`app/auth.py`)
- [x] **Bug #15** - Refresh tokens are single-use (`app/routers/auth.py`, `app/auth.py`)

### API Visibility & Security
- [x] **Bug #16** - Members can only see own bookings (`app/routers/bookings.py`)
- [x] **Bug #23** - Duplicate username returns 409, not success (`app/routers/auth.py`)
- [x] **Bug #24** - get_booking returns correct start_time (`app/routers/bookings.py`)

### Pagination
- [x] **Bug #17** - List bookings orders ascending by start_time (`app/routers/bookings.py`)
- [x] **Bug #18** - Pagination offset = (page-1)*limit (`app/routers/bookings.py`)
- [x] **Bug #19** - Limit parameter respected, not hardcoded to 10 (`app/routers/bookings.py`)

### Cache Invalidation
- [x] **Bug #20** - Report cache invalidated on booking creation (`app/routers/bookings.py`)
- [x] **Bug #21** - Availability cache invalidated on cancellation (`app/routers/bookings.py`)

## ✅ Concurrency Bugs (Require stress testing)

### Database-Level Locking
- [x] **Bug #6** - Double-booking prevention with `with_for_update()` (`app/routers/bookings.py`)
- [x] **Bug #7** - Quota check with `with_for_update()` (`app/routers/bookings.py`)
- [x] **Bug #11** - Cancel idempotency with `with_for_update()` (`app/routers/bookings.py`)

### Thread Synchronization
- [x] **Bug #8** - Rate limiter thread-safe with lock (`app/services/ratelimit.py`)
- [x] **Bug #12** - Reference code generator thread-safe with lock (`app/services/reference.py`)
- [x] **Bug #22** - Stats counter thread-safe with lock (`app/services/stats.py`)

### Database Constraints
- [x] Reference code unique constraint added to model (`app/models.py`)

## Verification Commands

### Check All Files Compile
```bash
python -m py_compile app/*.py app/routers/*.py app/services/*.py
```

### Run Contract Verification
```bash
# Start server in one terminal
uvicorn app.main:app

# Run contract checks in another
python scripts/contract_check.py
```

### Run Concurrency Stress Tests
```bash
# Clean database and run test
rm -f cowork.db
python scripts/stress_test.py

# Run multiple times to catch flaky races
for i in {1..5}; do
    rm -f cowork.db
    python scripts/stress_test.py || exit 1
done
```

## Files Modified

### Core Application Files
- `app/auth.py` - Token expiry, revocation checks, refresh token tracking
- `app/timeutils.py` - UTC normalization
- `app/models.py` - Reference code unique constraint

### Routers
- `app/routers/auth.py` - Registration duplicate check, refresh token rotation
- `app/routers/bookings.py` - Validation, locking, pagination, visibility, cache invalidation

### Services
- `app/services/ratelimit.py` - Thread-safe rate limiting
- `app/services/reference.py` - Thread-safe reference code generation
- `app/services/stats.py` - Thread-safe statistics updates
- `app/services/refunds.py` - Consistent rounding calculation

### Test Scripts (New)
- `scripts/stress_test.py` - Concurrency testing
- `scripts/contract_check.py` - API contract verification
- `scripts/README.md` - Test documentation

### Documentation
- `bug_report.md` - Detailed bug catalog
- `FIXES_CHECKLIST.md` - This file

## API Contract Guarantees (Unchanged)

✅ All endpoint paths unchanged
✅ All HTTP status codes unchanged
✅ All error code strings unchanged
✅ All JSON field names unchanged
✅ CSV export header order unchanged

## Key Implementation Details

### Concurrency Strategy
1. **Database locks** for data that must be consistent (bookings, cancellations)
2. **Thread locks** for in-memory data structures (counters, caches, rate limiters)
3. **Unique constraints** for natural keys (reference codes, usernames)

### Transaction Management
- `with_for_update()` used for pessimistic locking on critical reads
- Explicit rollback on `AppError` to release locks immediately
- All booking creation/cancellation in single transaction

### Rounding Implementation
Half-up rounding: `int(value + 0.5)`
- 50.5 cents → 51 cents
- 50.4 cents → 50 cents
- Consistent between cancel response and refund log

### Token Security
- Access tokens: JTI-based revocation on logout
- Refresh tokens: JTI tracked in `_used_refresh_tokens` set
- Single-use refresh prevents token replay attacks
