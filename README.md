# AnCapTruyenLamVideo

A full-stack web application that automatically crawls manga from truyenqqno.com, generates Vietnamese story narration using AI, creates videos with text-to-speech, and uploads to YouTube.

## Features

- **Manga Crawler** - Automatically crawl and download manga images from truyenqqno.com
- **AI Story Generation** - Convert manga panels to Vietnamese story narration using Qwen3-VL via DeepInfra
- **Text-to-Speech** - Generate Vietnamese audio narration using Edge TTS
- **Video Generation** - Create videos combining manga images with audio narration using FFmpeg
- **YouTube Upload** - Automatically upload generated videos to YouTube
- **Telegram Bot** - Trigger the pipeline via Telegram by sending a manga URL
- **Real-time Progress** - Track progress via Server-Sent Events (SSE)

## Tech Stack

- **Frontend:** Angular 21+ with PrimeNG component library
- **Backend:** Python FastAPI
- **Database:** MongoDB (supports both MongoDB Atlas and local installation)
- **AI:** Qwen3-VL via DeepInfra API
- **TTS:** Microsoft Edge TTS
- **Video:** FFmpeg

---

## Prerequisites

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| **Node.js** | v18.x or higher | [Download Node.js](https://nodejs.org/) |
| **Python** | 3.10 or higher | [Download Python](https://www.python.org/downloads/) |
| **FFmpeg** | Latest | [Download FFmpeg](https://ffmpeg.org/download.html) |
| **MongoDB** | 6.0+ | [MongoDB Atlas](https://www.mongodb.com/atlas) (recommended) or local |

---

## Project Structure

```
AnCapTruyenLamVideo/
├── frontend/                    # Angular + PrimeNG application
│   ├── src/app/
│   │   ├── components/
│   │   │   └── manga-crawler/   # Main crawler UI
│   │   ├── services/            # API & SSE services
│   │   └── models/              # TypeScript interfaces
│   └── ...
│
├── backend/                     # FastAPI Python application
│   ├── app/
│   │   ├── models/              # Pydantic models
│   │   ├── routes/
│   │   │   ├── crawler.py       # Crawler API endpoints
│   │   │   └── youtube.py       # YouTube OAuth endpoints
│   │   ├── services/
│   │   │   ├── crawler.py       # Main orchestrator
│   │   │   ├── scraper.py       # Web scraping
│   │   │   ├── image_downloader.py
│   │   │   ├── ai_processor.py  # Qwen3-VL integration
│   │   │   ├── tts_service.py   # Edge TTS
│   │   │   ├── video_generator.py
│   │   │   ├── youtube_uploader.py
│   │   │   └── telegram_bot.py
│   │   ├── utils/
│   │   │   └── event_bus.py     # SSE event broadcasting
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── content/                 # Generated scripts (gitignored)
│   ├── images/                  # Downloaded images (gitignored)
│   ├── videos/                  # Generated videos (gitignored)
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

---

## Setup & Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd AnCapTruyenLamVideo
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `.env` with your settings:

```env
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DATABASE_NAME=ancaptruyenlamvideo_db

# DeepInfra API (for AI processing)
DEEPINFRA_API_KEY=your_deepinfra_api_key

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ENABLED=true

# YouTube Upload (optional)
YOUTUBE_ENABLED=true
YOUTUBE_DEFAULT_PRIVACY=private
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 3: Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Step 4: Access the Application

- **Frontend:** http://localhost:4200
- **API Docs:** http://localhost:8000/docs

---

## Configuration

### DeepInfra API

1. Sign up at [deepinfra.com](https://deepinfra.com)
2. Get your API key
3. Add to `.env`: `DEEPINFRA_API_KEY=your_key`

### Telegram Bot (Optional)

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get the bot token
3. Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token`
4. Send a manga URL to your bot to trigger the pipeline

### YouTube Upload (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable "YouTube Data API v3"
3. Create OAuth 2.0 credentials (Web application)
4. Add redirect URI: `http://localhost:8000/api/youtube/auth/callback`
5. Download `client_secrets.json` to `backend/` folder
6. In the web UI, click "Connect YouTube" to authenticate

---

## API Endpoints

### Crawler

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/crawler/tasks` | Create and start a crawl task |
| GET | `/api/crawler/tasks` | List all tasks |
| GET | `/api/crawler/tasks/{id}` | Get task details |
| GET | `/api/crawler/tasks/{id}/events` | SSE progress stream |
| POST | `/api/crawler/tasks/{id}/cancel` | Cancel a running task |
| GET | `/api/crawler/content/{id}` | List generated scripts |
| GET | `/api/crawler/videos/{id}` | List generated videos |

### YouTube

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/youtube/status` | Check auth status |
| GET | `/api/youtube/auth/start` | Start OAuth flow |
| POST | `/api/youtube/auth/revoke` | Disconnect YouTube |

---

## Pipeline Workflow

1. **Input** - User provides manga URL (via web UI or Telegram)
2. **Crawl Chapters** - Scrape chapter list from manga page
3. **Download Images** - Download all manga panel images
4. **AI Processing** - Send images to Qwen3-VL to generate Vietnamese story
5. **Text-to-Speech** - Convert story text to Vietnamese audio
6. **Video Generation** - Combine images + audio into MP4 video
7. **YouTube Upload** - Auto-upload to YouTube (if configured)
8. **Notification** - Notify user via Telegram (if configured)

---

## Development Mode

In development mode, only the first 5 chapters are processed for faster testing.

Set in `.env`:
```env
ENVIRONMENT=development
```

For production (process all chapters):
```env
ENVIRONMENT=production
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Database name | `ancaptruyenlamvideo_db` |
| `DEEPINFRA_API_KEY` | DeepInfra API key for AI | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Optional |
| `TELEGRAM_ENABLED` | Enable Telegram bot | `true` |
| `YOUTUBE_ENABLED` | Enable YouTube upload | `true` |
| `YOUTUBE_DEFAULT_PRIVACY` | Video privacy (private/unlisted/public) | `private` |
| `ENVIRONMENT` | development or production | `development` |

---

## Troubleshooting

### FFmpeg not found
- Install FFmpeg and ensure it's in your system PATH
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

### YouTube API Error 403
- Enable "YouTube Data API v3" in Google Cloud Console
- Wait a few minutes after enabling for propagation

### AI Processing Too Slow
- DeepInfra API processes 20 images per request
- Large manga may take 10-30 minutes

### Video Generation Stuck
- Check FFmpeg is installed correctly
- Large videos (800+ images) may take 15-30 minutes
- Check logs for progress updates

---

## License

This project is for educational and development purposes.
