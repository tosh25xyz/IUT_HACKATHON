# CoWork API Bug Report

This document catalogs all bugs found and fixed in the CoWork backend API, organized by Business Rule violations.

## Summary

**Total Bugs Found: 23**
- Deterministic bugs: 15
- Concurrency bugs: 8

---

## Business Rule 1: Datetime Handling

### Bug #1: Timezone Offset Not Normalized to UTC
**Files:** `app/timeutils.py:11-15`

**Description:** The `parse_input_datetime` function removed timezone info without first converting to UTC. For an input like "2024-01-01T10:00:00+05:00", it would store "2024-01-01T10:00:00" instead of "2024-01-01T05:00:00" UTC.

**Violation:** BR1 - "Inputs with a UTC offset must be normalized to UTC before storage/comparison"

**Fix:** Changed from `dt.replace(tzinfo=None)` to `dt.astimezone(timezone.utc).replace(tzinfo=None)` to properly convert timezone-aware datetimes to UTC before removing the timezone info.

---

## Business Rule 2: Booking Price & Validation

### Bug #2: Start Time Has 5-Minute Grace Period
**Files:** `app/routers/bookings.py:60`

**Description:** Code checked `start <= now - timedelta(seconds=300)`, allowing bookings up to 5 minutes in the past.

**Violation:** BR2 - "start_time must be strictly in the future at request time (no grace window)"

**Fix:** Changed to `start <= now` to enforce strict future requirement.

### Bug #3: Missing Minimum Duration Check
**Files:** `app/routers/bookings.py:68-69`

**Description:** Code only checked maximum duration, not minimum. A booking with 0 hours would be accepted.

**Violation:** BR2 - "Duration must be a whole number of hours, min 1, max 8"

**Fix:** Changed condition from `if duration_hours > MAX_DURATION_HOURS` to `if duration_hours < MIN_DURATION_HOURS or duration_hours > MAX_DURATION_HOURS`.

### Bug #4: End Time Not Validated Against Start Time
**Files:** `app/routers/bookings.py:63-64`

**Description:** No check that `end_time > start_time`. A booking with end_time equal to or before start_time would be accepted.

**Violation:** BR2 - "end_time must be strictly after start_time"

**Fix:** Added explicit check `if end <= start: raise AppError(400, "INVALID_BOOKING_WINDOW", "end_time must be after start_time")`.

---

## Business Rule 3: No Double-Booking

### Bug #5: Overlap Logic Allows Back-to-Back as Conflict
**Files:** `app/routers/bookings.py:44`

**Description:** Overlap check used `<=` which would flag back-to-back bookings (e.g., 10:00-11:00 and 11:00-12:00) as conflicts.

**Violation:** BR3 - "Back-to-back is allowed" (overlap condition should use strict `<`)

**Fix:** Changed from `b.start_time <= end and start <= b.end_time` to `b.start_time < end and start < b.end_time`.

### Bug #6: Double-Booking Race Condition
**Files:** `app/routers/bookings.py:80-92`

**Description:** The `_has_conflict` check was performed outside a database transaction/lock. Two concurrent requests could both see no conflict and both insert, violating the no-double-booking rule.

**Violation:** BR3 - "Must hold under concurrent requests"

**Fix:** Moved conflict check inside transaction and added `.with_for_update()` to lock existing bookings for the room during the check-and-insert operation.

---

## Business Rule 4: Booking Quota

### Bug #7: Quota Check Race Condition
**Files:** `app/routers/bookings.py:93-94`

**Description:** The `_check_quota` function counted bookings without locking. Concurrent requests could all see count < 3 and all insert, exceeding the quota.

**Violation:** BR4 - "Must hold under concurrent requests"

**Fix:** Moved quota check inside transaction and added `.with_for_update()` to lock user's bookings during the count-and-insert operation.

---

## Business Rule 5: Rate Limiting

### Bug #8: Rate Limiter Has Race Condition
**Files:** `app/services/ratelimit.py:13-22`

**Description:** The `_buckets` dict was accessed without thread synchronization. Concurrent requests could interleave read-modify-write operations, allowing more than 20 requests through.

**Violation:** BR5 - "Must hold under concurrent requests"

**Fix:** Added `_lock = threading.Lock()` and wrapped the entire `record_and_check` logic in `with _lock:` to ensure atomic bucket updates.

---

## Business Rule 6: Cancellation Refund Policy

