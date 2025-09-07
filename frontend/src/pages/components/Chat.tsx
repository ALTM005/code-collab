import { useEffect, useState } from "react";
import {
  Box,
  Heading,
  VStack,
  Text,
  HStack,
  Input,
  Button,
} from "@chakra-ui/react";
import { type Socket } from "socket.io-client";

interface ChatProps {
  socket: Socket | null;
}
export default function Chat({ socket }: ChatProps) {
  const [messages, setMessages] = useState<{ sender: string; text: string }[]>(
    []
  );
  const [currentMessage, setCurrentMessage] = useState("");

  useEffect(() => {
    const onNewMessage = (newMessage: { sender: string; text: string }) => {
      setMessages((prevMessages) => [...prevMessages, newMessage]);
    };

    socket?.on("new-message", onNewMessage);
    return () => {
      socket?.off("new-message", onNewMessage);
    };
  }, [socket]);

  const handleSendMessage = () => {
    if (currentMessage.trim() && socket) {
      console.log("1. handleSendMessage triggered. Message:", currentMessage);
      console.log("2. Is socket connected?", socket?.connected);
      socket.emit("chat_message", { text: currentMessage });
      setCurrentMessage("");
    }
  };

  return (
    <Box mt={4} flex={1}>
      <VStack
        align="stretch"
        gap={2}
        height="250px"
        overflowY="auto"
        borderRadius="md"
        p={3}
      >
        {messages.map((mesg, index) => (
          <Text key={index}>
            <strong>{mesg.sender}:</strong>
            {mesg.text}
          </Text>
        ))}
      </VStack>
      <HStack px={3} py={2}>
        <Input
          value={currentMessage}
          onChange={(event) => {
            setCurrentMessage(event.target.value);
          }}
          placeholder="Type a message..."
          onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
          borderColor="gray.700"
          borderWidth="2px"
        />
        <Box
          as="button"
          onClick={handleSendMessage}
          px={4}
          py={2}
          rounded="md"
          bg="blue.500"
          color="white"
          fontSize="sm"
          _hover={{
            bg: "blue.400",
            boxShadow: "md",
          }}
        >
          Send
        </Box>
      </HStack>
    </Box>
  );
}
