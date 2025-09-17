import { useParams } from "react-router-dom";
import Editor, { type OnMount} from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client"; //install socket
import { supabase } from "../supabaseClient";
import { Box } from "@chakra-ui/react";
import LanguageSelector from "./components/LanguageSelector";


const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const CURSOR_COLORS = ["#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1"];
const getColorForId = (id : string) =>{
  let tot = 0;
  for (let i = 0; i < id.length; i++){
    tot += id.charCodeAt(i); 
  }
  return CURSOR_COLORS[tot % CURSOR_COLORS.length];
}


export default function Room() {

  const {id: room_id} = useParams();
  const socketRef = useRef<Socket | null>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof monaco | null>(null);
  const [remoteCursors, setRemoteCursors] = useState<Record<string, any>>({});
  const currentUserIdRef = useRef<string | null>(null);
  const decorationsCollectionRef = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);
  const isApplyingRemoteChange = useRef(false);
  const cursorUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  useEffect(()=>{
    supabase.auth.getUser().then(({data})=>{
      if (data.user){
        currentUserIdRef.current = data.user.id;
      }
    });
  }, []);

  useEffect(()=>{
    const s = io(API,{
      path:"/socket.io",
      transports: ["websocket"]
    });
    socketRef.current = s;

    s.on("connect", ()=>{
      console.log("Socket connected:", s.id) //remove before hosting, check s.id and sid
      s.emit("join",{room_id})
    });

    s.on("initial-code", (data)=>{
      isApplyingRemoteChange.current = true;
      editorRef.current?.setValue(data.code || "");
      isApplyingRemoteChange.current = false;
    });

    s.on("code-update", (data : {changes : monaco.editor.IModelContentChange[]})=>{
      const model = editorRef.current?.getModel();
      if (!model || !data.changes)
      {
        return;
      }
      isApplyingRemoteChange.current = true;
      model.applyEdits(data.changes.map(c => ({
        ...c,
        range: new monaco.Range(c.range.startLineNumber,c.range.startColumn,c.range.endLineNumber,c.range.endColumn)
      })));
      isApplyingRemoteChange.current = false;
    });

    s.on("cursor", (data : {userId: string; sid: string; lineNumber: number; column: number})=>{
      console.log("Cursor event received", data); //remove before hosting
      if (data.userId !== currentUserIdRef.current && monacoRef.current){
        setRemoteCursors((prev)=>({
          ...prev,
          [data.sid]: {
            position: new monacoRef.current!.Position(data.lineNumber, data.column),
            color: getColorForId(data.userId)
          },

        }));
      }

    });

    s.on("user-disconnected", (data: { sid: string }) => {
      setRemoteCursors((prev) => {
        const newCursors = { ...prev };
        delete newCursors[data.sid];
        return newCursors;
      });
    }); //removes cursors

    return () => { 
      s.off("connect");
      s.off("initial-code");
      s.off("code-update");
      s.off("cursor");
      s.off("user-disconnected");
      s.disconnect();
      if (cursorUpdateTimeoutRef.current){
        clearTimeout(cursorUpdateTimeoutRef.current);
      }
    };
  },[room_id]);

  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;
    
    console.log("[Step 4] Rendering remote cursors...", remoteCursors);

    if (!decorationsCollectionRef.current) {
      decorationsCollectionRef.current =
        editorRef.current.createDecorationsCollection();
    }
    const decorations = Object.entries(remoteCursors).map(([sid, cursor]) => ({
      range: new monaco.Range(
        cursor.position.lineNumber,
        cursor.position.column,
        cursor.position.lineNumber,
        cursor.position.column
      ),
      options: {
        after: { content: "" },
        afterContentClassName: `remote-cursor-widget remote-cursor-widget-${sid}`,
        stickiness:
          monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
      },
    }));
    decorationsCollectionRef.current.set(decorations);
  }, [remoteCursors]);

  const OnMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    editor.focus();
    monacoRef.current = monaco;


    editor.onDidChangeCursorPosition((event) => {
      //skip the remote change using isApplyingRemoteChange.current
      if(isApplyingRemoteChange.current){
        return;
      }

      if(currentUserIdRef.current && socketRef.current?.connected){
        //clear timeout
        if (cursorUpdateTimeoutRef.current) {
          clearTimeout(cursorUpdateTimeoutRef.current);
        }
      
      //set new timeout
      cursorUpdateTimeoutRef.current = setTimeout(()=>{
        console.log("Emiting cursor position");
        socketRef.current?.emit("cursor", {
          userId: currentUserIdRef.current,
          sid: socketRef.current.id,
          lineNumber: event.position.lineNumber,
          column: event.position.column
        }); 
      }, 100)//100ms break
    }  
    });

    editor.onDidChangeModelContent((event)=>{
      if (isApplyingRemoteChange.current){
        return;
      }
      socketRef.current?.emit("code_change", {
        changes: event.changes,
        code: editor.getValue()
      });
    });
  };


  return (
    <Box minH="100vh" bg="#0fa19" color="gray.500" px={6} py={8}>
        <h2>Room: {room_id}</h2>
        <Box>
          <LanguageSelector/>
            <Editor
            height="75vh"
            theme="vs-dark"
            defaultLanguage="javascript"
            defaultValue={"// Welcome! Start coding..."}
            onMount={OnMount}
            options={{ fontSize: 14, minimap: { enabled: false } }}
            />
      </Box>

      {/* remote cursor styles */}
      <style>{`
      .remote-cursor-widget {
        position: absolute;
        width: 2px;
        height: 1.2em;
        margin-left: -1px;
        pointer-events: none;
      }
      ${Object.entries(remoteCursors)
        .map(
          ([sid, cursor]) =>
            `.remote-cursor-widget-${sid} { background-color: ${cursor.color}; }`
        )
        .join("\n")}
    `}</style>
    </Box>

  );
}
