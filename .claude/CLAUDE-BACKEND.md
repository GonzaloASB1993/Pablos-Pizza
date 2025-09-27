# ⚙️ Backend Documentation - Pablo's Pizza

## 📁 Project Structure
```
backend/
├── main.py                   # Main Flask application
├── models/
│   └── schemas.py           # Pydantic models and validation
├── services/                # Business logic services
├── utils/                   # Utility functions
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
└── venv/                    # Virtual environment
```

## 🐍 Core Technology Stack
- **Framework:** Flask with CORS support
- **Database:** Firebase Firestore
- **Authentication:** Firebase Auth
- **Storage:** Firebase Storage
- **Validation:** Pydantic models
- **Deployment:** Google Cloud Run

## 🔗 Database Schema (Firestore Collections)

### 📅 `bookings` Collection
```python
{
  "id": str,
  "client_name": str,
  "client_email": str,
  "client_phone": str,
  "service_type": "workshop" | "pizza_party",
  "event_type": "birthday" | "corporate" | "school" | "private",
  "event_date": datetime,
  "event_time": str,
  "duration_hours": int,
  "participants": int,
  "location": str,
  "special_requests": str,
  "status": "pending" | "confirmed" | "completed" | "cancelled",
  "estimated_price": float,
  "created_at": datetime,
  "updated_at": datetime
}
```

### 🎉 `events` Collection
```python
{
  "id": str,
  "booking_id": str,
  "client_name": str,
  "event_type": str,
  "event_date": datetime,
  "participants": int,
  "status": "completed",
  "event_cost": float,      # Actual costs incurred
  "event_profit": float,    # Revenue received
  "notes": str,
  "created_at": datetime
}
```

### 📞 `contacts` Collection (NEW)
```python
{
  "id": str,
  "name": str,
  "email": str,
  "phone": str,
  "subject": str,
  "message": str,
  "priority": "low" | "normal" | "high" | "urgent",
  "status": "pending" | "in_progress" | "resolved",
  "created_at": datetime,
  "updated_at": datetime,
  "assigned_to": str,           # Admin user ID
  "response_method": str,       # "email" | "whatsapp"
  "response_sent": bool,
  "resolved_at": datetime,
  "notes": str
}
```

### 📸 `gallery` Collection
```python
{
  "id": str,
  "title": str,
  "description": str,
  "url": str,                   # Firebase Storage URL
  "event_id": str,              # Reference to event
  "category": str,
  "is_published": bool,
  "uploaded_at": datetime
}
```

### ⭐ `reviews` Collection
```python
{
  "id": str,
  "client_name": str,
  "client_email": str,
  "event_id": str,
  "rating": int,                # 1-5
  "comment": str,
  "is_approved": bool,
  "created_at": datetime
}
```

## 🛠️ API Endpoints Overview

### 📅 Booking Endpoints
```python
POST   /api/bookings/                    # Create booking (public)
GET    /api/bookings/                    # List bookings (admin)
PUT    /api/bookings/<booking_id>        # Update booking (admin)
DELETE /api/bookings/<booking_id>        # Delete booking (admin)
GET    /api/bookings/calendar/<year>/<month>  # Calendar view (admin)
```

### 📞 Contact Endpoints (NEW)
```python
POST   /api/contacts                     # Create contact message (public)
GET    /api/contacts                     # List contacts with filtering (admin)
PUT    /api/contacts/<contact_id>        # Update contact status (admin)
POST   /api/contacts/<contact_id>/respond # Send response via email/WhatsApp (admin)
```

### 🎉 Event Endpoints
```python
POST   /api/events/                      # Create event record (admin)
GET    /api/events/                      # List events (admin)
PUT    /api/events/<event_id>            # Update event (admin)
```

### 📸 Gallery Endpoints
```python
GET    /api/gallery/public               # Public gallery (events with images)
GET    /api/gallery/                     # Admin gallery management
POST   /api/gallery/upload               # Upload image (admin)
PUT    /api/gallery/<photo_id>/publish   # Publish/unpublish image (admin)
```

