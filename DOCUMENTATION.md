# Event Management API — Documentation

## Overview
This project is a **FastAPI** REST API backed by **MongoDB Atlas** using **Motor** (async MongoDB driver).

It supports:
- CRUD operations for:
  - Events
  - Attendees
  - Venues
  - Bookings
- File upload + retrieval (stored in MongoDB as raw bytes) for:
  - Event posters
  - Promo videos
  - Venue photos

The API is intended to be used via:
- Swagger UI: `http://127.0.0.1:8000/docs`
- Any HTTP client (Postman, curl, requests)

---

## Dependencies
Required (from the brief):
- `fastapi` — API framework
- `uvicorn` — ASGI server
- `motor` — async MongoDB client
- `pydantic` — validation / schemas
- `python-dotenv` — load `.env` variables
- `requests` — optional client library for testing from Python

Also required by this codebase:
- `python-multipart` — required for `UploadFile = File(...)` endpoints
- `email-validator` — required because `Attendee.email` uses `pydantic.EmailStr`

---

## MongoDB Connection
### Environment variables
- The API loads environment variables from a `.env` file located in the **project root**.
- Recommended variable:
  - `MONGO_URI=mongodb+srv://<user>:<password>@<cluster-host>/<db>?retryWrites=true&w=majority`

### Supported env keys
In `main.py`, the API tries the following in order:
- `MONGO_URI` (recommended)
- `MONGO_URL`
- `MONGODB_URI`
- `MONGODB_URL`
- `mango_Url` (legacy/typo support)

### Database name
The code connects to the MongoDB database:
- `event_management_db`

---

## Collections Used
The API stores documents in the following MongoDB collections:

- `events`
- `attendees`
- `venues`
- `bookings`

File storage collections:
- `event_posters`
- `promo_videos`
- `venue_photos`

---

## ObjectId Handling
MongoDB uses `_id` values of type `ObjectId`.

This API uses two helper behaviors:

1) **Validate and convert string → ObjectId**
- Incoming path parameters like `/events/{id}` are strings.
- The API validates the string using `ObjectId.is_valid(...)`.
- If invalid, it returns:
  - `400 Bad Request` with `{"detail": "Invalid id format"}`

2) **Convert ObjectId → string in responses**
- MongoDB returns `_id` as an `ObjectId`, which is not JSON serializable.
- The API converts it to a string before returning JSON.

---

## Data Models
The following Pydantic models represent request bodies for CRUD endpoints.

### Models Table

| Model | Fields | Validation Notes |
|---|---|---|
| `Event` | `name: str`, `description: str`, `date: str`, `venue_id: str`, `max_attendees: int` | All string fields must be non-empty (`min_length=1`). `max_attendees >= 1`. |
| `Attendee` | `name: str`, `email: EmailStr`, `phone: Optional[str]` | `name` non-empty. `email` must be valid email format (requires `email-validator`). `phone` optional. |
| `Venue` | `name: str`, `address: str`, `capacity: int` | `name/address` non-empty. `capacity >= 1`. |
| `Booking` | `event_id: str`, `attendee_id: str`, `ticket_type: str`, `quantity: int` | All string fields non-empty. `quantity >= 1`. |

Notes:
- IDs like `venue_id`, `event_id`, `attendee_id` are stored as **strings** in these documents (not enforced as ObjectId). If you want them to behave as ObjectIds, you must store/validate them consistently.

---

## API Endpoints
Base URL (local): `http://127.0.0.1:8000`

### Root

| Method | Path | Collection | Operation | Responses/Errors |
|---|---|---|---|---|
| GET | `/` | — | Health check | `200 {"status":"ok"}` |

---

## Events
### Endpoints Table

| Method | Path | Collection | Operation | Responses/Errors |
|---|---|---|---|---|
| POST | `/events` | `events` | Create event | `200` with created id; `422` validation |
| GET | `/events` | `events` | List events (max 100) | `200` list |
| GET | `/events/{id}` | `events` | Get by id | `200`; `400` invalid id; `404` not found |
| PUT | `/events/{id}` | `events` | Replace/update by id | `200`; `400` invalid id; `404` not found; `422` validation |
| DELETE | `/events/{id}` | `events` | Delete by id | `200`; `400` invalid id; `404` not found |

### Request/Response Notes
- POST/PUT body uses the `Event` model.
- Responses return MongoDB `_id` as a **string**.

---

## Attendees
### Endpoints Table

| Method | Path | Collection | Operation | Responses/Errors |
|---|---|---|---|---|
| POST | `/attendees` | `attendees` | Create attendee | `200` with created id; `422` validation |
| GET | `/attendees` | `attendees` | List attendees (max 100) | `200` list |
| GET | `/attendees/{id}` | `attendees` | Get by id | `200`; `400` invalid id; `404` not found |
| PUT | `/attendees/{id}` | `attendees` | Replace/update by id | `200`; `400` invalid id; `404` not found; `422` validation |
| DELETE | `/attendees/{id}` | `attendees` | Delete by id | `200`; `400` invalid id; `404` not found |

