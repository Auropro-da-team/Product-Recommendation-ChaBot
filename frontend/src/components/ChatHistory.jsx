import { useCallback, memo } from "react";
import newMessageIcon from "../assets/images/new-message.png";
import { BsChatLeftText } from "react-icons/bs";
// Memoize the ChatHistory component to prevent unnecessary re-renders
const ChatHistory = memo(({ chatHistory, onAddChat, onDeleteChat, onSelectChat }) => {
  // Memoized event handlers
  const handleAddChat = useCallback(() => onAddChat(), [onAddChat]);
  const handleDeleteChat = useCallback((id, e) => {
    e.stopPropagation();
    onDeleteChat(id);
  }, [onDeleteChat]);
  const handleSelectChat = useCallback((chat) => onSelectChat(chat), [onSelectChat]);

  console.log("ChatHistory called", chatHistory);

  return (
    <div className="w-64 bg-white shadow-xl p-4 h-full flex flex-col border border-gray-300 rounded-lg backdrop-blur-md">
      
      
      
      
      
      
      
      <h3 className="text-primary-black font-semibold mb-4 text-lg font-urbanist flex items-center gap-2  pl-10 ">
      <BsChatLeftText className="text-lg"/>History
      </h3>

      <button
        className="mb-4 bg-gradient-to-r from-black to-gray-800 text-white py-2 px-4 rounded-lg w-full flex items-center justify-center gap-2 
                   hover:from-gray-900 hover:to-black transition-all duration-200 shadow-md"
        onClick={handleAddChat}
        aria-label="Start a new chat"
      >
        <img src={newMessageIcon} alt="New Chat" className="w-5 h-5" />
        New Chat
      </button>


      <div className="space-y-2 overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-200">
        {chatHistory.length === 0 ? (
          <p className="text-gray-500 italic text-center">No chats yet</p>
        ) : (
          chatHistory.map((chat, index) => {
            // ✅ Extract last message safely
            const lastMessageObj = (chat.messages || []).length > 0 ? chat.messages[chat.messages.length - 1] : null;
            const lastMessage =lastMessageObj? " " : "No messages yet";

            // ✅ Handle timestamp safely
            let formattedDate = "Unknown Date";
            if (chat.timestamp) {
              try {
                let timestampMillis = chat.timestamp.toMillis ? chat.timestamp.toMillis() : chat.timestamp;
                let dateObj = new Date(timestampMillis);
                if (!isNaN(dateObj.getTime())) {
                  formattedDate = dateObj.toLocaleString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                }
              } catch (error) {
                console.warn("⚠️ Error parsing timestamp:", error);
              }
            }

            // ✅ Ensure unique key
            const timestampMillis = chat.timestamp?.toMillis ? chat.timestamp.toMillis() : Date.now();
            const key = `${chat.id}-${timestampMillis}-${index}`;

            // ✅ Extract product info safely (assuming chat.products is an array)
            const productCount = chat.products?.length || 0;
            const productText = productCount > 0 ? `(${productCount} product${productCount > 1 ? "s" : ""})` : "";

            return (
              <div
                key={key}
                className="bg-white/70 p-3 rounded-lg shadow-sm cursor-pointer hover:bg-gray-200 flex flex-col 
                           transition-all duration-200 border border-gray-300 backdrop-blur-lg"
                onClick={() => {
                  console.log(`🆕 Selecting chat: ${chat.id}`, chat);
                  handleSelectChat(chat);
                }}
                role="button"
                tabIndex={0}
                aria-label={`Open chat ${chat.title || `Conversation ${index + 1}`}`}
              >
                <div className="flex justify-between items-center">
                  <div className="flex flex-col">
                    <span className="truncate text-gray-800 font-medium font-poppins">
                      {chat.title || `Conversation ${index + 1}`} {productText}
                    </span>
                    <p className="text-xs text-gray-500">{formattedDate}</p>
                  </div>
                  <button
                    className="text-red-500 text-sm ml-2 hover:text-red-700 transition-all duration-200"
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    aria-label={`Delete chat ${chat.title || `Conversation ${index + 1}`}`}
                  >
                     <span aria-hidden="true">✖</span>
                  </button>
                </div>

                <p className="text-sm text-gray-600 italic truncate">{lastMessage}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

export default ChatHistory;