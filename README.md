# Multisession notebook

## Systemy Rozproszone

This project realizes a functionality of a multisession (multi threaded) collaborative notebook, with authentication. It supports multisession updates, delegated to adequate workers by a `Kafka` message broker.

## Authors

- Łukasz Florek
- Konrad Czerniej
- Jakub Janik

---

## 🚀 Quick Start (Docker Compose)

### Requirements

- Docker & Docker Compose
- Port 8000, 8501, 8888, 9092, 5432 available

### 1. Generate Environment Variables

Open a terminal in the repository root and run:

```bash
python3 ./backend/app/init_env.py
```

This creates `backend/app/.env` from `backend/app/.env.example`.

### 2. Run Docker Engine

Start Docker Desktop or Docker daemon.

### 3. Start All Services

In the root folder, run:

```bash
docker compose up --build
```

This starts:

- ✅ PostgreSQL (Database)
- ✅ Zookeeper + Kafka (Message Broker)
- ✅ Backend API (FastAPI)
- ✅ Worker (Kafka Consumer)
- ✅ Frontend (Streamlit)
- ✅ Adminer (Database UI)

### 4. Wait for Initialization (~30-60 seconds)

On the first start the backend creates the database schema automatically and the worker starts consuming Kafka messages. Look for logs like:

```
[WORKER] Consumer is listening for tasks...
WARNING streamlit.server.server: No users have logged-in yet...
```

### 5. Access the Applications

| Service         | URL                        | Purpose               |
| --------------- | -------------------------- | --------------------- |
| **Frontend**    | http://localhost:8501      | Web UI (Streamlit)    |
| **Backend API** | http://localhost:8000      | REST API              |
| **API Docs**    | http://localhost:8000/docs | Swagger Documentation |
| **Database UI** | http://localhost:8888      | Adminer (DB Admin)    |

---

## 🎯 Using the Application

### 1. Register / Login

- Open http://localhost:8501
- Click "Rejestracja" (Register) in sidebar
- Enter name, email, password
- Login with your credentials

### 2. Create Notebook

- Click "➕ Nowy notatnik" (New Notebook)
- Enter title
- Notebook appears in history

### 3. Edit Notebook

- Select notebook from "Historia" (History)
- Click "✏️ Otwórz" (Open)
- Edit content
- Click "🚀 Wyślij przez Kafkę" (Send via Kafka)
- Wait ~1 second for processing
- Click "🔄 Odśwież teraz" (Refresh) to see changes

### 4. Auto-Refresh

- Check "🔄 Auto-odświeżanie" (Auto-refresh)
- Changes update automatically every 5 seconds

---

## 💾 Data Storage

The application stores data in two places:

- `backend/data/notebook_<uuid>/` — notebook state persisted by the backend/worker
- `frontend/history_<email>.json` — per-user notebook history used by the Streamlit UI

Inside each notebook directory you will typically see:

- `cache.json` — latest notebook metadata and change cache
- `content.json` or `content.txt` — notebook content representation

Example backend notebook layout:

```text
backend/data/notebook_2322a4da-7550-4de5-8945-5e9b9341def6/
├── cache.json
└── content.json
```

Example frontend history file:

```json
{
  "affb363b-b7c1-4af0-9915-515856cba892": "notatnik1"
}
```

## 💻 Local Development (Without Docker)

### Install Dependencies

Frontend:

```bash
cd frontend
pip install -r requirements.txt
```

Backend:

```bash
cd backend
pip install -r requirements.txt
```

### Run Frontend Locally

If backend is running in Docker:

```bash
cd frontend
export BACKEND_URL=http://localhost:8000
streamlit run main.py
```

Frontend opens at http://localhost:8501

---

## 🔧 Configuration

### Environment Variables

**Backend** (`backend/app/.env`):

```env
ACCESS_SECRET=your_secret_key
REFRESH_SECRET=your_refresh_secret
ALGORITHM=HS256
```

**Frontend** (`docker-compose.yaml`):

```yaml
environment:
  - BACKEND_URL=http://api:8000 # In Docker
```

For local development, set `BACKEND_URL=http://localhost:8000` in your shell before running Streamlit.

