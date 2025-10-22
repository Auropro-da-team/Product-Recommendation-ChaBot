import { useState, useEffect } from "react";
import Chatbot from "./components/Chatbot";
import ChatHistory from "./components/ChatHistory";
import {
  fetchChatHistory,
  sendMessageToChatbot,
  startNewConversation,
  deleteChat,
  getSessionId,
} from "./api";
import logo from "./assets/images/logo.png";

function App() {
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const sessionId = getSessionId();

  useEffect(() => {
    const savedChatId = localStorage.getItem("selected_conversation_id");
    console.log("App startup - savedChatId:", savedChatId, "sessionId:", sessionId);
    loadChatHistory(savedChatId);
  }, [sessionId]);

  async function loadChatHistory(savedChatId) {
    setLoading(true);
    setError(null);
    let storedChats = JSON.parse(localStorage.getItem("chatHistory") || "[]");
    console.log("Loaded storedChats from localStorage:", storedChats);

    try {
      // If no stored chats, create a new conversation
      if (storedChats.length === 0) {
        console.log("No stored chats, creating new conversation");
        const newConversationId = await startNewConversation(sessionId, true);
        if (!newConversationId) {
          throw new Error("Failed to create initial conversation");
        }
        const chatData = await fetchChatHistory(sessionId, newConversationId);
        const firstChat = {
          id: newConversationId,
          conversation_id: newConversationId,
          title: "Conversation 1",
          messages: chatData.messages || [],
          timestamp: Date.now(),
        };
        storedChats = [firstChat];
        setChatHistory(storedChats);
        setSelectedChat(firstChat);
        localStorage.setItem("chatHistory", JSON.stringify(storedChats));
        localStorage.setItem("selected_conversation_id", newConversationId);
        console.log("Initialized new chat:", firstChat);
      } else {
        // Validate savedChatId against storedChats
        const selectedChatExists = storedChats.find((chat) => chat.conversation_id === savedChatId);
        if (!selectedChatExists && savedChatId) {
          console.warn("Saved chat ID not found in chatHistory, resetting to first chat");
          savedChatId = storedChats[0].conversation_id;
          localStorage.setItem("selected_conversation_id", savedChatId);
        }

        // Refresh chats from backend, but don't overwrite local data unless necessary
        console.log("Refreshing stored chats from backend");
        const updatedChats = await Promise.all(
          storedChats.map(async (chat) => {
            try {
              const chatData = await fetchChatHistory(sessionId, chat.conversation_id);
              if (chatData.messages && chatData.messages.length > chat.messages.length) {
                console.log(`Updating chat ${chat.conversation_id} with new messages`);
                return {
                  ...chat,
                  messages: chatData.messages,
                  timestamp: Date.now(),
                };
              }
              console.log(`No new messages for chat ${chat.conversation_id}, keeping local data`);
              return chat;
            } catch (error) {
              console.warn(`Failed to refresh chat ${chat.conversation_id}:`, error);
              return chat; // Keep local data if backend fails
            }
          })
        );

        setChatHistory(updatedChats);
        const selected = savedChatId
          ? updatedChats.find((chat) => chat.conversation_id === savedChatId) || updatedChats[0]
          : updatedChats[0];
        console.log("Setting selectedChat:", selected);
        setSelectedChat(selected);
      }
    } catch (error) {
      console.error("Error loading chat history:", error);
      setError("Failed to load chats. Using local data.");
      if (storedChats.length > 0) {
        setChatHistory(storedChats);
        const selected = savedChatId
          ? storedChats.find((chat) => chat.conversation_id === savedChatId) || storedChats[0]
          : storedChats[0];
        setSelectedChat(selected);
      } else {
        setChatHistory([]);
        setSelectedChat(null);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleAddChat() {
    setLoading(true);
    setError(null);
    try {
      const newConversationId = await startNewConversation(sessionId, true);
      if (!newConversationId) throw new Error("Failed to create new conversation");
      const chatData = await fetchChatHistory(sessionId, newConversationId);
      const newChat = {
        id: newConversationId,
        conversation_id: newConversationId,
        title: `Conversation ${chatHistory.length + 1}`,
        messages: chatData.messages || [],
        timestamp: Date.now(),
      };
      console.log("Adding new chat:", newChat);
      setChatHistory((prev) => {
        const updated = [...prev, newChat];
        localStorage.setItem("chatHistory", JSON.stringify(updated));
        return updated;
      });
      setSelectedChat(newChat);
      localStorage.setItem("selected_conversation_id", newConversationId);
    } catch (error) {
      console.error("Error adding chat:", error);
      setError("Failed to create new chat.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteChat(conversationId) {
    setLoading(true);
    setError(null);
    const chatToDelete = chatHistory.find((chat) => chat.conversation_id === conversationId);
    setChatHistory((prev) => {
      const updated = prev.filter((chat) => chat.conversation_id !== conversationId);
      localStorage.setItem("chatHistory", JSON.stringify(updated));
      return updated;
    });
    if (selectedChat?.conversation_id === conversationId) {
      setSelectedChat(null);
      localStorage.removeItem("selected_conversation_id");
    }
    try {
      await deleteChat(sessionId, conversationId);
      if (chatHistory.length === 1) {
        const newConversationId = await startNewConversation(sessionId, true);
        if (!newConversationId) throw new Error("Failed to create new conversation");
        const chatData = await fetchChatHistory(sessionId, newConversationId);
        const newChat = {
          id: newConversationId,
          conversation_id: newConversationId,
          title: "Conversation 1",
          messages: chatData.messages || [],
          timestamp: Date.now(),
        };
        setChatHistory([newChat]);
        setSelectedChat(newChat);
        localStorage.setItem("chatHistory", JSON.stringify([newChat]));
        localStorage.setItem("selected_conversation_id", newConversationId);
      }
    } catch (error) {
      console.error("Error deleting chat:", error);
      setError("Failed to delete chat.");
      if (chatToDelete) {
        setChatHistory((prev) => {
          const updated = [...prev, chatToDelete];
          localStorage.setItem("chatHistory", JSON.stringify(updated));
          return updated;
        });
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectChat(chat) {
    setLoading(true);
    setError(null);
    try {
      const chatData = await fetchChatHistory(sessionId, chat.conversation_id);
      const updatedChat = {
        ...chat,
        messages: chatData.messages || chat.messages,
      };
      console.log("Selecting chat:", updatedChat);
      setSelectedChat(updatedChat);
      localStorage.setItem("selected_conversation_id", chat.conversation_id);
      updateChatHistory(chat.conversation_id, updatedChat.messages);
    } catch (error) {
      console.error("Error selecting chat:", error);
      setError("Failed to select chat. Using local data.");
      setSelectedChat(chat);
    } finally {
      setLoading(false);
    }
  }

  function updateChatHistory(chatId, newMessages) {
    if (!newMessages) {
      console.warn("No messages to update for chatId:", chatId);
      return;
    }
    setChatHistory((prevHistory) => {
      const updatedHistory = prevHistory.map((chat) =>
        chat.conversation_id === chatId
          ? { ...chat, messages: newMessages, timestamp: Date.now() }
          : chat
      );
      console.log("Updating chat history in localStorage:", updatedHistory);
      localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
      return updatedHistory;
    });
  }

  return (
    <div className="flex h-screen">
      {error && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white p-4 rounded-lg shadow-lg">
          {error}
          <button className="ml-4 text-sm underline" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}
      <ChatHistory
        chatHistory={chatHistory}
        onAddChat={handleAddChat}
        onDeleteChat={handleDeleteChat}
        onSelectChat={handleSelectChat}
      />
      <Chatbot
        selectedChat={selectedChat}
        updateChatHistory={updateChatHistory}
        chatHistory={chatHistory}
      />
      <div className="fixed left-4 bottom-4 z-20">
        <img
          src={logo}
          alt="Logo"
          className="w-40 h-10 object-contain"
          onError={(e) => {
            console.error("Logo failed to load");
            e.currentTarget.src = "https://via.placeholder.com/150";
          }}
        />
      </div>
    </div>
  );
}

export default App;
