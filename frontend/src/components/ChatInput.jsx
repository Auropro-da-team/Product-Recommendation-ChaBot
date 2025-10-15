import { useCallback, useRef, useState } from "react";
import useAutosize from "../hooks/useAutosize";
import sendIcon from "../assets/images/send.png";
import uploadIcon from "../assets/images/upload-icon.png";

function ChatInput({ newMessage, isLoading, setNewMessage, submitNewMessage }) {
  const textareaRef = useAutosize(newMessage);
  const fileInputRef = useRef(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imageError, setImageError] = useState(null);
  const submissionRef = useRef(null);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey && !isLoading) {
        e.preventDefault();
        if (newMessage.trim() || selectedImage) {
          const submissionId = Date.now();
          if (submissionRef.current === submissionId) return;
          submissionRef.current = submissionId;
          console.log("KeyDown submission ID:", submissionId);
          submitNewMessage({ type: "text", content: newMessage, image: selectedImage });
          setNewMessage("");
          setSelectedImage(null);
          setImageError(null);
          if (fileInputRef.current) fileInputRef.current.value = null;
        }
      }
    },
    [isLoading, submitNewMessage, newMessage, selectedImage, setNewMessage]
  );

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      console.log("File selected:", file.name, file.size);
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        setImageError("Image is too large. Please upload an image smaller than 5MB.");
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        setSelectedImage(event.target.result);
        setImageError(null);
        if (fileInputRef.current) fileInputRef.current.value = null;
      };
      reader.onerror = () => {
        setImageError("Failed to load image. Please try again.");
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    setImageError(null);
    if (fileInputRef.current) fileInputRef.current.value = null;
  };

  const handleSendClick = () => {
    if ((newMessage.trim() || selectedImage) && !isLoading) {
      const submissionId = Date.now();
      if (submissionRef.current === submissionId) return;
      submissionRef.current = submissionId;
      console.log("SendClick submission ID:", submissionId);
      submitNewMessage({ type: "text", content: newMessage, image: selectedImage });
      setNewMessage("");
      setSelectedImage(null);
      setImageError(null);
      if (fileInputRef.current) fileInputRef.current.value = null;
    }
  };

  return (
    <div className="sticky bottom-0 bg-transparent flex justify-center" style={{ marginTop: '0' }}>
      <div className="w-full max-w-2xl px-4">
        <div className="bg-white relative rounded-2xl border border-gray-300 shadow-sm">
          {/* Image Preview Area */}
          {selectedImage && (
            <div className="flex items-center gap-2 ml-2 mt-2">
              <div className="relative group">
                <img
                  src={selectedImage}
                  alt="Preview"
                  className="w-20 h-20 object-cover rounded-md"
                />
                <button
                  onClick={handleRemoveImage}
                  className="absolute -top-1 -right-1 bg-white text-gray-600 hover:text-gray-800 rounded-full w-5 h-5 flex items-center justify-center border border-gray-300 text-xs font-bold hidden group-hover:block"
                  title="Remove image"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
          {/* Image Error Message */}
          {imageError && (
            <div className="p-2 text-red-500 text-sm bg-gray-100">
              {imageError}
            </div>
          )}
          
          {/* Claude-like interface with textarea above icons */}
          <div className="flex flex-col p-3">
            {/* Textarea First */}
            <div className="w-full mb-2">
              <textarea
                id="chat-input"
                className="block w-full min-h-10 py-2 resize-none focus:outline-none overflow-hidden rounded-md"
                ref={textareaRef}
                rows="1"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                aria-label="Chat input field"
                placeholder="Ask anything"
              />
            </div>
            
            {/* Icons Below */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                {/* Image Upload Button */}
                <label htmlFor="image-upload" className="cursor-pointer p-1 mr-2 hover:bg-gray-100 rounded-md">
                  <img src={uploadIcon} alt="Upload image" className="w-5 h-5" />
                </label>
                <input
                  type="file"
                  id="image-upload"
                  ref={fileInputRef}
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageUpload}
                />
              </div>
              
              {/* Send Button */}
              <button
                className="cursor-pointer p-1 rounded-md transition-all duration-150"
                onClick={handleSendClick}
                disabled={isLoading}
                aria-disabled={isLoading}
                title="Send message"
              >
                <img src={sendIcon} alt="Send message" className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatInput;