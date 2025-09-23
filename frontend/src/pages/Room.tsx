import { useParams } from "react-router-dom";
import Editor, { type OnMount } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client"; //install socket
import { supabase } from "../supabaseClient";
import { Box, VStack } from "@chakra-ui/react";
import LanguageSelector from "./components/LanguageSelector";
import { CODE_SNIPPETS, type LANGUAGE_VERSIONS } from "../constants";
import Output from "./components/OutPut";
import Chat from "./components/Chat";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const CURSOR_COLORS = [
  "#FF5733",
  "#33FF57",
  "#3357FF",
  "#FF33A1",
  "#A133FF",
  "#33FFA1",
];
const getColorForId = (id: string) => {
  let tot = 0;
  for (let i = 0; i < id.length; i++) {
    tot += id.charCodeAt(i);
  }
  return CURSOR_COLORS[tot % CURSOR_COLORS.length];
};

export default function Room() {
  const { id: room_id } = useParams();
  //const socketRef = useRef<Socket | null>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof monaco | null>(null);
  const [remoteCursors, setRemoteCursors] = useState<Record<string, any>>({});
  const currentUserIdRef = useRef<string | null>(null);
  const decorationsCollectionRef =
    useRef<monaco.editor.IEditorDecorationsCollection | null>(null);
  const isApplyingRemoteChange = useRef(false);
  const cursorUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [language, setLanguage] = useState<Language>("javascript");
  type Language = keyof typeof LANGUAGE_VERSIONS;
  const [socket] = useState(() =>
    io(API, {
      path: "/socket.io",
      transports: ["websocket"],
      autoConnect: false,
    })
  );
  const [output, setOutput] = useState("");

  const navigate = useNavigate();

  const handleRunCode = async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) return alert("Please log in to run code.");
    setOutput("Executing code...");
    console.log(`1. Sending request to: ${API}/rooms/${room_id}/run`);
    const response = await fetch(`${API}/rooms/${room_id}/run`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        language: language,
      }),
    });

    console.log(
      "2. Received response from backend with status:",
      response.status
    );
  };

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) {
        currentUserIdRef.current = data.user.id;
      }
    });
  }, []);

  useEffect(() => {
    socket.connect();

    return () => {
      socket.disconnect();
    };
  }, [socket]);

  useEffect(() => {
    if (!socket) return;

    const onConnect = () => {
      socket.emit("join", { room_id });
    };

    socket.on("connect", onConnect);

    socket.on("initial-code", (data) => {
      if (data.code) {
        isApplyingRemoteChange.current = true;
        editorRef.current?.setValue(data.code);
        isApplyingRemoteChange.current = false;
      }
    });

    socket.on(
      "code-update",
      (data: { changes: monaco.editor.IModelContentChange[] }) => {
        const model = editorRef.current?.getModel();
        if (!model || !data.changes) {
          return;
        }
        isApplyingRemoteChange.current = true;
        model.applyEdits(
          data.changes.map((c) => ({
            ...c,
            range: new monaco.Range(
              c.range.startLineNumber,
              c.range.startColumn,
              c.range.endLineNumber,
              c.range.endColumn
            ),
          }))
        );
        isApplyingRemoteChange.current = false;
      }
    );

    socket.on(
      "cursor",
      (data: {
        userId: string;
        sid: string;
        lineNumber: number;
        column: number;
      }) => {
        console.log("Cursor event received", data); //remove before hosting
        if (data.userId !== currentUserIdRef.current && monacoRef.current) {
          setRemoteCursors((prev) => ({
            ...prev,
            [data.sid]: {
              position: new monacoRef.current!.Position(
                data.lineNumber,
                data.column
              ),
              color: getColorForId(data.userId),
            },
          }));
        }
      }
    );

    socket.on("user-disconnected", (data: { sid: string }) => {
      setRemoteCursors((prev) => {
        const newCursors = { ...prev };
        delete newCursors[data.sid];
        return newCursors;
      });
    }); //removes cursors

    socket.on("execution-result", (data: { output: string }) => {
      setOutput(data.output);
    });

    socket.on("language-update", (data: { language: Language }) => {
      if (data.language) {
        setLanguage(data.language);
      }
    });

    if (socket.connected) {
      onConnect();
    }

    return () => {
      socket.off("connect");
      socket.off("initial-code");
      socket.off("code-update");
      socket.off("cursor");
      socket.off("execution-result");
      socket.off("language-update");
      socket.off("user-disconnected");
      if (cursorUpdateTimeoutRef.current) {
        clearTimeout(cursorUpdateTimeoutRef.current);
      }
    };
  }, [room_id, socket]);

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
      if (isApplyingRemoteChange.current) {
        return;
      }

      if (currentUserIdRef.current && socket.connected) {
        //clear timeout
        if (cursorUpdateTimeoutRef.current) {
          clearTimeout(cursorUpdateTimeoutRef.current);
        }

        //set new timeout
        cursorUpdateTimeoutRef.current = setTimeout(() => {
          console.log("Emiting cursor position");
          socket.emit("cursor", {
            userId: currentUserIdRef.current,
            sid: socket.id,
            lineNumber: event.position.lineNumber,
            column: event.position.column,
          });
        }, 100); //100ms break
      }
    });

    editor.onDidChangeModelContent((event) => {
      if (isApplyingRemoteChange.current) {
        return;
      }
      socket.emit("code_change", {
        changes: event.changes,
        code: editor.getValue(),
      });
    });
  };

  const onSelect = (lang: Language) => {
    setLanguage(lang);
    if (editorRef.current) {
      editorRef.current.setValue(CODE_SNIPPETS[lang]);
    }
    socket.emit("language_change", { language: lang });
  };

  return (
    <Box bg="gray.900" color="gray.100" minH="100dvh">
      <Box
        as="header"
        px={{ base: 3, md: 6 }}
        py={3}
        borderBottomWidth="2px"
        borderColor="gray.700"
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        gap={3}
      >
        <Box display="flex" alignItems="center" gap={3} flexWrap="wrap">
          <Box color="gray.400">Room:</Box>
          <Box fontFamily="mono" bg="gray.800" px={3} py={1} rounded="md">
            {room_id}
          </Box>
        </Box>

        <Box display="flex" gap={2}>
          <Box
            as="button"
            onClick={() => navigator.clipboard.writeText(window.location.href)}
            px={3}
            py={1.5}
            rounded="md"
            borderWidth="2px"
            borderColor="gray.700"
            _hover={{ bg: "gray.800" }}
          >
            Invite
          </Box>
          <Box
            as="button"
            onClick={() => navigate("/")}
            px={3}
            py={1.5}
            rounded="md"
            bg="red.500"
            _hover={{ bg: "red.400" }}
          >
            Leave
          </Box>
        </Box>
      </Box>

      <Box px={{ base: 3, md: 6 }} py={4}>
        <Box display="flex" gap={4} flexWrap={{ base: "wrap", lg: "nowrap" }}>
          <Box
            flex={{ base: "1 1 100%", lg: "1 1 65%" }}
            minW={{ base: "100%", lg: 0 }}
            bg="gray.850"
            borderWidth="2px"
            borderColor="gray.700"
            rounded="xl"
            overflow="hidden"
          >
            <Box
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              px={4}
              py={3}
              borderBottomWidth="2px"
              borderColor="gray.700"
              bg="gray.900"
            >
              <Box fontWeight="semibold">Editor</Box>
              <LanguageSelector language={language} onSelect={onSelect} />
            </Box>

            <Box px={0} py={0}>
              <Editor
                height="70vh"
                theme="vs-dark"
                language={language}
                defaultValue={CODE_SNIPPETS[language]}
                onMount={OnMount}
                options={{ fontSize: 14, minimap: { enabled: false } }}
              />
            </Box>
          </Box>

          <VStack
            align="stretch"
            flex={{ base: "1 1 100%", lg: "1 1 35%" }}
            minW={{ base: "100%", lg: 0 }}
            gap={4}
            h="full"
          >
            <Box
              bg="gray.850"
              borderWidth="2px"
              borderColor="gray.700"
              rounded="xl"
              overflow="hidden"
              h="45vh" // Fixed height for output
              display="flex"
              flexDirection="column"
            >
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
                px={4}
                py={3}
                borderBottomWidth="2px"
                borderColor="gray.700"
                bg="gray.900"
                flexShrink={0}
              >
                <Box fontWeight="semibold">Output</Box>
                <Box
                  as="button"
                  onClick={handleRunCode}
                  px={3}
                  py={1.5}
                  rounded="md"
                  bg="green.400"
                  color="black"
                  _hover={{ bg: "green.300" }}
                >
                  Run Code
                </Box>
              </Box>

              <Box p={0}>
                <Output output={output} />
              </Box>
            </Box>

            <Box
              bg="gray.850"
              borderWidth="2px"
              borderColor="gray.700"
              rounded="xl"
              overflow="hidden"
              flex="1" 
              minH="40vh" 
              display="flex"
              flexDirection="column"
            >
              <Box
                px={4}
                py={3}
                borderBottomWidth="2px"
                borderColor="gray.700"
                bg="gray.900"
                fontWeight="semibold"
              >
                Chat
              </Box>

              <Box p={0}>
                <Chat socket={socket} />
              </Box>
            </Box>
          </VStack>
        </Box>
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
