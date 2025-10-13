"""
Firebase Database Configuration
Centralized database connection with lazy loading
"""
import os
import firebase_admin
from firebase_admin import firestore, storage
import logging

logger = logging.getLogger(__name__)

# Global database client
_db = None
_storage_bucket = None


def get_db():
    """
    Get Firebase Firestore client with lazy initialization

    Returns:
        firestore.Client: Initialized Firestore client or None if initialization fails
    """
    global _db

    if _db is None:
        if not firebase_admin._apps:
            try:
                # Check if running in local development
                service_account_path = os.path.join(os.path.dirname(__file__), 'ServiceAccount.json')
                is_local = os.path.exists(service_account_path)

                if is_local:
                    logger.info("🔧 LOCAL: Using service account credentials")
                    from firebase_admin import credentials
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': 'pablospizza-d84bf.firebasestorage.app'
                    })
                else:
                    # Production environment - use Application Default Credentials
                    logger.info("☁️ PRODUCTION: Using default Firebase credentials")
                    firebase_admin.initialize_app(options={
                        'storageBucket': 'pablospizza-d84bf.firebasestorage.app'
                    })

            except Exception as e:
                logger.error(f"CRITICAL: Firebase initialization failed: {e}", exc_info=True)
                import traceback
                traceback.print_exc()
                return None

        _db = firestore.client()
        logger.info("✅ Firestore client initialized successfully")

    return _db


def get_storage_bucket():
    """
    Get Firebase Storage bucket with lazy initialization

    Returns:
        storage.bucket: Initialized Storage bucket or None if initialization fails
    """
    global _storage_bucket

    if _storage_bucket is None:
        try:
            # Ensure Firebase is initialized
            if not firebase_admin._apps:
                get_db()  # This will initialize Firebase

            _storage_bucket = storage.bucket()
            logger.info("✅ Storage bucket initialized successfully")

        except Exception as e:
            logger.error(f"CRITICAL: Storage bucket initialization failed: {e}", exc_info=True)
            return None

    return _storage_bucket
