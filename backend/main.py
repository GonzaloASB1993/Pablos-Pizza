from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from decouple import config

# Routers
from routers import bookings, events, gallery, reviews, inventory, reports, notifications, chat

app = FastAPI(
    title="Pablo's Pizza API",
    description="API para la gestión de talleres de pizza y eventos",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase initialization
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-service-account.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
security = HTTPBearer()

# Middleware para verificar token de Firebase
async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

# Include routers
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(gallery.router, prefix="/api/gallery", tags=["gallery"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Pablo's Pizza API - ¡Bienvenido!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Pablo's Pizza API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)