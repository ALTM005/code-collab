import { useParams } from "react-router-dom";
import Editor, {OnMount} from "@monaco-editor/react";
import { useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client"; //install socket
import { supabase } from "../supabaseClient";


const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";



export default function Room() {
  const { id } = useParams();
  const [code, setCode] = useState<string>("Start coding...");
  return (
    <>
        <h2>Room: {id}</h2>
        <div style={{ height: "70vh", border: "1px solid #ddd" }}>
            <Editor
            height="100%"
            defaultLanguage="javascript"
            value={code}
            onChange={(event) => setCode(event ?? "")}
            options={{ fontSize: 14, minimap: { enabled: false } }}
            />
      </div>
    </>

  );
}