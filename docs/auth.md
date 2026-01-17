# Authentication & Security

This document outlines how CodenCollab secures user data and prevents unauthorized access. We rely on **Supabase** for identity management and standard **JWT (JSON Web Token)** verification for access control.

## The Authentication Flow

We treat the Frontend and Backend as two separate entities that do not trust each other. The **JWT** is the only proof of identity accepted by the backend.

### 1. Client-Side Login (Frontend)
* The user logs in via the React frontend using the Supabase Client SDK.
* Supabase returns a session object containing an `access_token` (JWT) and a `refresh_token`.
* This token is stored securely in the browser (handled automatically by the Supabase client).

### 2. Protecting API Routes (REST)
When a user attempts to run code or fetch sensitive data, the frontend attaches the token to the HTTP Headers:

```http
POST /rooms/123/run HTTP/1.1
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>

```

* **Backend Check:** The FastAPI backend extracts this token and verifies its signature against our **Supabase JWT Secret**.
* **Expiration:** If the token is expired, the request is immediately rejected with a `401 Unauthorized` error.

### 3. Protecting the WebSocket (Real-Time)

Securing WebSockets is trickier because they are persistent connections.

* **Handshake:** During the initial Socket.IO handshake, the client should pass the token in the `auth` object.
* **Connection Guard:** The backend validates this token *before* allowing the socket to connect. If the token is invalid, the socket is disconnected immediately, preventing the user from receiving any real-time updates.

---

## Server-Side Access Control

Authentication identifies *who* the user is. Authorization determines *what* they can do.

### Room-Level Security

Just because a user is logged in doesn't mean they can enter any room.

* **Join Event:** When a socket emits `join { room_id }`, the backend checks if that room is public or private. If private, it verifies if the user's ID is on the allowlist for that room.

### Execution Security

Running code is the most dangerous action in the app.

* **Validation:** The `/run` endpoint is strictly protected. We verify the JWT on every single execution request.
* **Sanitization:** Input is stripped of obvious malicious shell characters before being sent to the sandbox.
* **Isolation:** Execution happens in **Piston**, a completely separate environment. Even if a user bypasses backend checks, they are trapped in a Docker container with no network access to our database.

---

## Security Best Practices

### 1. Secret Management

* **Service Role Keys:** We strictly keep the `SUPABASE_SERVICE_ROLE_KEY` on the backend. This key has admin rights and is **never** exposed to the frontend/browser.
* **Environment Variables:** All secrets are loaded via `.env` files and are never committed to Git.

### 2. Network Security

* **HTTPS/WSS:** In production, all traffic (REST and WebSockets) must be encrypted via TLS.
* **CORS (Cross-Origin Resource Sharing):** We explicitly whitelist only our frontend domain (e.g., `https://codencollab-app.vercel.app`) to prevent malicious websites from triggering actions on behalf of a user.

### 3. Token Lifecycle

* Supabase tokens are short-lived (usually 1 hour).
* The frontend handles token refreshing automatically. If a session expires during a coding session, the client will silently refresh the token and reconnect the socket seamlessly.
