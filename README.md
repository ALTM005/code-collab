````md
# CodeCollab

A real-time collaborative code editor for technical interviews and pair programming. CodeCollab combines the Monaco Editor (VS Code’s editor engine) with low-latency WebSocket syncing, in-room chat, and secure, sandboxed code execution.

---

## Table of Contents
- [Live Demo](#live-demo)
- [Screenshots](#screenshots)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Layout](#project-layout)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [License](#license)

---

## Live Demo

Frontend: https://codencollab-app.vercel.app

---

## Screenshots

_Add these after you capture them:_

![Editor](./assets/editor.png)
![Live Cursors](./assets/cursors.gif)
![Chat](./assets/chat.png)

---

## Features

- Real-time collaborative code editing via Socket.IO
- Live, color-coded multi-user cursor tracking
- Room-based collaboration with shareable Room IDs
- In-room chat for fast feedback and communication
- Supabase authentication (JWT sessions) with protected access
- Multi-language code execution via the Piston API (sandboxed)
- Responsive UI built for interview-style workflows

---

## Architecture Overview

CodeCollab uses a client–server architecture optimized for real-time collaboration:

- The **frontend** (React + Monaco) captures editor changes and user actions
- The **backend** (FastAPI) manages rooms, validates authentication, and coordinates real-time events
- **Socket.IO** carries low-latency events (code changes, cursors, chat, language updates)
- **Supabase** provides authentication and session tokens (JWT)
- **Piston** executes code in an isolated sandbox (code is not executed directly on your server)

Real-time events are scoped to a Room ID so updates are only broadcast to users in the same room.

---

## Project Layout

```bash
code-collab/
├── backend/                # FastAPI server + Socket.IO events + execution proxy
├── frontend/               # React/Vite client + Monaco editor + Chakra UI
└── README.md
````

---

## Tech Stack

### Frontend

* React (TypeScript)
* Vite
* Chakra UI
* Monaco Editor
* Socket.IO Client

### Backend

* Python
* FastAPI
* Socket.IO

### Services / Infrastructure

* Supabase (authentication & sessions)
* Piston API (sandboxed code execution)
* Vercel (frontend deployment)
* Railway (backend hosting)

---

## Getting Started

### Prerequisites

* Node.js 18+
* Python 3.10+
* A Supabase project (URL + anon key + JWT secret / service role key as required by your backend)

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Environment Variables

Create `.env` files in both directories.

### Frontend (`frontend/.env`)

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_URL=
```

### Backend (`backend/.env`)

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
JWT_SECRET=
PISTON_API_URL=
```

---

## Usage

1. Start the backend (`uvicorn ...`)
2. Start the frontend (`npm run dev`)
3. Open the app in your browser (Vite will show the URL in your terminal)
4. Create or join a room
5. Share the **Room ID** with a teammate to collaborate in the same session
6. Use **Run Code** to execute the current code through Piston and view the output in the UI

---

## Deployment

* Frontend deployed on **Vercel**
* Backend deployed on **Railway**
* Frontend communicates with backend via REST endpoints and Socket.IO
* The backend validates Supabase JWT sessions server-side before allowing protected actions

---

## Roadmap

* Presence indicators (active users list)
* Persistent room state and session history
* Role-based permissions (viewer/editor)
* File tree support per room
* Improved execution output formatting and error handling

---

## License

MIT License

```
```
