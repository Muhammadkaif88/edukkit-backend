import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import auth, courses, products, payments, video, learning, admin, admin_videos

# Import all models so SQLAlchemy creates all tables on startup
from .models import (  # noqa: F401
    User, Course, Lesson, Product, Order, OrderItem,
    Payment, PaymentEvent, CourseEntitlement, UserAddress,
)

# Create tables
Base.metadata.create_all(bind=engine)

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

