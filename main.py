import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Imagify.art API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3)
    art_type: Optional[str] = None
    style: Optional[str] = None
    aspect: Optional[str] = None  # e.g., "1:1", "16:9"
    resolution: Optional[str] = "512×512"  # e.g., "512×512"
    model: Optional[str] = "Pollination AI"
    count: int = Field(default=6, ge=1, le=9)


class GenerateResponse(BaseModel):
    images: List[str]


@app.get("/")
def read_root():
    return {"message": "Imagify.art Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Simple helper to compute width/height from aspect + resolution
ASPECT_MAP = {
    "1:1": (1, 1),
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3": (4, 3),
}


def parse_resolution(res: str) -> int:
    # Expect formats like "512×512" or "1024×1024"; return base size (first number)
    for sep in ["×", "x", "X", "*"]:
        if sep in res:
            try:
                return int(res.split(sep)[0])
            except Exception:
                break
    try:
        return int(res)
    except Exception:
        return 512


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_images(payload: GenerateRequest):
    if not payload.prompt or len(payload.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail="Prompt is too short.")

    # Determine width/height
    base = parse_resolution(payload.resolution or "512×512")
    aspect_key = payload.aspect or "1:1"
    rat = ASPECT_MAP.get(aspect_key, (1, 1))
    # Normalize so that the smallest side equals `base`
    if rat[0] >= rat[1]:
        height = base
        width = int(base * (rat[0] / rat[1]))
    else:
        width = base
        height = int(base * (rat[1] / rat[0]))

    # Build Pollinations public URLs (no key required)
    # Using multiple seeds to get multiple images deterministically
    prompt_clean = payload.prompt.strip()
    images: List[str] = []
    for i in range(payload.count):
        seed = 1000 + i
        url = (
            f"https://image.pollinations.ai/prompt/{prompt_clean}"
            f"?width={min(width, 1536)}&height={min(height, 1536)}&seed={seed}&nologo=true"
        )
        images.append(url)

    return GenerateResponse(images=images)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
