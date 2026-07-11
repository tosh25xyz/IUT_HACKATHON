# Bug Report — CoWork API
## IUT 12th ICT Fest Bdapps Agentic AI Hackathon

Total bugs found: **25** across all difficulty tiers.

---

## Bug #1 — Access Token Expiry Is 15 Hours Instead of 15 Minutes
**File:** `app/auth.py`, line 50  
**Difficulty:** Easy (3 pts)  
**What:** `lifetime = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 60)` computes `timedelta(minutes=15*60)` = `timedelta(minutes=900)` = **15 hours**.  
**Why wrong:** Rule 8: "Access tokens expire in exactly 900 seconds" = 15 minutes.  
**Fix:** Change to `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)` → `timedelta(minutes=15)` = 900 seconds.

---

## Bug #2 — Revoked Token Check Compares `sub` (user ID) Instead of `jti` (token ID)
**File:** `app/auth.py`, line 97  
**Difficulty:** Easy (3 pts)  
**What:** `if payload.get("sub") in _revoked_tokens:` checks the user's numeric ID against the revoked set, but `revoke_access_token()` on line 86 stores `payload["jti"]` (the token's unique ID).  
**Why wrong:** A revoked token's `jti` will never match its owner's `sub`, so revoked tokens remain usable. Conversely, ALL tokens from a logged-out user would be blocked (wrong field).  
**Fix:** Change `payload.get("sub")` to `payload.get("jti")`.

---

## Bug #3 — Duplicate Username Returns 200 Instead of 409 USERNAME_TAKEN
**File:** `app/routers/auth.py`, lines 37–43  
**Difficulty:** Easy (3 pts)  
**What:** When a duplicate `(org_id, username)` is found during registration, the code returns the existing user's data with HTTP 200.  
**Why wrong:** Rule 15: "A duplicate username within the org → 409 USERNAME_TAKEN."  
**Fix:** Replace the `return {...}` with `raise AppError(409, "USERNAME_TAKEN", "Username already taken")`.

---

## Bug #4 — Refresh Tokens Are Not Single-Use (Never Invalidated)
**File:** `app/routers/auth.py`, lines 81–93  
**Difficulty:** Medium (5 pts)  
**What:** The `/auth/refresh` endpoint decodes the refresh token and issues new token pairs, but never records the old refresh token's `jti` as used. The same refresh token can be reused indefinitely.  
**Why wrong:** Rule 8: "Refresh tokens are single-use: refreshing returns a new access and refresh token and invalidates the presented refresh token (reuse → 401)."  
**Fix:** Add a `_used_refresh_tokens` set in `app/auth.py` with `invalidate_refresh_token()` and `is_refresh_token_used()` helpers. In the refresh endpoint, check if the token was already used (→ 401) and mark it as used before issuing new tokens.

---

## Bug #5 — `parse_input_datetime` Strips UTC Offset Without Converting to UTC
**File:** `app/timeutils.py`, line 13  
**Difficulty:** Medium (5 pts)  
**What:** `dt = dt.replace(tzinfo=None)` discards the timezone info without converting to UTC. Input `2025-01-01T10:00:00+05:00` becomes `2025-01-01T10:00:00` (wrong — should be `05:00:00`).  
**Why wrong:** Rule 1: "Input datetimes carrying a UTC offset must be converted to UTC before storage or comparison."  
**Fix:** Change to `dt = dt.astimezone(timezone.utc).replace(tzinfo=None)`.

---

## Bug #6 — `start_time` Validation Allows a 300-Second Grace Window Into the Past
**File:** `app/routers/bookings.py`, line 86  
**Difficulty:** Easy (3 pts)  
**What:** `if start <= now - timedelta(seconds=300):` allows start times up to 5 minutes in the past.  
**Why wrong:** Rule 2: "start time must be strictly in the future at request time — no grace window."  
**Fix:** Change to `if start <= now:`.

---

