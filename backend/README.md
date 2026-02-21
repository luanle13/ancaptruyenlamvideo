# AnCapTruyenLamVideo Backend

FastAPI backend application for AnCapTruyenLamVideo.

## Tech Stack

- Python 3.10+
- FastAPI
- Motor (async MongoDB driver)
- Pydantic
- Uvicorn (ASGI server)

## Prerequisites

- Python 3.10 or higher
- pip
- MongoDB (Atlas or local)

## Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB connection string
   ```

## Running the Server

Development mode (with auto-reload):
```bash
uvicorn app.main:app --reload --port 8000
```

Production mode:
```bash
uvicorn app.main:app --port 8000
```

## API Documentation

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```
backend/
├── app/
│   ├── models/          # Pydantic models/schemas
│   ├── routes/          # API route handlers
│   ├── services/        # Business logic layer
│   ├── config.py        # Configuration settings
│   ├── database.py      # MongoDB connection
│   └── main.py          # FastAPI app entry point
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories` | List all stories |
| GET | `/api/stories/{id}` | Get a single story |
| POST | `/api/stories` | Create a new story |
| PUT | `/api/stories/{id}` | Update a story |
| DELETE | `/api/stories/{id}` | Delete a story |
| GET | `/health` | Health check |

## Further Help

For the full setup guide, refer to the main [README.md](../README.md) in the project root.
