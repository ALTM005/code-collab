import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { supabase } from "../supabaseClient";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function Home() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [session, setSession] = useState<any>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) =>
      setSession(s)
    );
    return () => sub.subscription.unsubscribe();
  }, []); // TAKE NOTES

  const signUp = async () => {
    try {
      setStatus("Signing in....");

      const { error } = await supabase.auth.signUp({ email, password });
      if (error) {
        setStatus(`Sign in error ${error.message}`);
      } else {
        setStatus("Sign in done");
      }
    } catch (err) {
      setStatus("Unexpected Error");
    }
  };

  const signIn = async () => {
    try {
      setStatus("Signing in....");

      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) {
        setStatus(`Sign in error ${error.message}`);
      } else {
        setStatus("Sign in done");
      }
    } catch (err) {
      setStatus("Unexpected Error");
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setStatus("Sign Out done");
  };

  const authHeader = async () => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      throw new Error("Not authenticated");
    }
    return { Authorization: `Bearer ${token}` };
  };

  const handleCreateRoom = async () => {
    try {
      const headers = await authHeader();
      supabase.auth.getSession().then(({ data }) => {
        console.log(data.session?.access_token);
      });
      const res = await fetch(`${API}/rooms`, { method: "POST", headers });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      navigate(`/room/${data.room_id}`);
    } catch (err) {
      alert("Failed to create room");
      console.error(err);
    }
  };

  const onJoin = async () => {
    try {
      const feedback = prompt("Enter room id: ");
      if (!feedback) {
        return;
      }
      const headers = await authHeader();
      const res = await fetch(`${API}/rooms/${feedback}/join`, {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      navigate(`/room/${feedback}`);
    } catch (err) {
      alert("Failed to join room");
      console.error(err);
    }
  };

  return (
    <div>
      <h1>Real time collab and code</h1>
      {!session ? (
        <>
          <input
            value={email}
            name="email"
            onChange={(event) => setEmail(event.target.value.trim())}
            placeholder="Email"
          />
          <input
            value={password}
            name="password"
            onChange={(event) => setPassword(event.target.value.trim())}
            placeholder="Password"
          />
          <button onClick={signUp}>Sign Up</button>
          <button onClick={signIn}>Sign In</button>
          <p>{status}</p>
        </>
      ) : (
        <>
          <span>Signed in as {session.user.email}</span>
          <button onClick={signOut}>Sign Out</button>
          <button onClick={handleCreateRoom}>Create Room</button>
          <button onClick={onJoin}>Join Room</button>
          <p>{status}</p>
        </>
      )}
    </div>
  );
}
