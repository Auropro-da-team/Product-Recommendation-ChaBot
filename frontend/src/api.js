const BASE_URL = import.meta.env.VITE_BACKEND_URL;

let cachedConversationId = null;
const activeRequests = new Map();

export const Kozmo = {
  getSessionId: () => {
    let sessionId = localStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = Math.random().toString(36).substr(2, 9);
      localStorage.setItem("session_id", sessionId);
      console.log("Generated new session_id:", sessionId);
    }
    return sessionId;
  },

  getConversationId: (selectedChat) => {
    if (selectedChat?.conversation_id) {
      console.log("Using selected chat conversation_id:", selectedChat.conversation_id);
      cachedConversationId = selectedChat.conversation_id;
      return selectedChat.conversation_id;
    }
    if (cachedConversationId) {
      console.log("Using cached conversation_id:", cachedConversationId);
      return cachedConversationId;
    }
    let conversationId = localStorage.getItem("conversation_id");
    if (!conversationId) {
      conversationId = Math.random().toString(36).substr(2, 9);
      localStorage.setItem("conversation_id", conversationId);
      console.log("Generated new conversation_id:", conversationId);
    }
    cachedConversationId = conversationId;
    return conversationId;
  },

  getLocalChatHistory: () => {
    try {
      const history = localStorage.getItem("chatHistory") || "[]";
      return JSON.parse(history);
    } catch (error) {
      console.error("Error parsing chatHistory:", error);
      return [];
    }
  },

  saveChatHistory: (chatHistory) => {
    try {
      localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
      console.log("Saved chatHistory to localStorage:", chatHistory);
    } catch (error) {
      console.error("Error saving chatHistory:", error);
    }
  },

  getLocalConversationHistory: (conversationId) => {
    const history = Kozmo.getLocalChatHistory();
    const chat = history.find((c) => c.conversation_id === conversationId);
    return chat?.messages || [];
  },

  saveToLocalStorage: (conversationId, messages) => {
    const history = Kozmo.getLocalChatHistory();
    const chatIndex = history.findIndex((c) => c.conversation_id === conversationId);
    const filteredMessages = messages.map((msg) => ({
      ...msg,
      image_data: msg.has_image && msg.image_data?.startsWith("data:image/") && msg.image_data.length > 1_000_000
        ? null
        : msg.image_data,
    }));
    const updatedChat = {
      id: conversationId,
      conversation_id: conversationId,
      title: history[chatIndex]?.title || `Conversation ${history.length + 1}`,
      messages: filteredMessages,
      timestamp: Date.now(),
    };
    if (chatIndex >= 0) {
      history[chatIndex] = updatedChat;
    } else {
      history.push(updatedChat);
    }
    Kozmo.saveChatHistory(history);
  },

  fetchChatHistory: async (sessionId, conversationId, retries = 3) => {
    console.log("fetchChatHistory:", { sessionId, conversationId, retries });
    if (!sessionId || !conversationId) {
      console.error("Missing session_id or conversation_id");
      return { conversation_id: conversationId, messages: [], timestamp: Date.now() };
    }

    const localMessages = Kozmo.getLocalConversationHistory(conversationId);
    const localChat = Kozmo.getLocalChatHistory().find((c) => c.conversation_id === conversationId);
    const localTimestamp = localChat?.timestamp || 0;

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        console.log(`Fetching chat history (attempt ${attempt}): ${BASE_URL}/chat/${sessionId}/${conversationId}`);
        const response = await fetch(`${BASE_URL}/chat/${sessionId}/${conversationId}`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.warn(`Fetch failed (attempt ${attempt}): ${response.status} - ${errorText}`);
          if (response.status === 404 && attempt === retries) {
            console.log("Conversation not found, returning local messages");
            return { conversation_id: conversationId, messages: localMessages, timestamp: localTimestamp };
          }
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Fetched chat history:", data);

        let backendMessages = (data.messages || []).filter(
          (msg) => !((msg.role === "user" || msg.user) && msg.content === "init")
        ).map((msg) => ({
          role: msg.role || (msg.user ? "user" : "assistant"),
          content: msg.content || msg.user || msg.bot,
          products: msg.table || [],
          orders: msg.orders_table || [],
          timestamp: msg.timestamp || Date.now(),
          has_image: msg.has_image || !!msg.image_url || false,
          image_data: msg.image_url || msg.image_data || null,
        }));

        const backendTimestamp = data.timestamp || Date.now();
        let mergedMessages = [];

        if (backendTimestamp > localTimestamp && backendMessages.length > 0) {
          console.log("Backend data is newer, updating local messages");
          mergedMessages = [...backendMessages];
          localMessages.forEach((localMsg) => {
            if (!mergedMessages.some((m) => m.timestamp === localMsg.timestamp && m.role === localMsg.role)) {
              mergedMessages.push(localMsg);
            }
          });
          mergedMessages.sort((a, b) => a.timestamp - b.timestamp);
          // Filter out "init" messages from the merged list
          mergedMessages = mergedMessages.filter(
            (msg) => !(msg.role === "user" && msg.content === "init")
          );
          console.log("Filtered merged messages (removed init):", mergedMessages);
          Kozmo.saveToLocalStorage(conversationId, mergedMessages);
          return { conversation_id: conversationId, messages: mergedMessages, timestamp: backendTimestamp };
        } else {
          console.log("Local data is up-to-date or backend data is empty, keeping local messages");
          // Filter out "init" messages from localMessages before returning
          const filteredLocalMessages = localMessages.filter(
            (msg) => !(msg.role === "user" && msg.content === "init")
          );
          console.log("Filtered local messages (removed init):", filteredLocalMessages);
          return { conversation_id: conversationId, messages: filteredLocalMessages, timestamp: localTimestamp };
        }
      } catch (error) {
        console.error(`fetchChatHistory error (attempt ${attempt}):`, error);
        if (attempt === retries) {
          console.log("Max retries reached, returning local messages");
          // Filter out "init" messages from localMessages in case of failure
          const filteredLocalMessages = localMessages.filter(
            (msg) => !(msg.role === "user" && msg.content === "init")
          );
          console.log("Filtered local messages (removed init) on failure:", filteredLocalMessages);
          return { conversation_id: conversationId, messages: filteredLocalMessages, timestamp: localTimestamp };
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  },

  sendMessageToChatbot: async (userInput, options = {}, retries = 3) => {
    console.log("sendMessageToChatbot:", { userInput, options, retries });
    const sessionId = options.session_id || Kozmo.getSessionId();
    let conversationId = options.conversation_id || Kozmo.getConversationId(options.selectedChat);
    const submissionId = options.submission_id || Date.now().toString();

    if (!sessionId || !conversationId) {
      console.error("Missing session_id or conversation_id");
      return { botResponse: "Error: Unable to establish session.", products: [], orders: [], image_url: null };
    }

    const isImage = options.isImage || false;
    let body, headers = {}, endpoint = `${BASE_URL}/chat/${sessionId}/${conversationId}`, imageData = null;

    if (isImage) {
      endpoint = `${BASE_URL}/chat/${sessionId}/${conversationId}/with-image`;
      const file = userInput.get("file");
      const imageUrl = userInput.get("image_url");
      if (file) {
        try {
          const reader = new FileReader();
          imageData = await new Promise((resolve) => {
            reader.onload = () => {
              console.log("FileReader completed:", reader.result?.slice(0, 50) + "...");
              resolve(reader.result);
            };
            reader.onerror = () => {
              console.error("FileReader error:", reader.error);
              resolve(null);
            };
            reader.readAsDataURL(file);
          });
        } catch (error) {
          console.error("Error reading file:", error);
          imageData = null;
        }
      } else if (imageUrl) {
        imageData = imageUrl;
      }
      body = userInput;
    } else {
      if (!userInput.trim()) {
        return { botResponse: "Cannot send empty message", products: [], orders: [], image_url: null };
      }
      headers = { "Content-Type": "application/json" };
      body = JSON.stringify({ user_input: userInput });
    }

    let conversationHistory = Kozmo.getLocalConversationHistory(conversationId);
    conversationHistory.push({
      role: "user",
      content: isImage ? (userInput.get("user_input") || "") : userInput,
      has_image: isImage,
      image_data: imageData,
      timestamp: Date.now(),
    });
    Kozmo.saveToLocalStorage(conversationId, conversationHistory);

    const controller = new AbortController();
    activeRequests.set(submissionId, controller);

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        console.log(`Sending request (attempt ${attempt}): ${endpoint}`);
        const response = await fetch(endpoint, {
          method: "POST",
          headers: isImage ? {} : headers,
          body,
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.warn(`Send failed (attempt ${attempt}): ${response.status} - ${errorText}`);
          if (response.status === 404 && attempt === retries) {
            console.log("Conversation not found, creating new one");
            const newConversationId = await Kozmo.startNewConversation(sessionId);
            if (!newConversationId) throw new Error("Failed to create new conversation");
            return Kozmo.sendMessageToChatbot(userInput, { ...options, conversation_id: newConversationId });
          }
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();
        console.log("API response:", data);

        let botResponse = data.response || "No response from chatbot.";
        let products = (data.products || []).map((p, i) => ({ ...p, id: i + 1 }));
        let orders = data.orders || [];
        let imageUrl = data.image_url || null;

        if (orders.length > 0) {
          console.log("Processing orders data:", orders);
          let tableData = "\n\n**Order Details**:\n\n";
          orders.forEach((order, index) => {
            const orderFields = {
              "Order ID": order["Order ID"] || "N/A",
              "Date of Order": order["Date of Order"] || "N/A",
              "Order Status": order["Order Status"] || "N/A",
              "Date of Delivery": order["Date of Delivery"] || "N/A",
              "Quantity": order["Quantity"] !== undefined ? order["Quantity"] : "N/A",
              "Product Name": order["Product Name"] || "N/A",
              "Customer Name": order["Customer Name"] || "N/A",
            };

            if (orders.length > 1) {
              tableData += `**Order ${index + 1}**\n`;
            }

            tableData += "| Field           | Value            |\n";
            tableData += "|-----------------|------------------|\n";
            Object.entries(orderFields).forEach(([key, value]) => {
              tableData += `| ${key.padEnd(15)} | ${String(value).padEnd(16)} |\n`;
            });
            tableData += "\n";
          });
          console.log("Generated Markdown table:\n", tableData);
          botResponse += tableData;
        }

        conversationHistory.push({
          role: "assistant",
          content: botResponse,
          products,
          orders,
          has_image: !!imageUrl,
          image_data: imageUrl,
          timestamp: Date.now(),
        });
        Kozmo.saveToLocalStorage(conversationId, conversationHistory);

        return { botResponse, products, orders, image_url: imageUrl };
      } catch (error) {
        if (error.name === "AbortError") {
          console.log("Request aborted:", submissionId);
          return { botResponse: "Request cancelled.", products: [], orders: [], image_url: null };
        }
        console.error(`sendMessageToChatbot error (attempt ${attempt}):`, error);
        if (attempt === retries) {
          conversationHistory.pop();
          Kozmo.saveToLocalStorage(conversationId, conversationHistory);
          return { botResponse: "Error sending message.", products: [], orders: [], image_url: null };
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      } finally {
        activeRequests.delete(submissionId);
      }
    }
  },

  startNewConversation: async (sessionId, forceNew = false, retries = 3) => {
    console.log("startNewConversation:", { sessionId, forceNew, retries });
    if (!sessionId) {
      console.error("Missing session_id");
      return null;
    }

    if (Kozmo.isCreatingConversation) {
      console.log("Conversation creation in progress, returning cached ID");
      return cachedConversationId || localStorage.getItem("conversation_id");
    }

    if (!forceNew && cachedConversationId) {
      console.log("Using cached conversation_id:", cachedConversationId);
      return cachedConversationId;
    }

    Kozmo.isCreatingConversation = true;
    const newConversationId = Math.random().toString(36).substr(2, 9);

    try {
      for (let attempt = 1; attempt <= retries; attempt++) {
        console.log(`Creating new conversation (attempt ${attempt}): ${BASE_URL}/chat/${sessionId}/${newConversationId}`);
        try {
          const response = await fetch(`${BASE_URL}/chat/${sessionId}/${newConversationId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_input: "init" }),
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.warn(`Init failed (attempt ${attempt}): ${response.status} - ${errorText}`);
            if (attempt === retries) {
              throw new Error(`HTTP error after ${retries} attempts: ${response.status} - ${errorText}`);
            }
            throw new Error(`HTTP error: ${response.status}`);
          }

          const data = await response.json();
          console.log("Init response:", data);

          localStorage.setItem("conversation_id", newConversationId);
          cachedConversationId = newConversationId;
          console.log("New conversation created:", newConversationId);

          const initialMessages = [{
            role: "user",
            content: "init",
            timestamp: Date.now(),
            has_image: false,
            image_data: null,
          }];

          if (data.response) {
            initialMessages.push({
              role: "assistant",
              content: data.response,
              timestamp: Date.now(),
              has_image: false,
              image_data: null,
            });
          }

          Kozmo.saveToLocalStorage(newConversationId, initialMessages);
          await Kozmo.fetchChatHistory(sessionId, newConversationId);
          return newConversationId;
        } catch (error) {
          console.error(`startNewConversation error (attempt ${attempt}):`, error);
          if (attempt === retries) {
            console.log("Max retries reached for init, returning null");
            return null;
          }
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
      }
    } finally {
      Kozmo.isCreatingConversation = false;
    }
  },

  deleteChat: async (sessionId, conversationId) => {
    console.log("deleteChat:", { sessionId, conversationId });
    if (!sessionId || !conversationId) {
      console.error("Missing session_id or conversation_id");
      throw new Error("Missing IDs");
    }

    try {
      const response = await fetch(`${BASE_URL}/chat/${sessionId}/${conversationId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error: ${response.status} - ${errorText}`);
      }

      console.log("Chat deleted:", conversationId);
      const chatHistory = Kozmo.getLocalChatHistory();
      const updatedHistory = chatHistory.filter((chat) => chat.conversation_id !== conversationId);
      Kozmo.saveChatHistory(updatedHistory);
      if (localStorage.getItem("conversation_id") === conversationId) {
        localStorage.setItem("conversation_id", "");
        cachedConversationId = null;
      }
      return true;
    } catch (error) {
      console.error("Error deleting chat:", error);
      throw error;
    }
  },
};

Kozmo.isCreatingConversation = false;

export const {
  getSessionId,
  getConversationId,
  getLocalChatHistory,
  saveChatHistory,
  getLocalConversationHistory,
  saveToLocalStorage,
  fetchChatHistory,
  sendMessageToChatbot,
  startNewConversation,
  deleteChat,
} = Kozmo;