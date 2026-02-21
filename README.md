# AnCapTruyenLamVideo

A full-stack web application for managing stories, built with modern technologies.

## Tech Stack

- **Frontend:** Angular 21+ with PrimeNG component library
- **Backend:** Python FastAPI
- **Database:** MongoDB (supports both MongoDB Atlas and local installation)

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| **Node.js** | v18.x or higher | [Download Node.js](https://nodejs.org/) |
| **npm** | v9.x or higher | Comes with Node.js |
| **Angular CLI** | v17+ | `npm install -g @angular/cli` |
| **Python** | 3.10 or higher | [Download Python](https://www.python.org/downloads/) |
| **pip** | Latest | Comes with Python |
| **Git** | Latest | [Download Git](https://git-scm.com/) |

### MongoDB (Choose One Option)

You need **one** of the following MongoDB setups:

#### Option A: MongoDB Atlas (Cloud - Recommended for Quick Start)
- Free tier available
- No local installation required
- Sign up at [mongodb.com/atlas](https://www.mongodb.com/atlas)

#### Option B: Local MongoDB
- MongoDB Community Edition installed locally
- Installation guides:
  - [Windows](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/)
  - [macOS](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/)
  - [Linux](https://www.mongodb.com/docs/manual/administration/install-on-linux/)

---

## Project Structure

```
AnCapTruyenLamVideo/
├── frontend/                    # Angular + PrimeNG application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/     # Angular components
│   │   │   ├── models/         # TypeScript interfaces
│   │   │   ├── services/       # API services
│   │   │   └── ...
│   │   ├── environments/       # Environment configs
│   │   └── ...
│   ├── angular.json
│   ├── package.json
│   └── proxy.conf.json         # API proxy config
│
├── backend/                     # FastAPI Python application
│   ├── app/
│   │   ├── models/             # Pydantic models
│   │   ├── routes/             # API route handlers
│   │   ├── services/           # Business logic
│   │   ├── config.py           # Configuration
│   │   ├── database.py         # MongoDB connection
│   │   └── main.py             # FastAPI entry point
│   ├── requirements.txt
│   └── .env.example
│
├── README.md
└── .gitignore
```

---

## Database Setup

### Option A: MongoDB Atlas (Cloud) - Recommended for Quick Start

1. **Create a free MongoDB Atlas account**
   - Go to [mongodb.com/atlas](https://www.mongodb.com/atlas)
   - Sign up for a free account

2. **Create a free-tier cluster**
   - Click "Build a Database"
   - Select "M0 FREE" tier
   - Choose a cloud provider and region
   - Click "Create Cluster"

3. **Create a database user**
   - Go to "Database Access" in the left sidebar
   - Click "Add New Database User"
   - Choose "Password" authentication
   - Enter a username and password (save these!)
   - Click "Add User"

4. **Whitelist your IP address**
   - Go to "Network Access" in the left sidebar
   - Click "Add IP Address"
   - For development, click "Allow Access from Anywhere" (adds `0.0.0.0/0`)
   - Click "Confirm"

5. **Get your connection string**
   - Go to "Database" in the left sidebar
   - Click "Connect" on your cluster
   - Select "Connect your application"
   - Choose "Python" as the driver
   - Copy the connection string (looks like: `mongodb+srv://username:<password>@cluster.xxxxx.mongodb.net/...`)

6. **Configure the connection string**
   - Replace `<password>` with your actual password
   - Replace `<username>` if different
   - You'll use this string in the backend `.env` file

### Option B: Local MongoDB

1. **Install MongoDB Community Edition**
   - Follow the installation guide for your operating system (links in Prerequisites)

2. **Start MongoDB**

   **macOS/Linux:**
   ```bash
   # Using brew (macOS)
   brew services start mongodb-community

   # Or manually
   mongod --dbpath /path/to/data/db
   ```

   **Windows:**
   ```bash
   # MongoDB usually runs as a service after installation
   # Or start manually:
   "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath="C:\data\db"
   ```

3. **Verify MongoDB is running**
   ```bash
   # Connect using mongosh
   mongosh

   # You should see the MongoDB shell prompt
   # Type 'exit' to quit
   ```

4. **Use the default connection string**
   ```
   mongodb://localhost:27017
   ```

---

## Setup & Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd AnCapTruyenLamVideo
```

### Step 2: Backend Setup

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate a Python virtual environment**

   **macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

5. **Edit the `.env` file**

   Open `.env` in your editor and configure `MONGODB_URI`:

   **For MongoDB Atlas:**
   ```env
   MONGODB_URI=mongodb+srv://yourusername:yourpassword@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=ancaptruyenlamvideo_db
   ```

   **For Local MongoDB:**
   ```env
   MONGODB_URI=mongodb://localhost:27017
   DATABASE_NAME=ancaptruyenlamvideo_db
   ```

6. **Start the FastAPI server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. **Verify the backend is running**
   - Open your browser to [http://localhost:8000/docs](http://localhost:8000/docs)
   - You should see the "AnCapTruyenLamVideo API" Swagger documentation
   - Check the terminal for MongoDB connection status

### Step 3: Frontend Setup

1. **Open a new terminal and navigate to the frontend directory**
   ```bash
   cd frontend
   ```

2. **Install npm dependencies**
   ```bash
   npm install
   ```

3. **Start the Angular development server**
   ```bash
   npm start
   ```

4. **Access the application**
   - Open your browser to [http://localhost:4200](http://localhost:4200)
   - You should see the AnCapTruyenLamVideo application

---

## Running the Full Application

### Quick Start Order

1. **Ensure MongoDB is accessible**
   - **Atlas:** Your cluster should be running (check Atlas dashboard)
   - **Local:** Start `mongod` if not running as a service

2. **Start the Backend** (Terminal 1)
   ```bash
   cd backend
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   uvicorn app.main:app --reload --port 8000
   ```

3. **Start the Frontend** (Terminal 2)
   ```bash
   cd frontend
   npm start
   ```

4. **Open the application**
   - Frontend: [http://localhost:4200](http://localhost:4200)
   - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories` | List all stories |
| GET | `/api/stories/{id}` | Get a single story |
| POST | `/api/stories` | Create a new story |
| PUT | `/api/stories/{id}` | Update an existing story |
| DELETE | `/api/stories/{id}` | Delete a story |
| GET | `/health` | Health check endpoint |

---

## Available Scripts

### Frontend (in `frontend/` directory)

| Command | Description |
|---------|-------------|
| `npm start` | Start development server on port 4200 |
| `npm run build` | Build for production |
| `npm test` | Run unit tests |
| `npm run watch` | Build and watch for changes |

### Backend (in `backend/` directory)

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start dev server with auto-reload |
| `uvicorn app.main:app` | Start production server |
| `pip install -r requirements.txt` | Install dependencies |

---

## Switching Between Atlas and Local MongoDB

To switch between MongoDB Atlas and local MongoDB:

1. **Open `backend/.env`**

2. **Update the `MONGODB_URI` value:**

   **For Atlas:**
   ```env
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

   **For Local:**
   ```env
   MONGODB_URI=mongodb://localhost:27017
   ```

3. **Restart the backend server**
   ```bash
   # Stop the server (Ctrl+C)
   # Start again
   uvicorn app.main:app --reload --port 8000
   ```

The application will automatically detect the connection type and log it on startup.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Database name | `ancaptruyenlamvideo_db` |
| `BACKEND_PORT` | Server port | `8000` |
| `BACKEND_HOST` | Server host | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:4200` |
| `ENVIRONMENT` | Environment mode | `development` |

---

## Troubleshooting

### MongoDB Atlas Issues

#### Connection Timeout
- **Cause:** IP address not whitelisted
- **Solution:** Go to Atlas → Network Access → Add your IP or allow `0.0.0.0/0`

#### Authentication Failed
- **Cause:** Incorrect username or password
- **Solution:**
  - Verify credentials in Database Access
  - URL-encode special characters in password (e.g., `@` → `%40`)
  - Create a new user if needed

#### DNS Resolution Error
- **Cause:** Missing `dnspython` package
- **Solution:** `pip install dnspython`

### Local MongoDB Issues

#### Connection Refused
- **Cause:** MongoDB service not running
- **Solution:**
  ```bash
  # macOS
  brew services start mongodb-community

  # Linux
  sudo systemctl start mongod

  # Windows - check Services app
  ```

#### Cannot Connect to localhost:27017
- **Cause:** MongoDB bound to different address
- **Solution:** Check MongoDB config or try `127.0.0.1` instead of `localhost`

### General Issues

#### Port Already in Use
- **Backend (8000):** Change port in `.env` or use `--port 8001`
- **Frontend (4200):** Use `ng serve --port 4201`

#### CORS Errors
- Verify `CORS_ORIGINS` in `.env` includes your frontend URL
- Check that both frontend and backend are running

#### API Requests Failing
- Verify backend is running on port 8000
- Check `proxy.conf.json` configuration
- Look at browser console and backend logs for errors

---

## Development Notes

### Frontend Development
- The proxy configuration (`proxy.conf.json`) forwards `/api` requests to the backend
- PrimeNG components are configured with the Lara Light Blue theme
- Environment files are in `src/environments/`

### Backend Development
- FastAPI auto-reloads on file changes with `--reload` flag
- MongoDB connection is async using Motor driver
- Pydantic handles request/response validation

---

## License

This project is for educational and development purposes.

---

## Support

If you encounter any issues, please check the Troubleshooting section above or review the logs for detailed error messages.
