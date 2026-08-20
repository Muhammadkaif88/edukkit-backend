import os
from pydantic_settings import BaseSettings

# Find backend root directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./edukkit.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "yoursecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Razorpay
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "test_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "test_secret")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # Cashfree Payment Gateway
    CASHFREE_ENV: str = os.getenv("CASHFREE_ENV", "sandbox")  # "sandbox" or "production"
    CASHFREE_CLIENT_ID: str = os.getenv("CASHFREE_CLIENT_ID", "TEST_CLIENT_ID")
    CASHFREE_CLIENT_SECRET: str = os.getenv("CASHFREE_CLIENT_SECRET", "TEST_CLIENT_SECRET")
    CASHFREE_API_VERSION: str = os.getenv("CASHFREE_API_VERSION", "2023-08-01")
    CASHFREE_WEBHOOK_SECRET: str = os.getenv("CASHFREE_WEBHOOK_SECRET", "")
    CASHFREE_RETURN_URL: str = os.getenv("CASHFREE_RETURN_URL", "https://edukkit.com/payment-response?order_id={order_id}")
    CASHFREE_NOTIFY_URL: str = os.getenv("CASHFREE_NOTIFY_URL", "https://api.edukkit.com/api/payments/cashfree/webhook")

    # Delivery Fee Rules
    DELIVERY_FEE_KERALA: float = 70.0
    DELIVERY_FEE_OUTSIDE_KERALA: float = 100.0

    # Bunny Stream
    BUNNY_SECURITY_KEY: str = os.getenv("BUNNY_SECURITY_KEY", "bunnysign_test_key")
    BUNNY_LIBRARY_ID: str = os.getenv("BUNNY_LIBRARY_ID", "123456")
    BUNNY_CDN_HOSTNAME: str = os.getenv("BUNNY_CDN_HOSTNAME", "vz-abcd-123.b-cdn.net")
    # Bunny Stream API key for video management (create/upload/delete) — server-side ONLY
    BUNNY_API_KEY: str = os.getenv("BUNNY_API_KEY", "")
    # Bunny webhook secret for validating incoming processing status callbacks
    BUNNY_WEBHOOK_SECRET: str = os.getenv("BUNNY_WEBHOOK_SECRET", "")


    class Config:
        env_file = ENV_PATH
        extra = "allow"


settings = Settings()
