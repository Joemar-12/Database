# AssignmentDatabase — Environment Setup

This repository contains a FastAPI + MongoDB Atlas (Motor) Event Management API.

## Prerequisites
- **Python 3.9+**
- A **MongoDB Atlas** cluster and a database user

## 1) Create + activate the virtual environment
From the project folder:

```bash
cd ~/Desktop/AssignmentDatabase

python3 -m venv .venv
source .venv/bin/activate
```

## 2) Install dependencies
Option A (recommended): install from `requirements.txt`

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Option B (manual install — if required by your brief)

```bash
pip install --upgrade pip
pip install fastapi uvicorn motor pydantic python-dotenv requests
# Needed by this project’s code:
pip install python-multipart email-validator

pip freeze > requirements.txt
```

## 3) Configure environment variables (`.env`)
Create a `.env` file in the project root (this repo already ignores it via `.gitignore`).

Your project supports these keys:
- `MONGO_URI` (recommended)
- `MONGODB_URL` (also supported)

Example:

```env
MONGODB_URL=mongodb+srv://<USERNAME>:<PASSWORD>@<CLUSTER_HOST>/<DB_NAME>?retryWrites=true&w=majority
```

Notes:
- If your password contains special characters (`@`, `:`, `/`, `?`, `#`, etc.), URL-encode it.

## 4) Quick test: MongoDB connection (ping)
Run this from the project folder:

```bash
source .venv/bin/activate

python - <<'PY'
from dotenv import dotenv_values
import asyncio
import motor.motor_asyncio

env = dotenv_values('.env')
uri = (
    env.get('MONGO_URI')
    or env.get('MONGO_URL')
    or env.get('MONGODB_URI')
    or env.get('MONGODB_URL')
    or env.get('mango_Url')
)

print('Mongo URI set:', bool(uri))
if uri:
    print('Host:', uri.split('@')[-1].split('/')[0])

async def main():
    if not uri:
        raise SystemExit('❌ Missing Mongo URI in .env')

    client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command('ping')
        print('✅ Mongo ping OK')
    finally:
        client.close()

asyncio.run(main())
PY
```

## 5) Run the API

```bash
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:
- Swagger docs: http://127.0.0.1:8000/docs

## Common issues
- **Port already in use** (8000): stop the existing process or restart VS Code terminal.
- **Authentication failed**: check Atlas Database Access username/password and that your IP is allowed in Atlas Network Access.
