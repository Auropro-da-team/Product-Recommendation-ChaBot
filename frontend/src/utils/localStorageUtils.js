import { useState, useEffect } from "react";

export const useLocalStorageState = (key, defaultValue) => {
  const [state, setState] = useState(() => {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : defaultValue;
    } catch (error) {
      console.error(`🚨 Error reading ${key} from localStorage:`, error);
      return defaultValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.error(`🚨 Error writing ${key} to localStorage:`, error);
    }
  }, [key, state]);

  return [state, setState];
};

export const useSessionManagement = () => {
  const [sessionId, setSessionId] = useLocalStorageState("session_id", null);

  useEffect(() => {
    if (!sessionId) {
      const newSessionId = Math.random().toString(36).substr(2, 9);
      setSessionId(newSessionId);
      console.log("✨ Generated New Session ID:", newSessionId);
    }
  }, [sessionId, setSessionId]);

  return sessionId;
};

export const useChatHistory = (sessionId) => {
  const [chatHistory, setChatHistory] = useLocalStorageState("chatHistory", []);
  const [selectedChatId, setSelectedChatId] = useLocalStorageState("selectedChatId", null);

  const selectedChat = chatHistory.find((chat) => chat.id === selectedChatId) || null;

  const addChat = (chat) => {
    setChatHistory((prev) => {
      const updatedHistory = [...prev, chat];
      localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
      return updatedHistory;
    });
    setSelectedChatId(chat.id);
  };

  const deleteChat = (chatId) => {
    setChatHistory((prev) => {
      const updatedHistory = prev.filter((chat) => chat.id !== chatId);
      localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
      return updatedHistory;
    });
    if (selectedChatId === chatId) {
      setSelectedChatId(chatHistory.length > 1 ? chatHistory[0].id : null);
    }
  };

  const updateChatMessages = (chatId, messages) => {
    setChatHistory((prev) => {
      const updatedHistory = prev.map((chat) =>
        chat.id === chatId ? { ...chat, messages, timestamp: Date.now() } : chat
      );
      localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
      return updatedHistory;
    });
  };

  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.key === "chatHistory") {
        try {
          const newHistory = JSON.parse(event.newValue || "[]");
          setChatHistory(newHistory);
          if (newHistory.length > 0 && !selectedChatId) {
            setSelectedChatId(newHistory[0].id);
          }
        } catch (error) {
          console.error("🚨 Error syncing chatHistory from storage event:", error);
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [setChatHistory, setSelectedChatId, selectedChatId]);

  return {
    chatHistory,
    selectedChat,
    setSelectedChat: (chat) => setSelectedChatId(chat?.id || null),
    addChat,
    deleteChat,
    updateChatMessages,
  };
};

export const persistImage = (imageUrl) => {
  if (!imageUrl) return null;
  try {
    const imageKey = `image_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem(imageKey, imageUrl);
    return imageKey;
  } catch (error) {
    console.error("🚨 Error persisting image URL:", error);
    return null;
  }
};

export const retrievePersistedImage = (imageKey) => {
  if (!imageKey) return null;
  try {
    return localStorage.getItem(imageKey) || null;
  } catch (error) {
    console.error("🚨 Error retrieving persisted image URL:", error);
    return null;
  }
};

export const clearAllPersistentData = () => {
  try {
    localStorage.clear();
    console.log("✅ LocalStorage cleared");
  } catch (error) {
    console.error("🚨 Error clearing localStorage:", error);
  }
};