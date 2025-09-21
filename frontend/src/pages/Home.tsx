import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { supabase } from "../supabaseClient";
import {
  Box,
  Container,
  Heading,
  Stack,
  Field,
  Input,
  InputGroup,
  IconButton,
  Button,
  Text,
  Separator,
} from "@chakra-ui/react";
import { LuEye, LuEyeOff } from "react-icons/lu";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function Home() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [session, setSession] = useState<any>(null);
  const [showPw, setShowPw] = useState(false);

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
    <Box
      minH="100dvh"
      bg="gray.900"
      color="gray.100"
      display="grid"
      placeItems="center"
      px={4}
    >
      <Container maxW="md">
        <Stack
          gap={6}
          bg="gray.800"
          borderWidth="1px"
          borderColor="gray.700"
          rounded="xl"
          p={6}
        >
          <Heading size="md">Real time collab & code</Heading>
          {!session ? (
            <>
              <Field.Root id="email" required>
                <Field.Label>Email</Field.Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value.trim())}
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </Field.Root>

              <Field.Root id="password" required>
                <Field.Label>
                  Password <Field.RequiredIndicator />
                </Field.Label>

                <InputGroup
                  endElement={
                    <IconButton
                      aria-label={showPw ? "Hide password" : "Show password"}
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowPw((s) => !s)}
                    >
                      {showPw ? <LuEyeOff /> : <LuEye />}
                    </IconButton>
                  }
                >
                  <Input
                    id="password"
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="current-password"
                  />
                </InputGroup>
              </Field.Root>

              <Stack direction="row">
                <Button onClick={signIn} colorScheme="purple" flex="1">
                  Sign In
                </Button>
                <Button
                  onClick={signUp}
                  colorScheme="purple" variant="solid"
                  flex="1"
                >
                  Sign Up
                </Button>
              </Stack>
              <Text fontSize="sm" color="gray.400">
                {status}
              </Text>
            </>
          ) : (
            <>
              <Text fontSize="sm" color="gray.300">
                Signed in as{" "}
                <Text as="span" fontWeight="semibold">
                  {session.user.email}
                </Text>
              </Text>
              <Stack direction="row">
                <Button onClick={handleCreateRoom} colorScheme="green" flex="1">
                  Create Room
                </Button>
                <Button
                  onClick={onJoin}
                  variant="solid"
                  flex="1"
                >
                  Join Room
                </Button>
              </Stack>
              <Separator borderColor="gray.700" variant="solid"
                  flex="1" />
              <Button onClick={signOut} >
                Sign Out
              </Button>
              <p>{status}</p>
            </>
          )}
        </Stack>
      </Container>
    </Box>
  );
}
