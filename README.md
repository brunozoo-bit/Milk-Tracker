# Milk Collection Management System

A comprehensive mobile application for managing milk collection from producers, built with React Native (Expo), FastAPI, and MongoDB.

## Features

### User Roles
- **Admin**: Full system access, can manage all users, producers, collectors, and collections
- **Factory**: Can view reports, manage producers and collectors, view all collections
- **Producer**: Can only view their own production data
- **Collector**: Can record milk collections from producers

### Core Functionality

#### 1. Authentication
- Email/password login
- JWT-based authentication
- Role-based access control
- Automatic session persistence

#### 2. Producer Management
- Create, view, update, and delete producers
- Store producer information: name, nickname, email, phone, address
- Upload producer photos (base64)
- Admin/Factory access only

#### 3. Collector Management
- Create and manage collectors
- Store collector information: name, email, phone
- Upload collector photos
- Admin/Factory access only

#### 4. Milk Collection Recording
- Record daily milk collections
- Track: date, time, day of week, quantity (liters)
- Add photos of collections
- Add notes/observations
- Role-based collection viewing (producers see only their data)

#### 5. Offline Support
- Network connectivity detection
- Offline indicators
- Batch sync endpoint for offline data (ready for implementation)
- Local storage with AsyncStorage

#### 6. Reports & Analytics
- Daily, weekly, and monthly summaries
- Total quantity collected
- Average quantity per collection
- Producer-specific statistics
- CSV export for payment processing

## Tech Stack

### Frontend
- **Framework**: Expo (React Native)
- **Navigation**: Expo Router with file-based routing
- **State Management**: Zustand + React Context
- **UI**: Native React Native components
- **Networking**: Axios
- **Offline Detection**: @react-native-community/netinfo
- **Storage**: @react-native-async-storage/async-storage
- **Image Handling**: expo-image-picker (base64 storage)
- **Date Utilities**: date-fns

### Backend
- **Framework**: FastAPI
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT with passlib/bcrypt
- **CORS**: Enabled for mobile access

## Project Structure

```
/app
├── backend/
│   ├── server.py          # FastAPI backend with all APIs
│   ├── .env              # Environment variables
│   └── requirements.txt  # Python dependencies
│
├── frontend/
│   ├── app/              # Expo Router screens
│   │   ├── (auth)/      # Authentication screens
│   │   │   └── login.tsx
│   │   ├── (tabs)/      # Main tab navigation
│   │   │   ├── index.tsx         # Collections list
│   │   │   ├── producers.tsx     # Producers list
│   │   │   ├── collectors.tsx    # Collectors list
│   │   │   ├── reports.tsx       # Reports & analytics
│   │   │   └── profile.tsx       # User profile
│   │   ├── add-collection/
│   │   ├── add-producer/
│   │   ├── add-collector/
│   │   ├── _layout.tsx   # Root layout with auth provider
│   │   └── index.tsx     # Entry point with route guard
│   │
│   ├── contexts/
│   │   └── AuthContext.tsx      # Authentication context
│   ├── services/
│   │   └── api.ts              # API client
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   └── package.json
│
└── memory/
    └── test_credentials.md      # Test account credentials
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/register` - Register new user (admin/factory only)

### Producers
- `GET /api/producers` - List all producers
- `POST /api/producers` - Create producer (admin/factory only)
- `GET /api/producers/{id}` - Get producer by ID
- `PUT /api/producers/{id}` - Update producer (admin/factory only)
- `DELETE /api/producers/{id}` - Delete producer (admin only)

### Collectors
- `GET /api/collectors` - List all collectors
- `POST /api/collectors` - Create collector (admin/factory only)
- `DELETE /api/collectors/{id}` - Delete collector (admin/factory only)

### Collections
- `GET /api/collections` - List collections (filtered by role)
- `POST /api/collections` - Create collection (collector/admin/factory)
- `GET /api/collections/{id}` - Get collection by ID
- `PUT /api/collections/{id}` - Update collection
- `DELETE /api/collections/{id}` - Delete collection (admin/factory only)
- `POST /api/collections/sync` - Batch sync offline collections

### Reports
- `GET /api/reports/summary` - Get summary statistics
- `GET /api/reports/export` - Export CSV report

## Default Credentials

**Admin Account:**
- Email: `admin@milktracker.com`
- Password: `admin123`

This account is automatically created on first backend startup.

## Setup & Installation

### Backend Setup
```bash
cd /app/backend
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup
```bash
cd /app/frontend
yarn install
yarn start
```

## Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
JWT_SECRET_KEY=your-secret-key-change-in-production
```

### Frontend (.env)
```
EXPO_PUBLIC_BACKEND_URL=https://your-app.preview.emergentagent.com
```

## Key Features Implementation

### 1. Role-Based UI
The tab navigation dynamically shows/hides tabs based on user role:
- Admin: All tabs (Collections, Producers, Collectors, Reports, Profile)
- Factory: Collections, Producers, Collectors, Reports, Profile
- Collector: Collections, Producers, Profile
- Producer: Collections, Profile

### 2. Image Handling
All images are stored as base64 strings in MongoDB for easy transfer and display. The app supports:
- Camera capture
- Gallery selection
- Image preview
- Compression (quality: 0.5)

### 3. Offline Detection
Uses `@react-native-community/netinfo` to detect network status and shows offline indicators. Backend has sync endpoint ready for offline data synchronization.

### 4. Data Validation
- Backend: Pydantic models for request/response validation
- Frontend: Form validation before submission
- JWT token validation on all protected routes

## Future Enhancements

1. **Full Offline Mode**
   - Implement local database (SQLite or Realm)
   - Queue offline actions
   - Auto-sync when online
   - Conflict resolution

2. **Enhanced Reports**
   - PDF generation
   - Graphical charts
   - Email reports
   - Scheduled reports

3. **Push Notifications**
   - Collection reminders
   - Payment notifications
   - System alerts

4. **Advanced Features**
   - Barcode/QR scanning for producers
   - GPS location tracking
   - Multiple collection routes
   - Payment integration
   - Multi-language support

## Testing

### Backend Tests
All backend APIs have been tested and verified:
- ✅ Authentication (login, token generation, user info)
- ✅ Producer CRUD operations
- ✅ Collector CRUD operations
- ✅ Collection recording and retrieval
- ✅ Reports and summaries
- ✅ Offline sync endpoint

Test results: 11/11 tests passed (100% success rate)

## Mobile App Preview

The app is deployed and accessible at:
- Web: https://milk-tracker-66.preview.emergentagent.com
- Expo Go: Scan QR code from Metro bundler

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.
