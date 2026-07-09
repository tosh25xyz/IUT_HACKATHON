# CoWork — Coworking Space Booking API

> **🐛 Bug Fix Submission — ICT Fest 2024 Preliminary Round**
> 
> This repository contains fixes for 24 bugs seeded into the CoWork API.
> All bugs have been systematically identified, fixed with minimal changes, and verified
> with comprehensive concurrency stress tests. See `bug_report.md` for complete details.

CoWork is a REST API for managing bookable rooms inside a coworking space across
multiple tenant organizations. Each organization has its own rooms, staff
(admins), and members. Members book rooms for time slots; admins manage rooms and
pull reports.

## Stack

- Python 3.11, FastAPI, SQLAlchemy, SQLite (single file, no external DB service)
- JWT auth (access + refresh tokens), HS256, secret from the `JWT_SECRET` env var
- One container, served on **port 8000**

## Setup

```bash
docker compose up --build
```

The database schema is created automatically on first startup — no manual
provisioning or seed scripts. The API listens on `http://localhost:8000`.

To run the smoke test locally:

```bash
pip install -r requirements.txt
pytest
```

## Business rules

1. **Datetimes.** All API datetimes are ISO 8601. Input datetimes carrying a UTC
   offset are converted to UTC before storage or comparison; naive input is
   treated as UTC. All response datetimes are UTC with an explicit UTC designator
   (`Z` or `+00:00`).
2. **Booking price.** `price_cents = hourly_rate_cents × duration_hours`. Duration
   must be a whole number of hours, minimum 1, maximum 8. `end_time` must be
   strictly after `start_time`. `start_time` must be strictly in the future at
   request time — no grace window of any size.
3. **No double-booking.** Two `confirmed` bookings for the same room overlap iff
   `existing.start_time < new.end_time AND new.start_time < existing.end_time`.
   Back-to-back bookings (one ending exactly when the other starts) are allowed.
   Conflict → `409 ROOM_CONFLICT`. Holds under concurrent requests.
4. **Booking quota.** A member may hold at most 3 `confirmed` bookings with
   `start_time` in the window `(now, now + 24h]`, across all rooms in their org.
   Violation → `409 QUOTA_EXCEEDED`. Holds under concurrent requests.
5. **Rate limit.** `POST /bookings` is limited to 20 requests per rolling 60
   seconds per user (all requests count, successful or not). Excess →
   `429 RATE_LIMITED`. Holds under concurrent requests.
6. **Cancellation refund policy.** Only the booking's owner or an admin of the
   same org may cancel. Notice = `start_time − cancellation_time`:
   - notice ≥ 48 hours → 100% refund
   - 24 hours ≤ notice < 48 hours → 50% refund
   - notice < 24 hours → 0% refund

   Refund amount = percentage of `price_cents`, rounded to the nearest cent with
   half-cents rounding up (e.g. 50% of 1001 = 501). Cancelling an
   already-cancelled booking → `409 ALREADY_CANCELLED`. A cancelled booking has
   exactly one RefundLog entry, and the amount returned by the cancel response
   equals the amount stored in the RefundLog. Holds under concurrent cancel
   requests for the same booking.
7. **Reference codes.** Every booking's `reference_code` is unique, including
   under concurrent creation.
8. **Auth.** Tokens are JWTs (HS256) with claims `sub` (user id, string), `org`
   (org id), `role`, `jti` (unique per token), `iat`, `exp`, `type`
   (`access` | `refresh`). Access tokens: `exp − iat` = exactly 900 seconds.
   Refresh tokens: 7 days. Logout immediately invalidates the presented access
   token for all further use (subsequent use → `401`). Refresh tokens are
   single-use: `POST /auth/refresh` returns a new access **and** refresh token and
   invalidates the presented refresh token (reuse → `401`).
9. **Multi-tenancy.** A user (including admins) may only ever read or act on data
   (rooms, bookings, reports, exports, availability, stats) belonging to their own
   organization, on every code path. Cross-org resource IDs behave as
   non-existent → `404`.
