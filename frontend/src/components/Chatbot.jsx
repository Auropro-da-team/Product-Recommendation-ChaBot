import { useState, useEffect, useRef } from "react";
import { useImmer } from "use-immer";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";
import { sendMessageToChatbot, startNewConversation, fetchChatHistory, getSessionId } from "../api";

import left1 from "../assets/images/left1.png";
import left2 from "../assets/images/left2.png";
import left3 from "../assets/images/left3.png";
import left4 from "../assets/images/left4.png";
import left5 from "../assets/images/left5.png";
import left6 from "../assets/images/left6.png";
import right1 from "../assets/images/right1.png";
import right2 from "../assets/images/right2.png";
import right3 from "../assets/images/right3.png";
import right4 from "../assets/images/right4.png";
import right5 from "../assets/images/right5.png";
import right6 from "../assets/images/right6.png";

const leftImages = [left1, left2, left3, left4, left5, left6];
const rightImages = [right1, right2, right3, right4, right5, right6];

function Chatbot({ selectedChat, updateChatHistory, chatHistory = [] }) {
  const [messages, setMessages] = useImmer(selectedChat ? selectedChat.messages : []);
  const [newMessage, setNewMessage] = useState("");
  const [imageIndex, setImageIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(selectedChat?.conversation_id || null);
  const [sessionId] = useState(getSessionId());
  const submissionRef = useRef(null);

  useEffect(() => {
    const loadChat = async () => {
      if (selectedChat?.conversation_id) {
        console.log("Fetching chat history for conversation_id:", selectedChat.conversation_id);
        const chatData = await fetchChatHistory(sessionId, selectedChat.conversation_id);
        console.log("Fetched chat data:", chatData);
        setMessages(chatData.messages || []);
        setConversationId(selectedChat.conversation_id);
      } else {
        setMessages([]);
        setConversationId(null);
      }
    };
    loadChat();
  }, [selectedChat, sessionId, setMessages]);

  useEffect(() => {
    const interval = setInterval(() => {
      setImageIndex((prev) => (prev + 1) % leftImages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  async function submitNewMessage(message) {
    if (isLoading) {
      console.log("Submission blocked: isLoading is true");
      return;
    }

    const submissionId = Date.now();
    if (submissionRef.current === submissionId) {
      console.log("Duplicate submission blocked:", submissionId);
      return;
    }
    submissionRef.current = submissionId;
    console.log("submitNewMessage ID:", submissionId);

    setIsLoading(true);
    const { type, content, image } = message;
    const trimmedMessage = content.trim();
    if (!trimmedMessage && !image) {
      console.error("❌ Error: Empty message and no image not sent!");
      setIsLoading(false);
      return;
    }

    const userMessage = {
      role: "user",
      type: "text",
      content: trimmedMessage || "User uploaded an image",
      has_image: !!image,
      image_data: image || null,
      timestamp: Date.now(),
    };

    console.log("Submitting user message:", userMessage);
    console.log("Image data length:", image ? image.length : "No image");

    setMessages((draft) => [...draft, userMessage, { role: "assistant", content: "", loading: true }]);
    setNewMessage("");

    try {
      let currentConversationId = conversationId;

      if (!currentConversationId) {
        currentConversationId = await startNewConversation(sessionId);
        if (!currentConversationId) {
          throw new Error("❌ Error: Failed to create a new conversation.");
        }
        setConversationId(currentConversationId);
      }

      const messageToSend = trimmedMessage || "User uploaded an image";
      let reply;
      if (image) {
        const base64Data = image.split(",")[1];
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: "image/jpeg" });

        const formData = new FormData();
        formData.append("file", blob, "uploaded_image.jpg");
        formData.append("user_input", messageToSend);

        console.log("Sending image request with ID:", submissionId);
        reply = await sendMessageToChatbot(formData, {
          conversation_id: currentConversationId,
          session_id: sessionId,
          isImage: true,
        });
      } else {
        reply = await sendMessageToChatbot(messageToSend, {
          conversation_id: currentConversationId,
          session_id: sessionId,
        });
      }

      const assistantMessage = {
        role: "assistant",
        type: "text",
        content: reply.botResponse,
        products: (reply.products || []).filter(product => product && typeof product === 'object'),
        loading: false,
        timestamp: Date.now(),
      };

      setMessages((draft) => {
        draft[draft.length - 1] = assistantMessage;
      });

      if (!selectedChat) {
        const newChat = {
          conversation_id: currentConversationId,
          title: "New Conversation",
          messages: [userMessage, assistantMessage],
        };
        console.log("Updating chat history (new chat):", newChat);
        updateChatHistory(currentConversationId, newChat.messages);
      } else {
        console.log("Updating chat history (existing chat):", [...messages, userMessage, assistantMessage]);
        updateChatHistory(currentConversationId, [...messages, userMessage, assistantMessage]);
      }
    } catch (error) {
      console.error("🚨 Error fetching chatbot response:", error);
      setMessages((draft) => {
        draft[draft.length - 1] = {
          role: "assistant",
          type: "text",
          content: "❌ Error fetching response. Try again!",
          loading: false,
          timestamp: Date.now(),
        };
      });
    } finally {
      setIsLoading(false);
      submissionRef.current = null;
    }
  }

  return (
    <div className="relative flex flex-col h-screen w-full bg-white font-urbanist">
      <div className="fixed left-13 top-1/2 md:bottom-16 transform -translate-y-1/2 opacity-90 transition-transform duration-700 ease-in-out z-0">
        <img src={leftImages[imageIndex]} alt="Left Avatar" className="w-40 md:w-56 lg:w-72 h-auto object-contain drop-shadow-lg" />
      </div>
      <div className="fixed right-5 top-[53%] md:bottom-16 transform -translate-y-1/2 opacity-90 transition-transform duration-700 ease-in-out z-0">
        <img src={rightImages[imageIndex]} alt="Right Avatar" className="w-32 md:w-48 lg:w-64 h-auto object-contain drop-shadow-lg" />
      </div>

      {messages.length === 0 && (
        <div className="mt-6 text-center text-gray-800 text-xl font-light w-full px-4 min-h-[50vh] flex flex-col items-center justify-center gap-6">
          <div className="flex flex-col items-center justify-center">
            <p className="text-2xl font-semibold mb-1"> 👋 Welcome! </p>
            <div className="flex items-center justify-center gap-1">
              <p className="text-lg">Ask me anything about</p>
              <div className="relative h-6 w-28 overflow-hidden">
                <div className="scrolling-text flex flex-col animate-scroll">
                  <span className="text-lg font-medium text-gray-800 h-6 flex items-center justify-center">Eyewear</span>
                  <span className="text-lg font-medium text-gray-800 h-6 flex items-center justify-center">Eye glasses</span>
                  <span className="text-lg font-medium text-gray-800 h-6 flex items-center justify-center">Sunglasses</span>
                  <span className="text-lg font-medium text-gray-800 h-6 flex items-center justify-center">Eyewear</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex-grow overflow-y-auto px-4 relative z-10">
        <ChatMessages messages={messages} isLoading={isLoading} />
      </div>
      <div className="sticky bottom-0 w-full bg-white shadow-md px-4 pt-0 pb-4">
        <ChatInput newMessage={newMessage} isLoading={isLoading} setNewMessage={setNewMessage} submitNewMessage={submitNewMessage} />
      </div>
    </div>
  );
}

export default Chatbot;