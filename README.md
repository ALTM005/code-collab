# CodenCollab
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Frontend](https://img.shields.io/badge/frontend-React-61DAFB.svg)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)

A high-performance, real-time collaborative code editor built for technical interviews and pair programming. CodenCollab combines the **Monaco Editor** (VS Code’s editor engine) with low-latency **WebSocket** synchronization, in-room chat, and secure, sandboxed code execution.

---

## Table of Contents
- [Live Demo](#live-demo)
- [Screenshots](#screenshots)
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [License](#license)

---

## Live Demo

**Application:** https://codencollab-app.vercel.app

---

## Screenshots

### Authentication
![Authentication](./assets/auth.gif)

### Home / Lobby
![Home](./assets/home.png)

### Collaboration Room
![Room](./assets/room.gif)

### Live Chat
![Chat](./assets/chat.gif)

### Code Execution Output
![Execution Output](./assets/output.gif)

---

## Features

- **Real-time Synchronization:** Low-latency collaborative editing using Socket.IO
- **Live Cursor Tracking:** Color-coded cursors show where teammates are typing
- **Multi-Language Execution:** Secure execution in 6 languages via the Piston API
- **Integrated Chat:** Communicate instantly within each collaboration room
- **Secure Authentication:** Protected routes and session handling with Supabase JWTs

---

## Project Structure

```bash
code-collab/
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI entry point
│   ├── .env                 # Backend environment variables
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── components/
│   │   │   │   ├── Chat.tsx              # Real-time chat component
│   │   │   │   ├── LanguageSelector.tsx  # Language selection dropdown
│   │   │   │   └── OutPut.tsx            # Code execution output display
│   │   │   ├── Home.tsx                  # Landing page
│   │   │   └── Room.tsx                  # Collaboration room
│   │   ├── supabaseClient.ts             # Supabase configuration
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── .env                 # Frontend environment variables
│   └── vite.config.ts       # Vite configuration
│
│
│
├── .env.example    # Environment variable template
│
├── LICENSE
│
├── assets/
│
└── README.md
```

---

## Tech Stack

| Layer    | Technology              | Purpose                                          |
| -------- | ----------------------- | ------------------------------------------------ |
| Frontend | React 18, Monaco Editor | Editor UI, local state, real-time events         |
| Backend  | FastAPI, Socket.IO      | Room orchestration, auth validation, event relay |
| Services | Supabase, Piston API    | Authentication, sandboxed code execution         |
| Hosting  | Vercel, Railway         | Frontend and backend deployment                  |

---

## Installation

### Prerequisites

* Node.js 18+
* Python 3.10+
* Supabase project (URL + anon key)

### 1. Clone Repository

```bash
git clone https://github.com/ALTM005/code-collab.git
cd code-collab
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Environment Variables

Create a `.env` file in **both** directories.

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY =
```

### Backend (`backend/.env`)

```env
FRONTEND_ORIGIN =http://localhost:5173
SUPABASE_URL =
SUPABASE_SERVICE_ROLE =
SUPABASE_JWT_SECRET =
PISTON_API =https://emkc.org/api/v2/piston/execute
```

---

## Usage

### 1. Start Backend

```bash
# inside /backend (ensure venv is active)
uvicorn main:app --reload
```

### 2. Start Frontend

```bash
# inside /frontend
npm run dev
```

### 3. Collaborate

* Open the URL shown by Vite (usually `http://localhost:5173`)
* Create a room and copy the **Room ID**
* Share the Room ID to collaborate in the same session

---

## Deployment

* **Frontend:** Deployed on Vercel with environment variables configured in the dashboard
* **Backend:** Deployed on Railway with build command `pip install -r requirements.txt`
* WebSocket and REST communication handled between frontend and backend
* Supabase JWTs are validated server-side for protected actions

---

## Roadmap

* Presence indicators for active users
* Persistent room state and history
* Role-based permissions (editor / viewer)
* Multi-file support per collaboration room

---

## License

MIT License