10. **Booking visibility.** Members may read and cancel only their own bookings
    (another member's booking id → `404 BOOKING_NOT_FOUND`). Admins may read and
    cancel any booking in their org.
11. **Pagination & ordering.** `GET /bookings` takes `page` (int ≥ 1, default 1)
    and `limit` (int 1–100, default 10). Items are the caller's own bookings
    sorted by ascending `start_time` (ties by ascending `id`). Page N with limit L
    returns items `[(N−1)·L, N·L)` of that ordering; sequential pages never skip
    or repeat items. Response includes `total`.
12. **Usage report.** `GET /admin/usage-report?from=YYYY-MM-DD&to=YYYY-MM-DD`
    returns, per room in the caller's org (including rooms with zero bookings),
    the count of `confirmed` bookings with `start_time` on a date in `[from, to]`
    (UTC, inclusive) and their summed `price_cents`. Cancelled bookings are
    excluded. The report reflects the current state immediately.
13. **Availability.** `GET /rooms/{id}/availability?date=YYYY-MM-DD` returns the
    room's `confirmed` bookings starting on that UTC date as busy intervals,
    sorted ascending. Reflects the current state immediately.
14. **Room stats.** `GET /rooms/{id}/stats` returns the room's current count of
    `confirmed` bookings and their summed `price_cents` (cancellation decrements
    both). Always equals the values derivable from the bookings themselves.
15. **Registration.** `POST /auth/register` with an unknown `org_name` creates the
    org and the user as `admin`; with a known `org_name` it joins the caller as
    `member`. A duplicate username within the org → `409 USERNAME_TAKEN`.
16. **Liveness.** The service responds to all endpoints at all times; no
    combination of concurrent valid requests may hang the service.

## API contract

### Endpoints

| Method | Path | Auth | Success | Description |
|---|---|---|---|---|
| POST | `/auth/register` | No | 201 | Register org admin or join org as member |
| POST | `/auth/login` | No | 200 | Returns access + refresh token |
| POST | `/auth/refresh` | No (refresh token in body) | 200 | Rotates tokens |
| POST | `/auth/logout` | Yes | 200 | Invalidates presented access token |
| GET | `/rooms` | Yes | 200 | List rooms in caller's org |
| POST | `/rooms` | Yes (admin) | 201 | Create a room |
| GET | `/rooms/{id}/availability` | Yes | 200 | Busy intervals for a date |
| GET | `/rooms/{id}/stats` | Yes | 200 | Live confirmed-booking count & revenue |
| POST | `/bookings` | Yes | 201 | Create a booking |
| GET | `/bookings` | Yes | 200 | Caller's bookings, paginated |
| GET | `/bookings/{id}` | Yes | 200 | Single booking incl. refunds |
| POST | `/bookings/{id}/cancel` | Yes | 200 | Cancel + refund calculation |
| GET | `/admin/usage-report` | Yes (admin) | 200 | Per-room usage/revenue for range |
| GET | `/admin/export` | Yes (admin) | 200 | Bookings CSV; `room_id`, `include_all` |
| GET | `/health` | No | 200 | `{"status": "ok"}` |

### Request/response schemas (exact field names)

- `POST /auth/register` body `{org_name, username, password}` →
  `{user_id, org_id, username, role}`
- `POST /auth/login` body `{org_name, username, password}` →
  `{access_token, refresh_token, token_type: "bearer"}`; bad credentials →
  `401 INVALID_CREDENTIALS`
- `POST /auth/refresh` body `{refresh_token}` → same shape as login
- Room: `{id, org_id, name, capacity, hourly_rate_cents}`;
  `POST /rooms` body `{name, capacity, hourly_rate_cents}`
- Availability: `{room_id, date, busy: [{start_time, end_time}, …]}`
- Stats: `{room_id, total_confirmed_bookings, total_revenue_cents}`
- `POST /bookings` body `{room_id, start_time, end_time}` → Booking:
  `{id, reference_code, room_id, user_id, start_time, end_time, status,
  price_cents, created_at}`
- `GET /bookings` → `{items: [Booking, …], page, limit, total}`
- `GET /bookings/{id}` → Booking plus
  `refunds: [{amount_cents, status, processed_at}, …]`
- `POST /bookings/{id}/cancel` →
  `{id, status: "cancelled", refund_percent, refund_amount_cents}`
- Usage report → `{from, to, rooms: [{room_id, room_name, confirmed_bookings,
  revenue_cents}, …]}`
- Export CSV header (exact):
  `id,reference_code,room_id,user_id,start_time,end_time,status,price_cents`

### Errors

Application errors return JSON `{"detail": <string>, "code": <CODE>}` with codes:
`USERNAME_TAKEN` (409), `INVALID_CREDENTIALS` (401), `ROOM_CONFLICT` (409),
`QUOTA_EXCEEDED` (409), `RATE_LIMITED` (429), `ALREADY_CANCELLED` (409),
`BOOKING_NOT_FOUND` (404), `ROOM_NOT_FOUND` (404), `FORBIDDEN` (403),
`INVALID_BOOKING_WINDOW` (400 — past start, non-whole/out-of-range duration, or
`end_time ≤ start_time`). Missing/invalid/expired/blacklisted tokens → 401.
Framework validation errors (422) use FastAPI's default shape.

## Grading

**Your fixes must preserve this contract exactly** (paths, status codes, error
codes, JSON field names, JWT claims). Grading is **black-box**: the grader builds
the container and asserts behavior against the business rules and API contract
above by talking to the API only.

---

## 🐛 Bug Fix Documentation

### Quick Links
- **[bug_report.md](bug_report.md)** - Complete catalog of all 24 bugs with line numbers and fixes
- **[SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md)** - High-level overview of changes
- **[FIXES_CHECKLIST.md](FIXES_CHECKLIST.md)** - Quick verification checklist
- **[QUICKSTART.md](QUICKSTART.md)** - Installation and testing guide
- **[scripts/README.md](scripts/README.md)** - Test script documentation

### What Was Fixed

**24 bugs across 9 files:**
- 4 datetime & validation bugs
- 3 business logic bugs
- 3 authentication bugs
- 3 API security & visibility bugs
- 3 pagination bugs
- 2 cache invalidation bugs
- 6 concurrency bugs (database + threading)

**Key improvements:**
- ✅ Timezone offsets properly converted to UTC
- ✅ All booking validations enforced (strict future, duration range, end > start)
- ✅ Back-to-back bookings allowed (strict overlap check)
- ✅ Refund policy correct (0% <24h, 50% 24-48h, 100% ≥48h) with half-up rounding
- ✅ Token expiry 900 seconds, JTI-based revocation, single-use refresh tokens
- ✅ Member visibility restricted to own bookings
- ✅ Pagination: ascending order, correct offset, respects limit
- ✅ Database-level locking prevents double-booking, quota violations, cancel races
- ✅ Thread-safe counters for rate limiting, reference codes, and statistics

### Verification

```bash
# Install dependencies
pip install -r requirements.txt
pip install httpx

# Start server (terminal 1)
uvicorn app.main:app

# Run contract verification (terminal 2)
python scripts/contract_check.py

# Run concurrency stress tests (repeat 3-5 times)
rm -f cowork.db && python scripts/stress_test.py
```

**Expected results:**
- Contract check: All ✓ marks (endpoints maintain exact API contract)
- Stress tests: 6/6 pass (all concurrency rules hold under load)

### Files Modified

**Core application (8 files):**
- `app/auth.py`, `app/timeutils.py`, `app/models.py`
- `app/routers/auth.py`, `app/routers/bookings.py`
- `app/services/ratelimit.py`, `app/services/reference.py`, `app/services/stats.py`, `app/services/refunds.py`

**New documentation & tests:**
- Bug report and checklists
- Concurrency stress tests (`scripts/stress_test.py`)
- API contract verification (`scripts/contract_check.py`)

### No Contract Changes

✅ All endpoint paths unchanged  
✅ All HTTP status codes unchanged  
✅ All error code strings unchanged  
✅ All JSON field names unchanged  
✅ CSV export header unchanged  

Every fix targets only the bug itself with minimal diffs.
