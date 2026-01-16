import os  # Read environment variables and build filesystem paths
import io  # Wrap raw bytes in a stream for StreamingResponse
from datetime import datetime
from typing import Optional

import certifi  # Provides an up-to-date CA bundle (helps TLS in some serverless environments)
from bson import ObjectId  # MongoDB's native id type
from dotenv import load_dotenv  # Loads env vars from a .env file
from fastapi import FastAPI, File, UploadFile, HTTPException  # FastAPI core + file upload primitives
from fastapi.responses import StreamingResponse, JSONResponse  # Streams bytes back; JSONResponse for custom error handling
from pymongo.errors import ServerSelectionTimeoutError  # Raised when MongoDB can't be reached
from pydantic import BaseModel, EmailStr, Field  # Request validation + schema generation
import motor.motor_asyncio  # Async MongoDB driver (Motor)

# Load environment variables from .env file (from this project directory)
# This makes local development easy without hard-coding secrets into code.
_dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_dotenv_path)

# Create the FastAPI application (Swagger UI available at /docs)
app = FastAPI(title="Event Management API")


@app.exception_handler(ServerSelectionTimeoutError)
async def mongo_unavailable_handler(request, exc):
    # When Atlas cannot be reached (common on serverless if IPs aren't allowlisted or TLS fails),
    # return a clean 503 instead of a long stack trace.
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable (MongoDB connection failed). Check Atlas Network Access allowlist and MONGO_URI/MONGODB_URL.",
        },
    )

# Connect to MongoDB Atlas
# We support several env var names to avoid config issues from typos/variations.
mongo_uri = (
    os.getenv("MONGO_URI")
    or os.getenv("MONGO_URL")
    or os.getenv("MONGODB_URI")
    or os.getenv("MONGODB_URL")
    or os.getenv("mango_Url")
)
if not mongo_uri:
    # Fail fast on startup if the app can't connect to the database.
    raise RuntimeError(
        "Mongo connection string missing. Set MONGO_URI (recommended) or MONGODB_URL in your .env file."
    )

# Create the MongoDB client.
# In some serverless environments, explicitly providing a CA bundle helps prevent TLS handshake issues.
client = motor.motor_asyncio.AsyncIOMotorClient(
    mongo_uri,
    tls=True,
    tlsCAFile=certifi.where(),
)

# Reference the database that will store all API collections.
db = client.event_management_db  # must match your Atlas database name


# -------------------------
# Helpers
# -------------------------
def oid(id_str: str) -> ObjectId:
    """Validate and convert a string to MongoDB ObjectId."""
    # Protect endpoints like /events/{id} from invalid ObjectId values.
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid id format")
    return ObjectId(id_str)

def fix_id(doc: dict) -> dict:
    """Convert _id to string for JSON responses."""
    # MongoDB returns ObjectId, which is not JSON-serializable.
    doc["_id"] = str(doc["_id"])
    return doc


# -------------------------
# Data Models
# -------------------------
class Event(BaseModel):
    # Event data sent by clients for create/update.
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    venue_id: str = Field(..., min_length=1)
    max_attendees: int = Field(..., ge=1)

class Attendee(BaseModel):
    # Attendee information; EmailStr validates email format.
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = None

class Venue(BaseModel):
    # Venue information for events.
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    capacity: int = Field(..., ge=1)

class Booking(BaseModel):
    # Booking ties an attendee to an event with a ticket type and quantity.
    event_id: str = Field(..., min_length=1)
    attendee_id: str = Field(..., min_length=1)
    ticket_type: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)


# -------------------------
# Root
# -------------------------
@app.get("/")
async def root():
    # Simple health-check endpoint (useful for verifying the server is up).
    return {"status": "ok"}


# -------------------------
# EVENTS (CRUD)
# -------------------------
@app.post("/events")
async def create_event(event: Event):
    # Insert a new event document into the `events` collection.
    result = await db.events.insert_one(event.model_dump())
    return {"message": "Event created", "id": str(result.inserted_id)}

@app.get("/events")
async def list_events():
    # List up to 100 events.
    docs = await db.events.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/events/{id}")
async def get_event(id: str):
    # Find a single event by MongoDB ObjectId.
    doc = await db.events.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return fix_id(doc)

