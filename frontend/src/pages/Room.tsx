import { useParams } from "react-router-dom";
import Editor, { type OnMount} from "@monaco-editor/react";
import { useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client"; //install socket
import { supabase } from "../supabaseClient";


const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";


export default function Room() {

  const {id: room_id} = useParams();
  const socketRef = useRef<Socket | null>(null);
  const editorRef = useRef<any>(null);
  const decorsRef = useRef<String[]>([]);
  //const [code, setCode] = useState<string>("Start coding...");

  useEffect(()=>{
    const s = io(API,{path:"/socket.io"});
    socketRef.current = s;

    s.on("connect", ()=>{
      s.emit("join",{room_id})
    });

    s.on("cursor", (data : any)=>{
      const editor = editorRef.current;
      if (!editor)
      {
        return;
      }
      const {lineNumber, column} = data;

      decorsRef.current = editor.deltaDecorations(
        decorsRef.current,
        [{
          range: {
            startLineNumber: lineNumber,
            startColumn: column,
            endLineNumber: lineNumber,
            endColumn: column + 1,
          },
          options: {
            className: "remote-cursor",
            stickiness: 1,
          }
        }]
      );

    });

    return () => { s.disconnect(); };

  },[room_id]);

  const OnMount : OnMount = (editor , monaco) =>{
    editorRef.current = editor;
    editor.onDidChangeCursorPosition(async (event) => {
      const {data} = await supabase.auth.getUser();
      const userId = data.user?.id;
      socketRef.current?.emit("cursor", {
        userId,
        lineNumber: event.position.lineNumber,
        column: event.position.column,
      });
      
    });

  };


  return (
    <>
        <h2>Room: {room_id}</h2>
        <div style={{ height: "70vh", border: "1px solid #ddd" }}>
            <Editor
            height="100%"
            defaultLanguage="javascript"
            value={"Start Coding!"}
            onMount={OnMount}
            options={{ fontSize: 14, minimap: { enabled: false } }}
            />
      </div>
      <style>{`.remote-cursor { border-left: 2px solid; }`}</style>
    </>

  );
}