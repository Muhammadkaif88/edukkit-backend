import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import auth, courses, products, payments, video, learning, admin, admin_videos

from sqlalchemy import text
from .models import (  # noqa: F401
    User, Course, Lesson, Product, Order, OrderItem,
    Payment, PaymentEvent, CourseEntitlement, UserAddress,
)

# Create tables
Base.metadata.create_all(bind=engine)

def run_startup_migrations():
    """Ensure newly added columns exist in older database instances."""
    migrations = [
        # --- orders table ---
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracking_number VARCHAR;",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_region VARCHAR DEFAULT 'Digital/DIY';",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_fee_rule VARCHAR DEFAULT 'FREE_DELIVERY';",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_amount FLOAT DEFAULT 0.0;",
        # Cashfree gateway columns
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cashfree_order_id VARCHAR;",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cashfree_session_id VARCHAR;",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cashfree_payment_id VARCHAR;",
        # Razorpay gateway columns
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR;",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR;",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS razorpay_signature VARCHAR;",
        # Other order metadata
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR DEFAULT 'Cashfree Online';",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_attempt_count INTEGER DEFAULT 1;",
        # user_id may have been added later
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS user_id VARCHAR;",
        # --- users table ---
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS approval_status VARCHAR DEFAULT 'pending';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image VARCHAR;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;",
        # --- courses table ---
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS original_price FLOAT;",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS short_description VARCHAR;",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS bunny_collection_id VARCHAR;",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS teacher_id INTEGER;",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_free BOOLEAN DEFAULT FALSE;",
        # --- lessons table ---
        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS notes_pdf VARCHAR;",
        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS circuit_diagram VARCHAR;",
        # --- products table ---
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS original_price FLOAT;",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS type VARCHAR DEFAULT 'diy_kit';",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS linked_course_id INTEGER;",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass

try:
    run_startup_migrations()
except Exception:
    pass

app = FastAPI(title="EdukkitApp API", version="2.0.0")

# Configure CORS origins based on environment
app_env = os.getenv("APP_ENV", "development").lower()
cors_origins_env = os.getenv("CORS_ORIGINS", "")

# Base origins always permitted
default_origins = [
    "https://admin.edukkit.com",
    "https://edukkit.com",
    "https://www.edukkit.com",
    "http://localhost",
    "http://127.0.0.1",
]

if cors_origins_env:
    origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    for o in default_origins:
        if o not in origins:
            origins.append(o)
else:
    origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(payments.router, prefix="/api/payments/cashfree", tags=["payments"])
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(learning.router, prefix="/api/my-learning", tags=["learning"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_videos.router, prefix="/api/admin/videos", tags=["admin-videos"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Edukkit API", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "env": app_env}

