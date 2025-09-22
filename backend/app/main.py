from fastapi import FastAPI, Depends, Header, HTTPException
import os, httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from time import time 
import socketio
from starlette.applications import Starlette
import asyncio

async def save_code_db (room_id: str, code:str):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                url = f'{SUPABASE_URL}/rest/v1/rooms?id=eq.{room_id}',
                headers={
                    "apikey": SUPABASE_SERVICE_ROLE,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={"code": code}
            )
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"Error saving code for room {room_id}, error: {e}")


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173"],  # Empty list allows all for WebSocket
    allow_upgrades=True,
)

sio_app = socketio.ASGIApp(sio)


@sio.event
async def connect(sid, environ):
    print("Socket Connected", sid)

@sio.event
async def disconnect(sid):
    print("Socket Disconnected",sid)
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    if room_id:
        await sio.emit("user-disconnected", {"sid": sid}, room=room_id, skip_sid=sid)

@sio.event
async def join(sid, data):
    room_id = data["room_id"]
    await sio.save_session(sid, {"room_id":room_id})
    await sio.enter_room(sid, room_id)
    #Log user in shell
    print(f"Socket {sid} joined room {room_id}")

    current_code = None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
            url = f'{SUPABASE_URL}/rest/v1/rooms?id=eq.{room_id}&select=code',
            headers={
                "apikey": SUPABASE_SERVICE_ROLE,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
                "Content-Type": "application/json",
            }
        )
        r.raise_for_status()
        if r.json() and r.json()[0].get("code") is not None:
            current_code = r.json()[0]["code"]
    except httpx.HTTPStatusError as e:
        print(f"Error fetching code for room {room_id}, error: {e}")

    if current_code is not None:
        await sio.emit("initial-code", {"code": current_code}, to=sid)


@sio.event
async def cursor(sid, data):
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    if room_id:
        await sio.emit("cursor", data, room=room_id, skip_sid=sid)

@sio.event
async def code_change(sid, data):
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    changes = data.get("changes")
    full_code = data.get("code")
    if room_id:
        if changes:
            await sio.emit("code-update", {"changes": changes}, room=room_id, skip_sid=sid)
            
        if full_code is not None:
            asyncio.create_task(save_code_db(room_id=room_id, code=full_code))
            

        


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN,"http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE", "SUPABASE_JWT_SECRET"):
    if not os.getenv(k):
        raise RuntimeError(f"Missing {k}. Check backend/.env")

'''def get_user_id(authorization: str | None = Header(default = None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
    token = authorization.replace("Bearer", "", 1).strip()
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid Token")
        return sub
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid Token")'''

#Temporary Code due to bug

def get_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    try:
        unverified = jwt.get_unverified_claims(token)
        print("UNVERIFIED:", {
            "sub": unverified.get("sub"),
            "iss": unverified.get("iss"),
            "aud": unverified.get("aud"),
            "exp_in": (unverified.get("exp") or 0) - int(time()),
        })
    except Exception as e:
        print("Unable to read unverified claims:", e)

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}, 
        )
        expected_iss = f"{SUPABASE_URL}/auth/v1"
        iss = payload.get("iss")
        if iss != expected_iss:
            print(f"Issuer Mismatch: got {iss}, expected {expected_iss}") 

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token (no sub)")
        return sub
    except JWTError as e:
        print("JWT decode error:", repr(e))
        raise HTTPException(status_code=401, detail="Invalid token")




@app.get("/health")
def health():
    return {"status":"running"}

@app.post("/rooms")
async def create_room(user_id : str = Depends(get_user_id)):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url=f'{SUPABASE_URL}/rest/v1/rooms',
            headers={
                "apikey": SUPABASE_SERVICE_ROLE,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
                "Content-Type": "application/json",
                "Prefer":"return=representation"
            },
            json={
                "title":None,
                "creator":user_id
            }
        )
        r.raise_for_status()
        room = r.json()[0]
        return {"room_id":room["id"]}

@app.post("/rooms/{room_id}/join")
async def join_room(room_id: str, user_id : str = Depends(get_user_id)):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url=f'{SUPABASE_URL}/rest/v1/sessions',
            headers={
                "apikey": SUPABASE_SERVICE_ROLE,
                "Authorization" : f"Bearer {SUPABASE_SERVICE_ROLE}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            },
            json={
                "room_id":room_id,
                "user_id":user_id
            }
        )
        # ignore conflict to allow mergiing same user r.raise_for_status()
        return {"joined": True}


fast_api = app
asgi = Starlette()
asgi.mount("/socket.io", sio_app)
asgi.mount("/", fast_api)