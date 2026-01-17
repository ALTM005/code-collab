# Real-Time Synchronization Strategy

This document explains the practical implementation details of CodenCollab's synchronization engine. It covers how we keep clients in sync, handle network "chattiness," and prevent infinite update loops.

## Core Architecture: Room Scoping
We utilize **Socket.IO Rooms** to isolate collaboration sessions.
- **Strict Isolation:** All events (`code-update`, `cursor`, `execution-result`) are emitted to a specific `room_id`.
- **Privacy:** This ensures that actions in "Room A" are never broadcast to "Room B," maintaining data privacy and reducing unnecessary server load.

## The "Echo" Problem (Feedback Loops)
The hardest part of real-time syncing is preventing an infinite loop where:
1. User A types a character.
2. Server sends it to User B.
3. User B's editor applies the change programmatically.
4. User B's editor detects a "change" and sends it *back* to User A.
5. Repeat forever until the browser crashes.

### Our Solution: The `isApplyingRemoteChange` Flag
We use a React `useRef` boolean to distinguish between *human* edits and *socket* edits.

1. **Incoming Event:** When a `code-update` event arrives, we set `isApplyingRemoteChange.current = true`.
2. **Apply Edit:** We apply the delta to the Monaco Model.
3. **Reset:** Immediately after application, we set the flag back to `false`.
4. **Event Listener:** Our local `onDidChangeModelContent` listener checks this flag first. If it is `true`, it knows the change came from the server, so it **ignores it** and does not emit a socket event.

## Cursor Optimization (Debouncing)
Cursor movements are extremely high-frequency events. Sending a packet for every pixel a mouse moves would flood the network and degrade performance.

### Strategy
- **Debouncing:** We implement a **100ms throttle** on the client side.
- **Logic:** If a user moves their cursor, we wait 100ms. If they move again within that window, we reset the timer. We only emit the final position once the user stops moving or the interval passes.
- **Result:** This reduces network traffic by approximately 90% while still looking "live" to other users.

## Handling Decorations (Visuals)
To render remote cursors, we do not insert text into the document. Instead, we use Monaco's **Decorations API**.

- **Implementation:** We maintain a `decorationsCollectionRef`.
- **Update Cycle:** When a `cursor` event arrives, we calculate the new positions and overwrite the collection using `set()`.
- **Memory Management:** Monaco handles the cleanup of old decorations automatically when we overwrite them, preventing memory leaks in long sessions.

## Conflict Resolution & Limitations
Currently, CodenCollab uses a **Server-Relay** (Last Write Wins) approach.
- **Pros:** Extremely low latency and simple codebase. Perfect for pair programming (2-3 people).
- **Cons:** Not mathematically conflict-free. If two users type on the exact same line at the exact same millisecond, consistency is not guaranteed.

### Future Migration Path
If the project scales to support large classrooms or offline-first editing, we plan to migrate the state management to a **CRDT** (Conflict-free Replicated Data Type) library like **Yjs**. This would allow for decentralized, mathematical conflict resolution at the cost of higher complexity.