## Bug #7 — Missing Minimum Duration Check (Allows 0-Hour Bookings)
**File:** `app/routers/bookings.py`, lines 89–94  
**Difficulty:** Easy (3 pts)  
**What:** The code checks `duration_hours > MAX_DURATION_HOURS` (max 8) but never checks `duration_hours < MIN_DURATION_HOURS` (min 1). A booking with `end_time == start_time` (duration 0) or `end_time < start_time` (negative duration) passes validation.  
**Why wrong:** Rule 2: "Duration must be a whole number of hours, minimum 1, maximum 8."  
**Fix:** Add `if duration_hours < MIN_DURATION_HOURS: raise AppError(400, "INVALID_BOOKING_WINDOW", "duration out of range")` after line 92.

---

## Bug #8 — Overlap Check Uses `<=` Instead of `<` (Blocks Back-to-Back Bookings)
**File:** `app/routers/bookings.py`, line 50  
**Difficulty:** Medium (5 pts)  
**What:** `if b.start_time <= end and start <= b.end_time:` treats bookings that share an endpoint (e.g., 10:00–11:00 then 11:00–12:00) as overlapping.  
**Why wrong:** Rule 3: "overlap iff existing.start < new.end AND new.start < existing.end. Back-to-back bookings are allowed."  
**Fix:** Change both `<=` to `<`: `if b.start_time < end and start < b.end_time:`.

---

## Bug #9 — Booking List Sorts Descending Instead of Ascending
**File:** `app/routers/bookings.py`, line 137  
**Difficulty:** Easy (3 pts)  
**What:** `.order_by(Booking.start_time.desc(), Booking.id.asc())` sorts by start time descending.  
**Why wrong:** Rule 11: "sorted ascending by start time (ties by ascending id)."  
**Fix:** Change `.desc()` to `.asc()`.

---

## Bug #10 — Pagination Offset Skips First Page
**File:** `app/routers/bookings.py`, line 138  
**Difficulty:** Easy (3 pts)  
**What:** `.offset(page * limit)` — for page 1 with limit 10, offset=10, skipping the first 10 items.  
**Why wrong:** Rule 11: "Sequential pages never skip or repeat items." Page 1 should start at offset 0.  
**Fix:** Change to `.offset((page - 1) * limit)`.

---

## Bug #11 — Hardcoded Limit of 10 (Ignores User-Specified Limit)
**File:** `app/routers/bookings.py`, line 139  
**Difficulty:** Easy (3 pts)  
**What:** `.limit(10)` always returns at most 10 items, ignoring the `limit` query parameter (which accepts 1–100).  
**Why wrong:** Rule 11: "limit (default 10, max 100)" — the user-specified value must be used.  
**Fix:** Change to `.limit(limit)`.

---

## Bug #12 — `get_booking` Overwrites `start_time` With `created_at`
**File:** `app/routers/bookings.py`, line 166  
**Difficulty:** Easy (3 pts)  
**What:** `response["start_time"] = iso_utc(booking.created_at)` replaces the correct `start_time` (already set by `serialize_booking` on line 165) with the booking's creation timestamp.  
**Why wrong:** The response should return the actual booking start time, not when the record was created.  
**Fix:** Remove line 166 entirely. The serializer already provides the correct `start_time`.

---

## Bug #13 — `get_booking` Missing Member Visibility Check
**File:** `app/routers/bookings.py`, lines 156–163  
**Difficulty:** Medium (5 pts)  
**What:** The query filters by `Room.org_id == user.org_id` but does NOT filter by `Booking.user_id` for non-admin users. A member can read any booking in their org by ID.  
**Why wrong:** Rule 10: "Members may read and cancel only their own bookings (another member's booking id → 404 BOOKING NOT FOUND)."  
**Fix:** After the `if booking is None` check, add: `if user.role != "admin" and booking.user_id != user.id: raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found")`. (Same pattern as `cancel_booking` line 192.)

