# Edukkit FastAPI Backend

Production REST API powering the Edukkit learning platform, mobile applications, and administration web portal.

## Tech Stack
- **Framework:** FastAPI
- **Server:** Uvicorn
- **ORM & Database:** SQLAlchemy 2.0 with PostgreSQL (Supabase) / SQLite (Dev)
- **Migrations:** Alembic
- **Authentication:** Firebase Admin SDK (Cryptographic ID Token Verification & RBAC)
- **Video Infrastructure:** Bunny Stream CDN (Direct TUS Ingest & Signed Token Playback)
- **Payments:** Cashfree Payment Gateway (Webhook Verification & Automatic Entitlements)

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file (see production configuration documentation):
```ini
APP_ENV=development
DATABASE_URL=sqlite:///./edukkit.db
SECRET_KEY=your_secret_key
```

### 3. Apply Database Migrations
```bash
alembic upgrade head
```

### 4. Seed Catalog Data (Optional)
```bash
python seed.py
```

### 5. Start Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Production Deployment (Render)
- **Build Command:** `pip install -r requirements.txt`
- **Pre-deploy Command:** `alembic upgrade head`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health` or `/`
