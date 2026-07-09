# CoWork API - Frontend Integration Guide

This guide will help you build a frontend application that connects to the CoWork API.

## 🚀 Quick Start

### 1. API Base URL
```
http://localhost:8000
```

### 2. Swagger/OpenAPI Documentation
```
http://localhost:8000/docs          # Interactive Swagger UI
http://localhost:8000/redoc         # Alternative ReDoc UI
http://localhost:8000/openapi.json  # Raw OpenAPI schema
```

FastAPI automatically generates interactive API documentation at these URLs when your server is running.

---

## 🔐 Authentication Flow

### Step 1: Register a New Organization & Admin User
**Endpoint:** `POST /auth/register`

```javascript
const response = await fetch('http://localhost:8000/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    org_name: "MyCompany",
    username: "admin",
    password: "securepass123"
  })
});

const data = await response.json();
// Response: { user_id, org_id, username, role: "admin" }
```

**Note:** First user in an organization becomes `admin`, subsequent users are `member`.

### Step 2: Login
**Endpoint:** `POST /auth/login`

```javascript
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    org_name: "MyCompany",
    username: "admin",
    password: "securepass123"
  })
});

const data = await response.json();
// Response: { access_token, refresh_token, token_type: "bearer" }

// Save tokens in localStorage or sessionStorage
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

### Step 3: Use Access Token for API Calls
```javascript
const token = localStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/rooms', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Step 4: Refresh Token (when access token expires)
**Endpoint:** `POST /auth/refresh`

```javascript
const refreshToken = localStorage.getItem('refresh_token');

const response = await fetch('http://localhost:8000/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: refreshToken
  })
});

const data = await response.json();
// Update stored tokens
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

**Important:** Access tokens expire in 15 minutes, refresh tokens in 7 days.

### Step 5: Logout
**Endpoint:** `POST /auth/logout`

```javascript
const token = localStorage.getItem('access_token');

await fetch('http://localhost:8000/auth/logout', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Clear stored tokens
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

---

## 🏢 Room Management

### List All Rooms (in your organization)
**Endpoint:** `GET /rooms`

```javascript
const response = await fetch('http://localhost:8000/rooms', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const rooms = await response.json();
// Response: [{ id, org_id, name, capacity, hourly_rate_cents }, ...]
```

### Create Room (admin only)
**Endpoint:** `POST /rooms`

```javascript
const response = await fetch('http://localhost:8000/rooms', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "Conference Room A",
    capacity: 10,
    hourly_rate_cents: 5000  // $50.00
  })
});

const room = await response.json();
// Response: { id, org_id, name, capacity, hourly_rate_cents }
```

### Check Room Availability
**Endpoint:** `GET /rooms/{room_id}/availability?date=YYYY-MM-DD`

```javascript
const roomId = 1;
const date = '2026-07-15';

const response = await fetch(
  `http://localhost:8000/rooms/${roomId}/availability?date=${date}`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const availability = await response.json();
// Response: {
//   room_id: 1,
//   date: "2026-07-15",
//   busy: [
//     { start_time: "2026-07-15T10:00:00Z", end_time: "2026-07-15T12:00:00Z" },
//     ...
//   ]
// }
```

### Get Room Statistics
**Endpoint:** `GET /rooms/{room_id}/stats`

```javascript
const response = await fetch(
  `http://localhost:8000/rooms/${roomId}/stats`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const stats = await response.json();
// Response: {
//   room_id: 1,
//   total_confirmed_bookings: 42,
//   total_revenue_cents: 210000
// }
```

---

## 📅 Booking Management

### Create Booking
**Endpoint:** `POST /bookings`

```javascript
const response = await fetch('http://localhost:8000/bookings', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    room_id: 1,
    start_time: "2026-07-15T10:00:00Z",  // ISO 8601 format
    end_time: "2026-07-15T12:00:00Z"
  })
});

