from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, firestore, auth
from firebase_functions import https_fn
import os
from dotenv import load_dotenv

# Load environment variables
# En producción (Firebase Functions), usar .env.production
env_file = '.env.production' if os.getenv('ENVIRONMENT') == 'production' else '.env'
load_dotenv(env_file)

app = FastAPI(
    title="Pablo's Pizza API",
    description="API para la gestión de talleres de pizza y eventos",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pablospizza.web.app",
        "https://pablospizza.firebaseapp.com",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase initialization
if not firebase_admin._apps:
    # Verificar si existe el archivo de credenciales
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'ServiceAccount.json')
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'pablospizza-d84bf.appspot.com'
        })
    else:
        # Fallback para desarrollo sin credenciales
        firebase_admin.initialize_app()

db = firestore.client()
security = HTTPBearer()

# Import routers AFTER Firebase initialization
from routers import bookings, events, gallery, reviews, inventory, reports, notifications, chat

# Middleware para verificar token de Firebase (opcional para rutas públicas)
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

# Firebase Function
@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    """Firebase Function entry point"""
    import asyncio
    from asgi_lifespan import LifespanManager
    from mangum import Mangum

    handler = Mangum(app, lifespan="off")
    return handler(req, None)