### Bug #9: Less Than 24h Notice Gets 50% Instead of 0%
**Files:** `app/routers/bookings.py:171-177`

**Description:** The refund logic had `else: refund_percent = 50` which gave 50% refund for <24h notice instead of 0%.

**Violation:** BR6 - "<24h → 0% refund"

**Fix:** Changed else branch from `refund_percent = 50` to `refund_percent = 0`.

### Bug #10: Rounding Uses Banker's Rounding Not Half-Up
**Files:** `app/routers/bookings.py:179`, `app/services/refunds.py:14`

**Description:** Python's `round()` uses banker's rounding (round half to even), not the "half-up" rounding specified. Additionally, the refund logging function used truncation (`int()`) instead of proper rounding, and had unnecessary intermediate float conversions.

**Violation:** BR6 - "Round to nearest cent, half-cents round up"

**Fix:** 
- In `cancel_booking`: Changed from `round(booking.price_cents * (refund_percent / 100.0))` to `int(booking.price_cents * (refund_percent / 100.0) + 0.5)` for half-up rounding.
- In `log_refund`: Changed from multi-step dollar conversion with truncation to direct calculation `int(booking.price_cents * (percent / 100.0) + 0.5)` to ensure both functions calculate the exact same amount.

### Bug #11: Concurrent Cancel Race Condition
**Files:** `app/routers/bookings.py:156-189`

**Description:** Cancellation checked status without locking. Concurrent cancel requests could both see status="confirmed" and both proceed, creating multiple RefundLog entries.

**Violation:** BR6 - "Exactly one RefundLog per cancelled booking; must hold under concurrent cancel requests"

**Fix:** Added `.with_for_update()` to booking query to lock the booking row during the status check and cancellation.

---

## Business Rule 7: Reference Code Uniqueness

### Bug #12: Reference Code Generator Has Race Condition
**Files:** `app/services/reference.py:13-16`

**Description:** The counter increment was not atomic. Concurrent requests could read the same counter value and generate duplicate reference codes.

**Violation:** BR7 - "Every booking's reference code is unique, including under concurrent creation"

**Fix:** Added `_lock = threading.Lock()` and wrapped counter logic in `with _lock:` to ensure atomic counter increments. Also added `unique=True` constraint to the database column.

---

## Business Rule 8: Authentication

### Bug #13: Access Token Expires in 900 Minutes Not 900 Seconds
**Files:** `app/auth.py:62`

**Description:** Code used `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)` where `ACCESS_TOKEN_EXPIRE_MINUTES=15`, resulting in 900-minute (15-hour) expiry instead of 900-second (15-minute) expiry.

**Violation:** BR8 - "Access tokens expire in exactly 900s"