Notes:
- `email` must be a valid email string.

---

## Venues
### Endpoints Table

| Method | Path | Collection | Operation | Responses/Errors |
|---|---|---|---|---|
| POST | `/venues` | `venues` | Create venue | `200` with created id; `422` validation |
| GET | `/venues` | `venues` | List venues (max 100) | `200` list |
| GET | `/venues/{id}` | `venues` | Get by id | `200`; `400` invalid id; `404` not found |
| PUT | `/venues/{id}` | `venues` | Replace/update by id | `200`; `400` invalid id; `404` not found; `422` validation |
| DELETE | `/venues/{id}` | `venues` | Delete by id | `200`; `400` invalid id; `404` not found |

---

## Bookings
### Endpoints Table

| Method | Path | Collection | Operation | Responses/Errors |
|---|---|---|---|---|
| POST | `/bookings` | `bookings` | Create booking | `200` with created id; `422` validation |
| GET | `/bookings` | `bookings` | List bookings (max 100) | `200` list |
| GET | `/bookings/{id}` | `bookings` | Get by id | `200`; `400` invalid id; `404` not found |
| PUT | `/bookings/{id}` | `bookings` | Replace/update by id | `200`; `400` invalid id; `404` not found; `422` validation |
| DELETE | `/bookings/{id}` | `bookings` | Delete by id | `200`; `400` invalid id; `404` not found |

---

## File Storage and Retrieval
The API stores uploaded files directly inside MongoDB documents.

### Upload behavior
- Upload endpoints accept **multipart/form-data**.
- The file must be sent under the form key:
  - `file`
- The server reads bytes using:
  - `content = await file.read()`

### Storage format
Uploaded file bytes are stored in MongoDB as:
- `content` — raw bytes
- `filename` — original name
- `content_type` — MIME type (e.g., `image/png`, `video/mp4`)
- `uploaded_at` — UTC timestamp
- plus an association field:
  - `event_id` for event poster and promo video
  - `venue_id` for venue photo

### Retrieval behavior
- Retrieval endpoints query for the latest file by:
  - sorting `uploaded_at` descending
- The bytes are streamed back with:
  - `StreamingResponse(io.BytesIO(content), media_type=content_type)`

This allows the browser/client to render or download the content using the stored MIME type.

---

## File Endpoints
### Summary Table

| Type | Upload POST | Collection | Retrieve GET | Notes |
|---|---|---|---|---|
| Event Poster | `/upload_event_poster/{event_id}` | `event_posters` | `/event_poster/{event_id}` | Retrieves most recent by `uploaded_at` |
| Promo Video | `/upload_promo_video/{event_id}` | `promo_videos` | `/promo_video/{event_id}` | Retrieves most recent by `uploaded_at` |
| Venue Photo | `/upload_venue_photo/{venue_id}` | `venue_photos` | `/venue_photo/{venue_id}` | Retrieves most recent by `uploaded_at` |

---

## Error Handling
Typical errors you should expect:

- **400 Bad Request**
  - When an id path parameter is not a valid ObjectId string.
  - Response body: `{"detail": "Invalid id format"}`

- **404 Not Found**
  - When a document is not found for a valid ObjectId.
  - Example: `{"detail": "Event not found"}`

- **422 Unprocessable Entity**
  - Automatic FastAPI/Pydantic validation failure for request bodies.

- **500 Internal Server Error**
  - Unexpected failures (e.g., MongoDB outages, authentication issues, unhandled exceptions).

---

## Testing
### Using Swagger UI
1. Start server:
   - `source .venv/bin/activate`
   - `uvicorn main:app --reload`
2. Open:
   - `http://127.0.0.1:8000/docs`
3. Use **Try it out** on endpoints.

### Typical CRUD flow (example)
For a resource like **events**:
1. `POST /events`
2. `GET /events` (confirm it appears)
3. `GET /events/{id}`
4. `PUT /events/{id}`
5. `DELETE /events/{id}`

Repeat similarly for attendees, venues, and bookings.

### File upload testing (Postman or Swagger UI)
- Choose the upload endpoint (e.g., `POST /upload_event_poster/{event_id}`)
- Set request type to **multipart/form-data**
- Add key:
  - `file` (type: File)
- Send request, then retrieve with the matching `GET` endpoint.

---

## Running the API
From the project root:
- `source .venv/bin/activate`
- `uvicorn main:app --reload --host 127.0.0.1 --port 8000`

Docs:
- `http://127.0.0.1:8000/docs`