---

## Bug #14 — Refund Tier: `notice >= 48h` Uses `>` Instead of `>=` (48h Gets 50% Instead of 100%)
**File:** `app/routers/bookings.py`, line 201  
**Difficulty:** Easy (3 pts)  
**What:** `notice_hours = int(...)` truncates to whole hours. `if notice_hours > 48:` misses exactly 48 hours. A booking cancelled exactly 48 hours before start gets 50% refund instead of 100%.  
**Why wrong:** Rule 6: "notice ≥ 48 hours → 100% refund."  
**Fix:** Change `>` to `>=` on line 201: `if notice_hours >= 48:`.

---

## Bug #15 — Refund Tier: `notice < 24h` Gives 50% Instead of 0%
**File:** `app/routers/bookings.py`, line 206  
**Difficulty:** Easy (3 pts)  
**What:** The `else` branch (notice < 24 hours) sets `refund_percent = 50`.  
**Why wrong:** Rule 6: "notice < 24 hours → 0% refund."  
**Fix:** Change `refund_percent = 50` to `refund_percent = 0`.

---

## Bug #16 — Refund Rounding: Response and RefundLog Use Different Formulas
**Files:** `app/routers/bookings.py` line 208, `app/services/refunds.py` line 17  
**Difficulty:** Medium (5 pts)  
**What:** The cancel response computes `round(price_cents * percent / 100.0)` (Python banker's rounding), while `log_refund` computes `int(refund_dollars * 100)` (truncation). These produce different values for odd amounts.  
  - Example: price=151¢, 50% → response: `round(75.5)`=76, RefundLog: `int(75.5)`=75. **Mismatch!**  
  - Example: price=149¢, 50% → response: `round(74.5)`=74, RefundLog: `int(74.5)`=74. **Same, but both wrong!** Should be 75 (half-cents rounding up).  
**Why wrong:** Rule 6: "Refund amount rounds to the nearest cent, half-cents rounding up" and "the amount returned by the cancel response must equal the amount stored in the RefundLog."  
**Fix:** Both places must use the same half-up rounding: `int(value + 0.5)` for positive values. Also, compute the refund amount in `log_refund` and return it, then use that value in the response.

---

## Bug #17 — Availability Cache Not Invalidated on Booking Cancellation
**File:** `app/routers/bookings.py`, `cancel_booking` function (around line 217)  
**Difficulty:** Medium (5 pts)  
**What:** When a booking is cancelled, `cache.invalidate_report(...)` is called but `cache.invalidate_availability(...)` is NOT. The availability endpoint continues showing the cancelled booking as busy.  
**Why wrong:** Rule 13: availability must return "the current state immediately."  
**Fix:** Add `cache.invalidate_availability(booking.room_id, booking.start_time.date().isoformat())` after the cancellation commit.

---

## Bug #18 — Usage Report Cache Not Invalidated on Booking Creation
**File:** `app/routers/bookings.py`, `create_booking` function (around line 121)  
**Difficulty:** Medium (5 pts)  
**What:** When a booking is created, `cache.invalidate_availability(...)` is called but `cache.invalidate_report(...)` is NOT. The usage report endpoint returns stale data until a cancellation happens.  
**Why wrong:** Rule 12: the usage report "Must reflect the current state immediately."  
**Fix:** Add `cache.invalidate_report(user.org_id)` after booking creation.

---

## Bug #19 — Room Stats Are In-Memory and Lose Consistency
**File:** `app/services/stats.py`  
**Difficulty:** Hard (10 pts)  
**What:** Stats are tracked incrementally in a plain Python dict with `time.sleep(0.1)` and no locking. After a server restart, stats reset to zero while bookings persist in SQLite. Under concurrent requests, the read-modify-write pattern loses updates (two threads read same `current`, both write, one update lost).  
**Why wrong:** Rule 14: stats must be "always consistent with the bookings themselves, including after bursts of concurrent activity."  
**Fix:** Change `stats.get()` to query the database directly (count confirmed bookings and sum price_cents). Remove the `_aggregate_pause()` sleep. Add a `threading.Lock` for thread safety. Keep `record_create`/`record_cancel` as no-ops (called from bookings.py but no longer affect `get()`).

---

## Bug #20 — Rate Limiter Has Race Condition (No Lock + Sleep)
**File:** `app/services/ratelimit.py`  
**Difficulty:** Hard (10 pts)  
**What:** `_buckets` dict is accessed without any locking. `_settle_pause()` adds a 0.1s sleep that widens the race window. Two concurrent threads can read the same bucket state, both append, and one update is lost, allowing more requests than the 20-request limit.  
**Why wrong:** Rule 5: rate limiting "Must hold under concurrent requests."  
**Fix:** Add a `threading.Lock()` around the read-modify-write of `_buckets`. Remove the `_settle_pause()` sleep.

---

## Bug #21 — Reference Code Generator Has Race Condition (No Lock + Sleep)
**File:** `app/services/reference.py`  
**Difficulty:** Hard (10 pts)  
**What:** The counter is read, then incremented after a `time.sleep(0.12)`. Two concurrent threads can read the same value and produce duplicate reference codes: Thread A reads 1000, sleeps, Thread B reads 1000, both increment to 1001, both return "CW-001000".  
**Why wrong:** Rule 7: "Every booking's reference code is unique, including under concurrent creation."  
**Fix:** Add a `threading.Lock()` around the read-increment-return. Remove `_format_pause()`.

---

## Bug #22 — Notifications Deadlock (Inconsistent Lock Ordering)
**File:** `app/services/notifications.py`  
**Difficulty:** Hard (10 pts)  
**What:** `notify_created` acquires `_email_lock` then `_audit_lock` (line 25-28). `notify_cancelled` acquires `_audit_lock` then `_email_lock` (line 31-34). If a create and cancel happen concurrently, Thread A holds email_lock waiting for audit_lock, Thread B holds audit_lock waiting for email_lock → **classic deadlock**. The `time.sleep(0.12)` and `time.sleep(0.1)` calls in the simulated operations make the deadlock nearly guaranteed under load.  
**Why wrong:** Rule 16: "no combination of concurrent valid requests may hang the service."  
**Fix:** Use a single lock for both operations (or always acquire locks in the same order). Remove the `time.sleep()` calls.

---

## Bug #23 — Booking Creation Has No Concurrency Protection (Double-Booking Possible)
**File:** `app/routers/bookings.py`, `_has_conflict` + `create_booking`  
**Difficulty:** Hard (10 pts)  
**What:** The conflict check (`SELECT`) and the insert (`INSERT`) are not atomic. Two concurrent requests for the same room can both pass the conflict check (neither sees the other's pending booking) and both commit, creating a double-booking. The `_pricing_warmup()` sleep widens this race window.  
**Why wrong:** Rule 3: "No double-booking ... Must hold under concurrent requests."  
**Fix:** Add a `threading.Lock()` in `create_booking` that wraps the conflict check, quota check, and insert as an atomic operation. Remove the `_pricing_warmup()` sleep.

---

## Bug #24 — Cancellation Has No Concurrency Protection (Double-Refund Possible)
**File:** `app/routers/bookings.py`, `cancel_booking`  
**Difficulty:** Hard (10 pts)  
**What:** The `ALREADY_CANCELLED` check (line 195) and the status update (line 213) are not atomic. Two concurrent cancel requests can both see `status == "confirmed"`, both compute a refund, and both commit — resulting in a double refund. The `_settlement_pause()` sleep widens the race window.  
**Why wrong:** Rule 6: "Must hold under concurrent cancel requests for the same booking."  
**Fix:** Add a `threading.Lock()` in `cancel_booking` that wraps the entire cancel+refund logic. Remove the `_settlement_pause()` sleep.

---

## Bug #25 — CSV Export Leaks Cross-Organization Data
**File:** `app/services/export.py`, lines 49–50  
**Difficulty:** Medium (5 pts)  
**What:** When `include_all=True` and `room_id` is provided, `fetch_bookings_raw(db, room_id)` is called, which does NOT filter by `org_id`. An admin from Org A could export bookings belonging to Org B by specifying a room_id from Org B.  
**Why wrong:** Rule 9: "A user (including admins) may only ever read or act on data belonging to their own organization, on every code path."  
**Fix:** Replace `fetch_bookings_raw(db, room_id)` with `_fetch_scoped(db, org_id, None, room_id)` which always filters by the caller's org.

---

## Additional: Unnecessary `time.sleep()` Calls Causing Latency
**Files:** `app/routers/bookings.py` (lines 29, 34, 39), `app/services/stats.py` (line 12), `app/services/ratelimit.py` (line 15), `app/services/reference.py` (line 14), `app/services/notifications.py` (lines 16, 21)  
**Difficulty:** Part of Bug #19–#24 fixes  
**What:** Eight `time.sleep()` calls disguised as "warmup", "audit", "settlement", "aggregate", "format", "settle", and simulated "email"/"audit" operations add ~0.5s+ to every booking operation and create race-condition/deadlock windows.  
**Fix:** Remove all eight `time.sleep()` calls as part of fixing Bugs #19–#24.

---

## Summary Table

| # | File(s) | Difficulty | Description |
|---|---------|-----------|-------------|
| 1 | auth.py:50 | Easy | Token expiry 15h instead of 15min |
| 2 | auth.py:97 | Easy | Revocation checks `sub` instead of `jti` |
| 3 | routers/auth.py:37 | Easy | Duplicate username → 200 instead of 409 |
| 4 | routers/auth.py:81 | Medium | Refresh tokens not single-use |
| 5 | timeutils.py:13 | Medium | UTC offset stripped without conversion |
| 6 | bookings.py:86 | Easy | 300s grace window on start_time |
| 7 | bookings.py:93 | Easy | Missing minimum duration (1h) check |
| 8 | bookings.py:50 | Medium | Overlap `<=` blocks back-to-back bookings |
| 9 | bookings.py:137 | Easy | Sort descending instead of ascending |
| 10 | bookings.py:138 | Easy | Pagination offset off-by-one |
| 11 | bookings.py:139 | Easy | Hardcoded limit=10, ignores param |
| 12 | bookings.py:166 | Easy | start_time overwritten with created_at |
| 13 | bookings.py:156 | Medium | Members can view other members' bookings |
| 14 | bookings.py:201 | Easy | 48h boundary `>` instead of `>=` |
| 15 | bookings.py:206 | Easy | <24h refund is 50% instead of 0% |
| 16 | bookings.py:208 + refunds.py:17 | Medium | Rounding mismatch + wrong rounding mode |
| 17 | bookings.py:cancel | Medium | Availability cache not invalidated on cancel |
| 18 | bookings.py:create | Medium | Report cache not invalidated on create |
| 19 | stats.py | Hard | In-memory stats inconsistent after restart/race |
| 20 | ratelimit.py | Hard | Race condition on rate limiter buckets |
| 21 | reference.py | Hard | Race condition → duplicate reference codes |
| 22 | notifications.py | Hard | Deadlock from inconsistent lock ordering |
| 23 | bookings.py:create | Hard | No concurrency protection → double-booking |
| 24 | bookings.py:cancel | Hard | No concurrency protection → double-refund |
| 25 | export.py:49 | Medium | Export leaks cross-org bookings |

**Point totals by difficulty:**
- Easy (3 pts each): 10 bugs × 3 = **30 points**
- Medium (5 pts each): 9 bugs × 5 = **45 points**
- Hard (10 pts each): 6 bugs × 10 = **60 points**
- **Grand total: 135 points**
