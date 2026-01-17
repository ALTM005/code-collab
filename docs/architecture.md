# System Architecture

This document breaks down how CodenCollab works under the hood. It explains our data flow, the "Hybrid" execution model we implemented, and the specific trade-offs we made for low-latency performance.

## High-Level Overview

CodenCollab operates on a **Pub/Sub (Publish/Subscribe)** model.
- **Publishers:** Clients (browsers) emit events like keystrokes or cursor movements.
- **Subscriber/Broadcaster:** The FastAPI backend receives these events and immediately broadcasts them to other users in the same "Room."

We decoupled the code execution (Piston) from the WebSocket layer to ensure that running heavy computations doesn't block the real-time sync for other users.

```ascii
+----------------------+           +-------------------------+
|   Browser Client     |           |      Vercel (CDN)       |
| (React + Monaco UI)  |<--------->|    (Static Assets)      |
+----------------------+           +-------------------------+
      |      ^
      |      |  1. WebSocket (Sync & Cursors)
      |      |  2. HTTP POST (Trigger Run)
      v      v
+----------------------+           +-------------------------+
|   FastAPI Backend    |<--------->|        Supabase         |
|      (Railway)       |   Auth    |    (JWT Validation)     |
+----------------------+           +-------------------------+
           |
           | HTTP (Sandbox Request)
           v
+----------------------+
|      Piston API      |
| (Isolated Execution) |
+----------------------+

```

---

## The "Hybrid" Execution Flow

One unique design choice in this project is how we handle "Run Code." We don't do it purely over WebSockets. We use a **Hybrid REST + Socket** approach to handle authentication securely and broadcast results efficiently.

### Step 1: The Trigger (REST)

When a user clicks "Run Code," the frontend sends a secure `POST` request to `${API}/rooms/{id}/run`.

* **Why REST?** It allows us to easily attach the Supabase Auth Header (`Authorization: Bearer <token>`) to the request. This makes validating permissions on the backend strictly standard and secure.

### Step 2: The Execution (Background)

The backend validates the token. If valid, it forwards the code to the **Piston API** (our sandboxed execution engine). This happens asynchronously so the server remains responsive.

### Step 3: The Result (WebSocket)

Once Piston returns the output (`stdout`), the backend does **not** send it back via the HTTP response. Instead, it emits a `execution-result` event via **Socket.IO** to the entire room.

* **Why?** If User A clicks "Run", User B should also see the output immediately. This ensures the interview context is shared perfectly.

---

## Real-Time Synchronization Strategy

### Code Sync

We use a **Server-Relay** pattern.

1. **Event:** `code_change`
2. **Payload:** The specific delta (change) + full code state.
3. **Action:** The server relays this delta to everyone else in the room.
4. **Client:** The Monaco Editor applies the delta using `model.applyEdits()`, preventing the cursor from jumping to the start of the file.

### Cursor Tracking

To prevent flooding the network, cursor movements are **debounced** (100ms throttle).

1. **Event:** `cursor`
2. **Payload:** `{ userId, lineNumber, column }`
3. **Visualization:** The frontend renders a custom "Remote Cursor Widget" (CSS-based) at those coordinates using Monaco's Decoration API.

---

## Security & Isolation

### 1. Code Sandbox (Piston)

We never run user code directly on our FastAPI server. User code is malicious by default. We send it to Piston, which runs it in isolated Docker containers (chrooted environments) with no network access.

### 2. Row Level Security (RLS) & JWTs

* **Frontend:** Supabase handles the login and issues a JWT.
* **Backend:** Every sensitive request (like running code) requires this JWT. The backend decodes and validates the token signature against Supabase's secret before processing.

---

## Design Trade-offs

* **Latency vs. Consistency:** We prioritized **low latency**. We use a "Last Write Wins" approach. It is blazing fast for small teams (2-3 people). However, if two users type on the exact same line at the exact same millisecond, you might see a "jitter" or conflict. Ideally, a future version would implement **CRDTs (Yjs)** for mathematical consistency.
* **Ephemeral State:** Currently, code exists only in the active server memory. If the server restarts, the room resets. A future improvement is to add a background task that saves the code to Supabase every 30 seconds (Auto-Save).