const booking = await response.json();
// Response: {
//   id, room_id, user_id, start_time, end_time,
//   status: "confirmed", reference_code, price_cents, created_at
// }
```

**Business Rules:**
- Duration: 1-8 hours (whole hours only)
- Start time must be in the future
- Maximum 3 bookings per user within 24 hours (quota limit)
- Maximum 20 bookings per user per minute (rate limit)

### List My Bookings
**Endpoint:** `GET /bookings?page=1&limit=10`

```javascript
const response = await fetch(
  'http://localhost:8000/bookings?page=1&limit=10',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const data = await response.json();
// Response: {
//   items: [{ booking details }, ...],
//   page: 1,
//   limit: 10,
//   total: 42
// }
```

### Get Booking Details
**Endpoint:** `GET /bookings/{booking_id}`

```javascript
const bookingId = 123;

const response = await fetch(
  `http://localhost:8000/bookings/${bookingId}`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const booking = await response.json();
// Response: {
//   ...booking details,
//   refunds: [
//     { amount_cents, status, processed_at },
//     ...
//   ]
// }
```

### Cancel Booking
**Endpoint:** `POST /bookings/{booking_id}/cancel`

```javascript
const response = await fetch(
  `http://localhost:8000/bookings/${bookingId}/cancel`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const result = await response.json();
// Response: {
//   id, status: "cancelled",
//   refund_percent: 100,  // 100% if >48h, 50% if 24-48h, 0% if <24h
//   refund_amount_cents
// }
```

**Refund Policy:**
- ≥48 hours notice: 100% refund
- 24-48 hours notice: 50% refund
- <24 hours notice: 0% refund

---

## ⚠️ Error Handling

All errors follow this format:

```javascript
{
  "code": "ERROR_CODE",
  "message": "Human readable error message"
}
```

### Common Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 400 | `INVALID_BOOKING_WINDOW` | Invalid date/time format or duration |
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 401 | `INVALID_CREDENTIALS` | Wrong username/password |
| 404 | `ROOM_NOT_FOUND` | Room doesn't exist or not in your org |
| 404 | `BOOKING_NOT_FOUND` | Booking doesn't exist or not yours |
| 409 | `USERNAME_TAKEN` | Username already exists in org |
| 409 | `ROOM_CONFLICT` | Room already booked for that time |
| 409 | `QUOTA_EXCEEDED` | Too many bookings in 24h window |
| 409 | `ALREADY_CANCELLED` | Booking already cancelled |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |

### Error Handling Example

```javascript
try {
  const response = await fetch('http://localhost:8000/bookings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(bookingData)
  });

  if (!response.ok) {
    const error = await response.json();
    
    // Handle specific errors
    if (error.code === 'ROOM_CONFLICT') {
      alert('This room is already booked for that time!');
    } else if (error.code === 'QUOTA_EXCEEDED') {
      alert('You have reached your booking limit (3 per 24 hours)');
    } else if (response.status === 401) {
      // Token expired, refresh it
      await refreshAccessToken();
    } else {
      alert(error.message);
    }
    return;
  }

  const booking = await response.json();
  console.log('Booking created:', booking);
} catch (err) {
  console.error('Network error:', err);
}
```

---

## 🎨 Sample Frontend Implementation (React)

### Axios Setup with Interceptor
```javascript
// api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000'
});

// Add token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            'http://localhost:8000/auth/refresh',
            { refresh_token: refreshToken }
          );
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          
          // Retry original request
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return axios(error.config);
        } catch {
          // Refresh failed, logout
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    throw error;
  }
);

export default api;
```

### Example Components

```javascript
// Login.jsx
import { useState } from 'react';
import api from './api';

function Login() {
  const [form, setForm] = useState({ org_name: '', username: '', password: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post('/auth/login', form);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      window.location.href = '/dashboard';
    } catch (err) {
      alert(err.response?.data?.message || 'Login failed');
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input placeholder="Organization" onChange={e => setForm({...form, org_name: e.target.value})} />
      <input placeholder="Username" onChange={e => setForm({...form, username: e.target.value})} />
      <input type="password" placeholder="Password" onChange={e => setForm({...form, password: e.target.value})} />
      <button type="submit">Login</button>
    </form>
  );
}

// RoomList.jsx
import { useEffect, useState } from 'react';
import api from './api';

function RoomList() {
  const [rooms, setRooms] = useState([]);

  useEffect(() => {
    api.get('/rooms').then(res => setRooms(res.data));
  }, []);

  return (
    <div>
      <h2>Available Rooms</h2>
      {rooms.map(room => (
        <div key={room.id}>
          <h3>{room.name}</h3>
          <p>Capacity: {room.capacity}</p>
          <p>Rate: ${room.hourly_rate_cents / 100}/hour</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔧 Development Tips

### CORS Configuration
If you're running your frontend on a different port (e.g., React on `localhost:3000`), you may need to enable CORS in the FastAPI app:

```python
# In app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### DateTime Handling
- API expects ISO 8601 format: `2026-07-15T10:00:00Z`
- JavaScript: `new Date().toISOString()`
- Display: `new Date(isoString).toLocaleString()`

### Price Display
Prices are stored in cents:
```javascript
const displayPrice = (cents) => `$${(cents / 100).toFixed(2)}`;
// 5000 cents → "$50.00"
```

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **OpenAPI Schema:** http://localhost:8000/openapi.json
- **Health Check:** http://localhost:8000/health

## 🐛 Testing

Use the included stress test to verify the API:
```bash
python scripts/stress_test.py
```

Start building your frontend and explore the interactive Swagger UI at http://localhost:8000/docs for live API testing!
