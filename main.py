import os
import io
from datetime import datetime
from typing import Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
import motor.motor_asyncio

# Load environment variables from .env file (from this project directory)
_dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_dotenv_path)

app = FastAPI(title="Event Management API")

# Connect to MongoDB Atlas
mongo_uri = (
    os.getenv("MONGO_URI")
    or os.getenv("MONGO_URL")
    or os.getenv("MONGODB_URI")
    or os.getenv("MONGODB_URL")
    or os.getenv("mango_Url")
)
if not mongo_uri:
    raise RuntimeError(
        "Mongo connection string missing. Set MONGO_URI (recommended) or MONGODB_URL in your .env file."
    )

client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
db = client.event_management_db  # must match your Atlas database name


# -------------------------
# Helpers
# -------------------------
def oid(id_str: str) -> ObjectId:
    """Validate and convert a string to MongoDB ObjectId."""
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid id format")
    return ObjectId(id_str)

def fix_id(doc: dict) -> dict:
    """Convert _id to string for JSON responses."""
    doc["_id"] = str(doc["_id"])
    return doc


# -------------------------
# Data Models
# -------------------------
class Event(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    venue_id: str = Field(..., min_length=1)
    max_attendees: int = Field(..., ge=1)

class Attendee(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = None

class Venue(BaseModel):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    capacity: int = Field(..., ge=1)

class Booking(BaseModel):
    event_id: str = Field(..., min_length=1)
    attendee_id: str = Field(..., min_length=1)
    ticket_type: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)


# -------------------------
# Root
# -------------------------
@app.get("/")
async def root():
    return {"status": "ok"}


# -------------------------
# EVENTS (CRUD)
# -------------------------
@app.post("/events")
async def create_event(event: Event):
    result = await db.events.insert_one(event.model_dump())
    return {"message": "Event created", "id": str(result.inserted_id)}

@app.get("/events")
async def list_events():
    docs = await db.events.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/events/{id}")
async def get_event(id: str):
    doc = await db.events.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return fix_id(doc)

@app.put("/events/{id}")
async def update_event(id: str, event: Event):
    result = await db.events.update_one({"_id": oid(id)}, {"$set": event.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}

@app.delete("/events/{id}")
async def delete_event(id: str):
    result = await db.events.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


# -------------------------
# ATTENDEES (CRUD)
# -------------------------
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    result = await db.attendees.insert_one(attendee.model_dump())
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
async def list_attendees():
    docs = await db.attendees.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/attendees/{id}")
async def get_attendee(id: str):
    doc = await db.attendees.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return fix_id(doc)

@app.put("/attendees/{id}")
async def update_attendee(id: str, attendee: Attendee):
    result = await db.attendees.update_one({"_id": oid(id)}, {"$set": attendee.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee updated"}

@app.delete("/attendees/{id}")
async def delete_attendee(id: str):
    result = await db.attendees.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee deleted"}


# -------------------------
# VENUES (CRUD)
# -------------------------
@app.post("/venues")
async def create_venue(venue: Venue):
    result = await db.venues.insert_one(venue.model_dump())
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
async def list_venues():
    docs = await db.venues.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/venues/{id}")
async def get_venue(id: str):
    doc = await db.venues.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return fix_id(doc)

@app.put("/venues/{id}")
async def update_venue(id: str, venue: Venue):
    result = await db.venues.update_one({"_id": oid(id)}, {"$set": venue.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue updated"}

@app.delete("/venues/{id}")
async def delete_venue(id: str):
    result = await db.venues.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue deleted"}


# -------------------------
# BOOKINGS (CRUD)
# -------------------------
@app.post("/bookings")
async def create_booking(booking: Booking):
    result = await db.bookings.insert_one(booking.model_dump())
    return {"message": "Booking created", "id": str(result.inserted_id)}

@app.get("/bookings")
async def list_bookings():
    docs = await db.bookings.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/bookings/{id}")
async def get_booking(id: str):
    doc = await db.bookings.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return fix_id(doc)

@app.put("/bookings/{id}")
async def update_booking(id: str, booking: Booking):
    result = await db.bookings.update_one({"_id": oid(id)}, {"$set": booking.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking updated"}

@app.delete("/bookings/{id}")
async def delete_booking(id: str):
    result = await db.bookings.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted"}


# -------------------------
# FILES: Upload + Retrieve (stream)
# -------------------------
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    content = await file.read()
    doc = {
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow(),
    }
    result = await db.event_posters.insert_one(doc)
    return {"message": "Event poster uploaded", "id": str(result.inserted_id)}

@app.get("/event_poster/{event_id}")
async def get_event_poster(event_id: str):
    doc = await db.event_posters.find_one({"event_id": event_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Poster not found")
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])


@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    content = await file.read()
    doc = {
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow(),
    }
    result = await db.promo_videos.insert_one(doc)
    return {"message": "Promo video uploaded", "id": str(result.inserted_id)}

@app.get("/promo_video/{event_id}")
async def get_promo_video(event_id: str):
    doc = await db.promo_videos.find_one({"event_id": event_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Promo video not found")
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])


@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    content = await file.read()
    doc = {
        "venue_id": venue_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow(),
    }
    result = await db.venue_photos.insert_one(doc)
    return {"message": "Venue photo uploaded", "id": str(result.inserted_id)}

@app.get("/venue_photo/{venue_id}")
async def get_venue_photo(venue_id: str):
    doc = await db.venue_photos.find_one({"venue_id": venue_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Venue photo not found")
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])
