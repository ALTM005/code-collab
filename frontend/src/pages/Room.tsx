import { useParams } from "react-router-dom";
import { Editor } from "@monaco-editor/react";
import { useState } from "react";


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