**Fix:** Changed from `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)` to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`.

### Bug #14: Token Revocation Checks Wrong Field
**Files:** `app/auth.py:100`

**Description:** Revocation check used `payload.get("sub")` (user ID) instead of `payload.get("jti")` (token ID), so logout didn't actually revoke the specific token.

**Violation:** BR8 - "Logout immediately invalidates the presented access token (reuse → 401)"

**Fix:** Changed from checking `"sub" in _revoked_tokens` to checking `"jti" in _revoked_tokens`.

### Bug #15: Refresh Tokens Not Single-Use
**Files:** `app/routers/auth.py:48-57`

**Description:** Refresh tokens could be reused multiple times. The spec requires single-use with rotation.

**Violation:** BR8 - "Refresh tokens are single-use — refreshing rotates both tokens and invalidates the old refresh token (reuse → 401)"

**Fix:** Added `_used_refresh_tokens` set and check/mark JTI as used during refresh to prevent token reuse.

---

## Business Rule 10: Booking Visibility

### Bug #16: Members Can See Other Members' Bookings
**Files:** `app/routers/bookings.py:125-145`

**Description:** The `get_booking` endpoint filtered by org but not by user ownership. Any member could view any other member's booking in the same org.

**Violation:** BR10 - "Members can read only their own bookings (another member's booking id → 404)"

**Fix:** Added check `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, ...)` to enforce member-only-sees-own-bookings rule.

---

## Business Rule 11: Pagination

### Bug #17: List Bookings Orders Descending Not Ascending
**Files:** `app/routers/bookings.py:114`

**Description:** Bookings were ordered by `start_time.desc()` instead of ascending.

**Violation:** BR11 - "ascending by start_time, ties by ascending id"

**Fix:** Changed from `.order_by(Booking.start_time.desc(), ...)` to `.order_by(Booking.start_time.asc(), ...)`.

### Bug #18: Pagination Offset Calculation Off By One Page
**Files:** `app/routers/bookings.py:115`

**Description:** Offset calculated as `page * limit` instead of `(page - 1) * limit`, skipping the first page of results.

**Violation:** BR11 - "Sequential pages must never skip or repeat items"

**Fix:** Changed from `.offset(page * limit)` to `.offset((page - 1) * limit)`.

### Bug #19: Limit Parameter Ignored (Hardcoded to 10)
**Files:** `app/routers/bookings.py:116`

**Description:** Query used `.limit(10)` instead of `.limit(limit)`, ignoring the user's requested page size.

**Violation:** BR11 - "limit (default 10, max 100)" should be respected

**Fix:** Changed from `.limit(10)` to `.limit(limit)`.

---

## Business Rule 12: Usage Report

### Bug #20: Report Cache Not Invalidated on Booking Creation
**Files:** `app/routers/bookings.py:97-100`

**Description:** Cache invalidation only occurred on cancel, not on create. New bookings wouldn't appear in cached reports until cache timeout.

**Violation:** BR12 - "Must reflect current state immediately"

**Fix:** Added `cache.invalidate_report(user.org_id)` after booking creation.

---

## Business Rule 13: Availability

### Bug #21: Availability Cache Not Invalidated on Cancellation
**Files:** `app/routers/bookings.py:187-189`

**Description:** Availability cache was only invalidated on booking creation, not on cancellation. Cancelled bookings would still show as busy until cache timeout.

**Violation:** BR13 - "Must reflect current state immediately"

**Fix:** Added `cache.invalidate_availability(booking.room_id, booking.start_time.date().isoformat())` after cancellation.

---

## Business Rule 14: Room Statistics

### Bug #22: Stats Counter Has Race Condition
**Files:** `app/services/stats.py:10-23`

**Description:** The `_stats` dict was accessed without thread synchronization. Concurrent updates could lose increments or decrements.

**Violation:** BR14 - "Including after concurrent bursts"

**Fix:** Added `_lock = threading.Lock()` and wrapped all `_stats` access in `with _lock:` blocks to ensure atomic updates.

---

## Business Rule 15: Registration

### Bug #23: Duplicate Username Returns Success Instead of 409
**Files:** `app/routers/auth.py:25-33`

**Description:** When a user registered with an existing username in the same org, the code returned the existing user's data with 201 status instead of raising `409 USERNAME_TAKEN`.

**Violation:** BR15 - "Duplicate username in org → 409 USERNAME_TAKEN"

**Fix:** Changed from returning existing user data to `raise AppError(409, "USERNAME_TAKEN", "Username already exists in organization")`.

---

## Additional Bug: Incorrect Start Time in Booking Detail Response

### Bug #24: get_booking Returns created_at as start_time
**Files:** `app/routers/bookings.py:143`

**Description:** The response overwrote `start_time` with `booking.created_at` instead of keeping the actual start time from serialization.

**Violation:** API contract consistency - start_time should be the booking start time, not creation time

**Fix:** Removed the line `response["start_time"] = iso_utc(booking.created_at)` to preserve the correct start_time from serialization.

---

## Testing Methodology

### Phase 1: Static Audit
Each business rule was traced through the codebase line-by-line to identify logic errors, missing validation, and contract violations.

### Phase 2: Deterministic Bug Fixes
Bugs that could be verified with single-request testing (validation, calculations, datetime handling, pagination, etc.) were fixed and manually verified.

### Phase 3: Concurrency Testing
A comprehensive stress test script (`scripts/stress_test.py`) was created to verify all six concurrency-sensitive rules:
- Double-booking prevention
- Quota enforcement
- Rate limiting
- Reference code uniqueness
- Cancel idempotency
- Statistics consistency

Each test fires concurrent requests and asserts the expected invariants hold.

### Phase 4: Contract Verification
All endpoint paths, status codes, error codes, and JSON field names were verified to remain unchanged per the specification.

---

## Verification Status

All 23 bugs have been fixed with minimal, targeted changes. Database-level locking ensures concurrency safety. Thread-local synchronization protects in-memory data structures. No API contract changes were made.
