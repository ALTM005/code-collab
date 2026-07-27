from fastapi import FastAPI, Depends, Header, HTTPException
import os, httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from time import time 
import socketio
from socketio.exceptions import ConnectionRefusedError
from starlette.applications import Starlette
import asyncio
from pydantic import BaseModel

class RunRequest(BaseModel):
    language:str

LANGUAGE_VERSIONS = {
  "javascript": "18.15.0",
  "typescript": "5.0.3",
  "python": "3.10.0",
  "java": "15.0.2",
  "csharp": "6.12.0",
  "php": "8.2.3",
}

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
PISTON_API = os.getenv("PISTON_API")

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173"],  # Empty list allows all for WebSocket
    allow_upgrades=True,
)

sio_app = socketio.ASGIApp(sio)


socket_expiry_tasks: dict[str, asyncio.Task] = {}

async def _expire_socket(sid, delay):
    await asyncio.sleep(delay)
    print(f"Token expired for {sid}, disconnecting")
    await sio.disconnect(sid)

@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token")
    if not token:
        raise ConnectionRefusedError("Missing token")

    try:
        payload = verify_token(token)
    except TokenError as e:
        raise ConnectionRefusedError(str(e))

    user_id = payload["sub"]
    await sio.save_session(sid, {"user_id": user_id})

    exp = payload.get("exp")
    if exp is not None:
        delay = exp - time()
        if delay <= 0:
            raise ConnectionRefusedError("Token expired")
        socket_expiry_tasks[sid] = asyncio.create_task(_expire_socket(sid, delay))

    print("Socket Connected", sid, "user", user_id)

@sio.event
async def disconnect(sid):
    print("Socket Disconnected",sid)
    task = socket_expiry_tasks.pop(sid, None)
    if task:
        task.cancel()
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    if room_id:
        await sio.emit("user-disconnected", {"sid": sid}, room=room_id, skip_sid=sid)

@sio.event
async def join(sid, data):
    room_id = data["room_id"]
    sess = await sio.get_session(sid)
    user_id = sess.get("user_id")

    # Every Supabase call below uses the service-role key, which bypasses RLS.
    # This membership check is therefore the only access control gate on room
    # content there is — there is no database-level policy backing it up.
    allowed = False
    rows = []

    if not user_id:
        print(f"Join denied for {sid}: no user_id on session")
    else:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    url=f'{SUPABASE_URL}/rest/v1/rooms?id=eq.{room_id}&select=creator,code',
                    headers={
                        "apikey": SUPABASE_SERVICE_ROLE,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
                        "Content-Type": "application/json",
                    },
                )
                r.raise_for_status()
                rows = r.json()
        except httpx.HTTPStatusError as e:
            print(f"Join denied for {sid}: error looking up room {room_id}: {e}")

        if not rows:
            print(f"Join denied for {sid}: room {room_id} does not exist")
        elif rows[0].get("creator") == user_id:
            allowed = True
        else:
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        url=f'{SUPABASE_URL}/rest/v1/sessions?room_id=eq.{room_id}&user_id=eq.{user_id}&select=user_id',
                        headers={
                            "apikey": SUPABASE_SERVICE_ROLE,
                            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
                            "Content-Type": "application/json",
                        },
                    )
                    r.raise_for_status()
                    allowed = bool(r.json())
            except httpx.HTTPStatusError as e:
                print(f"Join denied for {sid}: error checking membership for room {room_id}: {e}")

            if not allowed:
                print(f"Join denied for {sid}: user {user_id} is not a member of room {room_id}")

    if not allowed:
        await sio.emit(
            "join-error",
            {"message": "You don't have access to this room."},
            to=sid,
        )
        return

    async with sio.session(sid) as session:
        session["room_id"] = room_id
    await sio.enter_room(sid, room_id)
    #Log user in shell
    print(f"Socket {sid} joined room {room_id}")

    current_code = rows[0].get("code")
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
            
@sio.event
async def chat_message(sid, data):
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    print(f"3. Backend received chat message for room '{room_id}': {data}")

    if room_id:

        sender_name = f"User-{sid[:5]}"
        await sio.emit(
            "new-message",
            {"text": data.get("text"), "sender":sender_name},
            room=room_id
        )


@sio.event
async def language_change(sid, data):
    sess = await sio.get_session(sid)
    room_id = sess.get("room_id")
    if room_id:
        await sio.emit("language-update",
        {"language":data.get("language")},
        skip_sid=sid,
        room=room_id
        )

        


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN,"http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE", "SUPABASE_JWT_SECRET","PISTON_API"):
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

class TokenError(Exception):
    pass


def verify_token(token: str) -> dict:
    """Decode and validate a Supabase access token. Shared by the REST
    dependency (get_user_id) and the Socket.IO connect handler so there is
    exactly one definition of what makes a token valid."""
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
    except JWTError as e:
        print("JWT decode error:", repr(e))
        raise TokenError("Invalid token")

    expected_iss = f"{SUPABASE_URL}/auth/v1"
    iss = payload.get("iss")
    if iss != expected_iss:
        print(f"Issuer Mismatch: got {iss}, expected {expected_iss}")

    if not payload.get("sub"):
        raise TokenError("Invalid token (no sub)")

    return payload


def get_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    try:
        payload = verify_token(token)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return payload["sub"]




@app.get("/health")
def health():
    return {"status":"running"}

@app.post("/rooms")
async def create_room(user_id : str = Depends(get_user_id)):
    default_js = (
        "function greet(name) {\n"
        '  console.log("Hello, " + name + "!");\n'
        "}\n"
        'greet("World");\n'
    )
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
                "creator":user_id,
                "code": default_js
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

@app.post("/rooms/{room_id}/run")
async def run_code(room_id:str, request:RunRequest, user_id:str = Depends(get_user_id)):
    code_run = ""
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
        if r.json():
            code_run = r.json()[0].get("code","")
    except httpx.HTTPStatusError as e:
        await sio.emit("execution-result",{"output": f"Error fetching code: {e}"}, room=room_id)
        return {"status": "error fetching code"}
    

    try:
        selected_language = request.language
        language_ver = LANGUAGE_VERSIONS.get(selected_language,"18.15.0")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url = PISTON_API,
                json={
                    "language": selected_language,
                    "version": language_ver,
                    "files": [{"content": code_run}]
                }
            )
            result= r.json()
    except Exception as e:
        await sio.emit("execution-result", {"output": f"Error contacting Piston API: {e}"}, room=room_id)
        return {"status": "error with piston"}

    print("INCOMING RUN REQUEST BODY:", result)

    output = result.get("run", {}).get("output", "No output.")
    if result.get("run", {}).get("stderr"):
         output = result["run"]["stderr"]

    await sio.emit("execution-result", {"output": output}, room=room_id)

    return {"status": "Execution triggered"}
            


fast_api = app
asgi = Starlette()
asgi.mount("/socket.io", sio_app)
asgi.mount("/", fast_api)