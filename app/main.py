from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routes import router
#Create all tables on startup (safe: skips if they exist)
Base.metadata.create_all(bind=engine)

# FastAPI app 
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Order & Checkout Service

Handles the full order lifecycle:
- Checkout: Move cart items → create order atomically
- Order details: Fetch a single order with all line items
- Order history: Paginated order list with filters
- Status management: Update order through its lifecycle states
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Routers 
app.include_router(router, prefix="/api/v1")

#  Health check 
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}

#  Root 
@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Order & Checkout Service",
        "docs": "/docs",
        "health": "/health",
    }
