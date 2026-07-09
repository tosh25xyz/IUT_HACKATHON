# CoWork Frontend

React frontend for the CoWork room booking system.

## Setup & Run

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Make sure the backend is running on `http://localhost:8000`

3. Start the development server:
```bash
npm run dev
```

4. Open http://localhost:3000 in your browser

## Features

- User registration and login
- JWT authentication with auto-refresh
- Browse available rooms
- Create bookings with date/time picker
- View all your bookings
- Cancel bookings with automatic refund calculation
- Real-time error handling
- Responsive design

## Default Test Account

If you ran the stress tests, you can login with:
- Organization: `StressOrg`
- Username: `admin1`
- Password: `pass123`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` folder.