---

## 🏗️ System Architecture

```
┌──────────────┐
│   Frontend   │ (Streamlit - port 8501)
│  (User Web)  │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│   FastAPI Backend    │ (port 8000)
│   - Authentication   │
│   - Notebooks API    │
└────────┬─────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│Database│ │  Kafka   │ (port 9092)
│ (PG)   │ │ (Broker) │
└────────┘ └────┬─────┘
                │
                ▼
           ┌─────────────────┐
           │  Worker/Actor   │
           │  (Consumer)     │
           │  - Processes    │
           │  - File I/O     │
           └─────────────────┘
```

### Data Flow

**Writing a Notebook:**

```
Frontend (PUT)
    ↓
API (creates message)
    ↓
Kafka (topic: "notebook_updates")
    ↓
Worker (processes message)
    ↓
File Storage (writes to disk)
    ↓
Frontend GET /poll (reads & displays)
```

### JSON Response Format

All API responses wrapped in:

```json
{
  "message": "Operation description",
  "data": {
    "id": "uuid",
    "title": "Notebook Title",
    "content": "Notebook content",
    "admin_id": 1,
    "collaborators": []
  }
}
```

---

## 🐛 Debugging & Troubleshooting

### View Logs

All containers:

```bash
docker compose logs -f
```

Specific service:

```bash
docker compose logs -f frontend
docker compose logs -f api
docker compose logs -f worker
```

### Frontend Debug Panel

In the editor, open the "🔧 DEBUG - Stan notatnika" expander to see:

- Notebook ID
- Content type
- Text length
- First 100 characters

### Check Database

Open http://localhost:8888 (Adminer UI)

- User: `user`
- Password: `password`
- Database: `notebook_db`

### Check Kafka Messages

```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic notebook_updates \
  --from-beginning
```

### Common Issues

**Issue: Can't login**

- Check if backend is running: `curl http://localhost:8000/docs`
- View logs: `docker compose logs api`
- Restart: `docker compose restart`

**Issue: Notebook content is empty**

- Check worker: `docker compose logs worker`
- Click "🔄 Odśwież teraz" (Refresh Now)
- Wait 2-3 seconds after sending

**Issue: Error 403 - Permission Denied**

- Login as notebook owner (creator)
- Check database admin_id matches your user ID

**Issue: Kafka not starting**

```bash
docker compose down
docker compose up --build -d
# Wait 30 seconds
docker compose logs kafka
```

---

## 🧹 Cleanup

### Stop All Containers

```bash
docker compose down
```

### Full Reset (Delete All Data)

```bash
docker compose down -v
```

---

## 📦 Project Structure

```
multisession-notebook/
├── docker-compose.yaml       ← Service orchestration
├── README.md                 ← This file
│
├── frontend/
│   ├── Dockerfile            ← Frontend container
│   ├── main.py               ← Streamlit app
│   ├── requirements.txt      ← Python dependencies
│   └── history_*.json        ← User notebook history
│
├── backend/
│   ├── Dockerfile            ← Backend container
│   ├── requirements.txt      ← Python dependencies
│   ├── app/
│   │   ├── main.py           ← FastAPI entry point
│   │   ├── init_env.py       ← Creates backend/app/.env from the example file
│   │   ├── .env.example      ← Local environment template
│   │   ├── features/         ← Auth, notebook, and user features
│   │   ├── workers/          ← Kafka consumer/session manager
│   │   └── core/             ← Database, Kafka, and lifespan setup
│   └── data/
│       └── notebook_{id}/    ← Notebook storage
│           ├── content.json  ← Event chain / notebook content data
│           └── cache.json    ← Cache
│
└── postgres_data/            ← Database volume
```

---

## 🎓 Technology Stack

- **Frontend:** Streamlit (Python)
- **Backend:** FastAPI (Python/asyncio)
- **Database:** PostgreSQL
- **Message Broker:** Apache Kafka
- **Authentication:** JWT tokens
- **Containerization:** Docker & Docker Compose

---

## 📄 License

This is an educational project for the "Distributed Systems" course.

---

**Last Updated:** 2026-06-08