### ⭐ Review Endpoints
```python
POST   /api/reviews/                     # Create review (public)
GET    /api/reviews/                     # List reviews
PUT    /api/reviews/<review_id>/approve  # Approve review (admin)
```

## 🔧 Key Backend Functions

### 🗄️ Database Connection
```python
def get_db():
    """Get Firestore database connection"""
    if not firebase_admin._apps:
        cred = credentials.Certificate("path/to/serviceAccount.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()
```

### 🔐 Authentication Middleware
```python
def verify_admin_token(token):
    """Verify Firebase authentication token"""
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token.get('admin', False)
    except Exception:
        return False
```

### 📧 WhatsApp Integration
```python
def send_whatsapp_notification(phone, message):
    """Send WhatsApp notification to admin"""
    # Integration point for WhatsApp API
    # Currently logs message for development
    print(f"📱 WhatsApp to {phone}: {message}")
```

## 🚀 Business Logic Workflows

### 📅 Booking → Event Flow
```python
# 1. Client creates booking (status: pending)
POST /api/bookings/
→ Auto-calculate estimated_price
→ Send confirmation email

# 2. Admin confirms booking
PUT /api/bookings/{id} {"status": "confirmed"}
→ Send confirmation WhatsApp

# 3. Admin completes event with costs (NEW WORKFLOW)
PUT /api/bookings/{id} {
  "status": "completed",
  "event_cost": 150.00,
  "event_profit": 300.00
}
→ Auto-create event record
→ Calculate profit margins
```

### 📞 Contact Management Flow (NEW)
```python
# 1. Client submits contact form
POST /api/contacts
→ Store with priority level
→ Send WhatsApp notification to admin
→ Status: "pending"

# 2. Admin takes case
PUT /api/contacts/{id} {"status": "in_progress"}

# 3. Admin responds
POST /api/contacts/{id}/respond {
  "response_method": "whatsapp",
  "response_message": "Hola! Te contacto por tu consulta..."
}
→ Send response via chosen method
→ Status: "resolved"
```

### 📸 Gallery Management Flow
```python
# 1. Upload photos to event
POST /api/gallery/upload
→ Store in Firebase Storage
→ Create gallery record (is_published: false)

# 2. Admin publishes photos
PUT /api/gallery/{photo_id}/publish {"is_published": true}

# 3. Public gallery displays published photos grouped by events
GET /api/gallery/public
→ Return events with published image arrays
```

## ⚡ Performance Optimizations

### 🗄️ Database Queries
- **Firestore compound indexes** for efficient filtering
- **Pagination** with limit/offset for large datasets
- **Selective field projection** to reduce data transfer

### 🔄 Caching Strategy
- **In-memory caching** for frequently accessed data
- **Image URL caching** for gallery performance
- **Report data caching** for dashboard loading

### 📊 Query Optimization Examples
```python
# Optimized booking queries with indexes
bookings_ref = db.collection("bookings")\
  .where("status", "==", status)\
  .where("event_date", ">=", start_date)\
  .order_by("event_date")\
  .limit(50)

# Efficient gallery grouping
events_ref = db.collection("events")\
  .where("status", "==", "completed")\
  .order_by("event_date", direction=firestore.Query.DESCENDING)
```

## 🔒 Security Implementation

### 🛡️ CORS Configuration
```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://pablospizza.web.app", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

### 🔐 Authentication Check
```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not verify_admin_token(auth_header.split(' ')[1]):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function
```

## 🔧 Development Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
```

## 📦 Key Dependencies
```txt
Flask==2.3.2
Flask-CORS==4.0.0
firebase-admin==6.2.0
pydantic==2.1.1
python-dotenv==1.0.0
requests==2.31.0
gunicorn==21.2.0
```

## 🐛 Error Handling Patterns
```python
try:
    # Database operation
    result = db.collection("bookings").document(booking_id).get()
    if not result.exists:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(result.to_dict()), 200
except Exception as e:
    print(f"Error: {e}")
    return jsonify({"error": "Internal server error"}), 500
```

## 🚀 Deployment Configuration
- **Cloud Run** for automatic scaling
- **Environment variables** for configuration
- **Health checks** at `/api/health`
- **Logging** with structured output for monitoring