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

### 🤖 AI Assistant Endpoints (all `@require_admin`, except `/health`)
```python
POST   /api/ai-chat/                          # Chat with tool use; body {messages}; returns {response, tools_used, pending_actions[]}
GET    /api/ai-chat/pending/<id>              # A proposed action (flips to `expired` after 24 h)
POST   /api/ai-chat/pending/<id>/confirm      # Execute it ONCE; optional body {payload} with the edited fields (revalidated)
POST   /api/ai-chat/pending/<id>/cancel
GET    /api/ai-chat/health                    # Public
```
- **Propose → confirm:** the agent's `propose_*` tools only create a `pending_actions` document; `confirm` (no LLM) writes through the shared services (`services/expenses_service.py`) and logs to `audit_logs` with `metadata.source = 'ai_agent'`.
- **Tools:** read: `get_bookings`, `get_events`, `get_inventory_status`, `get_contacts`, `get_financial_summary`, `get_expenses_summary`, `search_inventory`. Propose (never write): `propose_expense`, `propose_receipt`, `propose_inventory_item`, `propose_inventory_purchase`, `propose_inventory_update`, `propose_stock_adjustment`.
- **Receipts:** each line of `propose_receipt` is `existing` (adds stock), `new` (item created at stock 0, then a `purchase` movement) or `expense` (variable expense) - never two at once. Confirmation uses `uuid5(action_id, line)` ids, so a retry after a partial failure does not duplicate anything.
- **Events:** `search_bookings` finds the event; `ask_choice` shows buttons (the turn ends, one question per turn); `propose_event_supplies` (estimate, no stock movement) and `propose_event_consumption` (deducts stock, replaces a previous consumption) only accept a `booking_id` that appears in a USER message (`user_said`), so the model cannot choose the event itself. `services/event_inventory_service.py` validates a consumption fully first and applies it in one atomic batch.
- **Bookings:** `propose_booking` creates a PENDING booking in the website's exact format through `services/booking_service.py` (single `calculate_estimated_price`). Confirming the proposal notifies the admin and partner (WhatsApp `new_booking`) and the admin (e-mail), never the customer; the agent has no tool to confirm, cancel or edit bookings (confirming notifies the customer and stays manual in the panel). `event_date` may be `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:00` (website): use `booking_search.event_day`.
- **WhatsApp channel:** `POST /api/whatsapp/webhook` (public; Twilio signature + allowlist, off unless `AI_WHATSAPP_ENABLED=true`) stores the message in `whatsapp_inbox`; the Firestore trigger `whatsapp_inbox_worker` (main.py) runs `run_chat` and answers via the Twilio API. Same propose -> confirm rule: the person confirms with SI/NO (`services/whatsapp_agent.py`). Setup and security in `docs/WHATSAPP_ASISTENTE.md`.
- **Shared logic:** `services/inventory_service.py` (items, weighted-average movements, atomic batch) is used by the HTTP routes in `main.py` and by the agent; `services/inventory_search.py` does fuzzy lookups.
- **Client history is untrusted:** `services/ai_chat_history.py` allows only user/assistant text and user images (≤3, last message only); the tool loop is capped at 8 iterations.
- **Images:** originals go to private `ai_uploads/{uid}/` in Storage (client access denied in `storage.rules`).
- **Model:** `claude-sonnet-5-5` with `anthropic==1.13.0`. No sampling params are sent (Sonnet 5.x rejects them; SDK 1.x dropped them). Thinking is adaptive and counts toward `max_tokens`.
- **Env:** `ADMIN_EMAILS`, `AI_CHAT_MODEL` (default `claude-sonnet-5-5`), `AI_CHAT_MAX_TOKENS` (8192), `AI_CHAT_EFFORT` (`medium`; empty = omit), `AI_CHAT_SERVER_FALLBACK` (`true`: beta `server-side-fallback-2026-07-01`, retries cyber/frontier_llm refusals; `false` = plain `messages.create`).
- **Tests:** `cd backend && pip install -r requirements-dev.txt && python -m pytest tests -q` (in-memory Firestore fake in `tests/fakes.py`).

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