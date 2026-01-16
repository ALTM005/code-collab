# CodeCollab
CodeCollab is a high-performance, real-time collaborative code editor engineered for technical interviews and pair programming. It combines the power of the Monaco Editor (VS Code's engine) with seamless WebSocket synchronization and secure, sandboxed code execution.

*Note: This project utilizes a specialized client-server architecture designed for low-latency updates and secure code isolation.*

<br>

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [License](#license)

<br>

## Features
- **Real-time Synchronization:** Conflict-free code editing using Socket.IO.
- **Live Cursor Tracking:** See exactly where your teammates are typing with color-coded cursors.
- **Multi-Language Execution:** Run code in 20+ languages powered by the secure Piston API.
- **Integrated Chat:** Discuss logic and share feedback instantly within the editor interface.
- **Secure Auth:** Protected routes and session management via Supabase JWTs.

<br>

## Project Structure
```bash
code-collab/
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI entry point
│   ├── .env                 # Backend secrets (Add this!)
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── pages/
│   │   │   ├── components/
│   │   │   │   ├── Chat.tsx              # Real-time chat component
│   │   │   │   ├── LanguageSelector.tsx  # Dropdown for language selection
│   │   │   │   └── OutPut.tsx            # Code execution output display
│   │   │   ├── Home.tsx     # Landing page
│   │   │   └── Room.tsx     # Main collaboration room
│   │   ├── supabaseClient.ts # Supabase configuration
│   │   ├── theme.ts          # Chakra UI theme
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── .env                 # Frontend API keys (Add this!)
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── vercel.json          # Vercel deployment config
│   └── vite.config.ts       # Vite configuration
│
└── README.md