@app.put("/events/{id}")
async def update_event(id: str, event: Event):
    # Update fields for a given event by id.
    result = await db.events.update_one({"_id": oid(id)}, {"$set": event.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}

@app.delete("/events/{id}")
async def delete_event(id: str):
    # Delete an event by id.
    result = await db.events.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


# -------------------------
# ATTENDEES (CRUD)
# -------------------------
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    # Insert a new attendee into the `attendees` collection.
    result = await db.attendees.insert_one(attendee.model_dump())
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
async def list_attendees():
    # List up to 100 attendees.
    docs = await db.attendees.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/attendees/{id}")
async def get_attendee(id: str):
    # Find a single attendee by id.
    doc = await db.attendees.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return fix_id(doc)

@app.put("/attendees/{id}")
async def update_attendee(id: str, attendee: Attendee):
    # Update an attendee document by id.
    result = await db.attendees.update_one({"_id": oid(id)}, {"$set": attendee.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee updated"}

@app.delete("/attendees/{id}")
async def delete_attendee(id: str):
    # Delete an attendee by id.
    result = await db.attendees.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"message": "Attendee deleted"}


# -------------------------
# VENUES (CRUD)
# -------------------------
@app.post("/venues")
async def create_venue(venue: Venue):
    # Insert a new venue into the `venues` collection.
    result = await db.venues.insert_one(venue.model_dump())
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
async def list_venues():
    # List up to 100 venues.
    docs = await db.venues.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/venues/{id}")
async def get_venue(id: str):
    # Find a single venue by id.
    doc = await db.venues.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return fix_id(doc)

@app.put("/venues/{id}")
async def update_venue(id: str, venue: Venue):
    # Update a venue by id.
    result = await db.venues.update_one({"_id": oid(id)}, {"$set": venue.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue updated"}

@app.delete("/venues/{id}")
async def delete_venue(id: str):
    # Delete a venue by id.
    result = await db.venues.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"message": "Venue deleted"}


# -------------------------
# BOOKINGS (CRUD)
# -------------------------
@app.post("/bookings")
async def create_booking(booking: Booking):
    # Insert a new booking into the `bookings` collection.
    result = await db.bookings.insert_one(booking.model_dump())
    return {"message": "Booking created", "id": str(result.inserted_id)}

@app.get("/bookings")
async def list_bookings():
    # List up to 100 bookings.
    docs = await db.bookings.find().to_list(100)
    return [fix_id(d) for d in docs]

@app.get("/bookings/{id}")
async def get_booking(id: str):
    # Find a single booking by id.
    doc = await db.bookings.find_one({"_id": oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return fix_id(doc)

@app.put("/bookings/{id}")
async def update_booking(id: str, booking: Booking):
    # Update booking fields by id.
    result = await db.bookings.update_one({"_id": oid(id)}, {"$set": booking.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking updated"}

@app.delete("/bookings/{id}")
async def delete_booking(id: str):
    # Delete a booking by id.
    result = await db.bookings.delete_one({"_id": oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted"}


# -------------------------
# FILES: Upload + Retrieve (stream)
# -------------------------
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    # Read the uploaded file into memory (bytes).
    content = await file.read()
    # Store bytes + metadata in MongoDB.
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
    # Fetch the most recently uploaded poster for this event.
    doc = await db.event_posters.find_one({"event_id": event_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Poster not found")
    # Stream bytes back with the stored content type.
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])


@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    # Read the uploaded file into memory (bytes).
    content = await file.read()
    # Store bytes + metadata in MongoDB.
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
    # Fetch the most recently uploaded promo video for this event.
    doc = await db.promo_videos.find_one({"event_id": event_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Promo video not found")
    # Stream bytes back with the stored content type.
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])


@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    # Read the uploaded file into memory (bytes).
    content = await file.read()
    # Store bytes + metadata in MongoDB.
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
    # Fetch the most recently uploaded venue photo.
    doc = await db.venue_photos.find_one({"venue_id": venue_id}, sort=[("uploaded_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Venue photo not found")
    # Stream bytes back with the stored content type.
    return StreamingResponse(io.BytesIO(doc["content"]), media_type=doc["content_type"])
