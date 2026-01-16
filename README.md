```markdown
# CodeCollab
![License](https://img.shields.io/badge/license-MIT-blue.svg) ![React](https://img.shields.io/badge/frontend-React-61DAFB.svg) ![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)

A high-performance, real-time collaborative code editor engineered for technical interviews and pair programming. CodeCollab combines the **Monaco Editor** (VS Code’s engine) with low-latency **WebSocket** syncing, in-room chat, and secure, sandboxed code execution.

*Note: This project utilizes a specialized client-server architecture designed for low-latency updates and secure code isolation.*

---

## Table of Contents
- [Live Demo](#live-demo)
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Deployment](#deployment)
- [Roadmap](#roadmap)

---

## Live Demo
**Frontend:** [https://codencollab-app.vercel.app](https://codencollab-app.vercel.app)

---

## Features
- **Real-time Synchronization:** Conflict-free code editing using Socket.IO.
- **Live Cursor Tracking:** See exactly where your teammates are typing with color-coded cursors.
- **Multi-Language Execution:** Run code in 20+ languages powered by the secure Piston API.
- **Integrated Chat:** Discuss logic and share feedback instantly within the editor interface.
- **Secure Auth:** Protected routes and session management via Supabase JWTs.

---

## Project Structure
```bash
code-collab/
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI entry point
│   ├── .env                 # Backend secrets
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── components/
│   │   │   │   ├── Chat.tsx              # Real-time chat component
│   │   │   │   ├── LanguageSelector.tsx  # Dropdown for language selection
│   │   │   │   └── OutPut.tsx            # Code execution output display
│   │   │   ├── Home.tsx     # Landing page
│   │   │   └── Room.tsx     # Main collaboration room
│   │   ├── supabaseClient.ts # Supabase configuration
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── .env                 # Frontend API keys
│   └── vite.config.ts       # Vite configuration
│
└── README.md

```

---

## Tech Stack

| **Layer** | **Technology** | **Purpose** |
| --- | --- | --- |
| **Frontend** | React 18 & Monaco Editor | Manages editor state, local UI (Chakra), and socket events |
| **Backend** | FastAPI & Socket.IO | Orchestrator for rooms, user auth, and proxying execution |
| **Services** | Piston API & Supabase | Sandboxed code execution environment and database/auth |
| **Hosting** | Vercel & Railway | Frontend and Backend deployment infrastructure |

---

## Installation

### Prerequisites

* Node.js 18+
* Python 3.10+
* Supabase Account (URL + Anon Key)

### 1. Clone Repository

```bash
git clone [https://github.com/your-username/code-collab.git](https://github.com/your-username/code-collab.git)
cd code-collab

```

### 2. Backend Setup

Navigate to the backend, create a virtual environment, and install dependencies.

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

### 3. Frontend Setup

Navigate to the frontend and install Node packages.

```bash
cd ../frontend
npm install

```

---

## Environment Variables

Create a `.env` file in **both** the `frontend` and `backend` directories using the templates below.

### Frontend (`frontend/.env`)

```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_BACKEND_URL=http://localhost:8000

```

### Backend (`backend/.env`)

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
JWT_SECRET=your_jwt_secret_from_supabase
PISTON_API_URL=[https://emkc.org/api/v2/piston](https://emkc.org/api/v2/piston)

```

---

## Usage

**1. Start the Backend**

```bash
# Inside /backend (ensure venv is active)
uvicorn main:app --reload

```

**2. Start the Frontend**

```bash
# Inside /frontend
npm run dev

```

**3. Collaborate**

* Open the URL provided by Vite (usually `http://localhost:5173`).
* Create a room and copy the **Room ID**.
* Share the ID with a partner to join the same session.

---

## Deployment

* **Frontend:** Deployed on Vercel. Ensure environment variables are added in the Vercel Dashboard.
* **Backend:** Deployed on Railway. Ensure the `PORT` variable is dynamically bound and the build command is set to `pip install -r requirements.txt`.

---

## Roadmap

* [ ] **Presence Indicators:** View avatars of active users in the room header.
* [ ] **Persistent State:** Save code snippets to Supabase for later retrieval.
* [ ] **Role Management:** Toggle between "Editor" and "Viewer" permissions.
* [ ] **File Explorer:** Support for multiple files within a single collaboration room.

---

## License

Distributed under the MIT License.

```

```