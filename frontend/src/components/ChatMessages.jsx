import { useEffect, useRef, useMemo } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import userIcon from "../assets/images/user.svg";
import botIcon from "../assets/images/logo.svg";
import ProductTile from "./ProductTile";

function ChatMessages({ messages, isLoading }) {
  const messagesEndRef = useRef(null);

  // Smooth scrolling to the latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isLoading]);

  return (
    <div className="grow flex flex-col items-center space-y-4 px-4 overflow-y-auto w-full">
      {messages.map(({ role, content, products, type, has_image, image_data }, idx) => (
        <MessageBubble
          key={idx}
          role={role}
          content={content}
          products={products}
          type={type}
          hasImage={has_image}
          imageData={image_data}
        />
      ))}
      {isLoading && <TypingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  );
}

function MessageBubble({ role, content, products, type, hasImage, imageData }) {
  const isUser = role === "user";

  // Normalize content to string for Markdown
  const messageText =
    typeof content === "object" && content.botResponse
      ? content.botResponse
      : String(content || "");

  // Validate base64 image src
  const isValidImageSrc = (src) => {
    if (!src || typeof src !== "string") {
      console.log("Image src invalid: empty or non-string", { src });
      return false;
    }
    // Check if the src starts with "data:image/" and contains "base64,"
    const isValid = src.startsWith("data:image/") && src.includes("base64,");
    console.log("Image src validation:", { src: src.slice(0, 50) + "...", isValid, length: src.length });
    return isValid;
  };

  // Memoized Markdown components for rendering tables, lists, and images
  const markdownComponents = useMemo(() => ({
    table: ({ children }) => (
      <div className="border border-gray-400 rounded-md overflow-hidden mt-2">
        {children}
      </div>
    ),
    thead: () => null,
    tbody: ({ children }) => (
      <div className="divide-y divide-gray-300">{children}</div>
    ),
    tr: ({ children }) => (
      <div className="flex justify-between px-4 py-2 bg-gray-100 border-b border-gray-300">
        {children}
      </div>
    ),
    th: ({ children }) => (
      <span className="font-semibold text-gray-800">{children}:</span>
    ),
    td: ({ children }) => <span className="text-gray-700">{children}</span>,
    li: ({ children }) => (
      <div className="flex items-start gap-2">
        <span>•</span>
        {children}
      </div>
    ),
    img: ({ src, alt }) => {
      // Only render images embedded in Markdown content (not user-uploaded images)
      if (!isValidImageSrc(src)) {
        console.log("Skipping image render due to invalid src:", src);
        return <span className="text-gray-500 italic">Invalid image data</span>;
      }
      return (
        <img
          src={src}
          alt={alt || "Embedded image"}
          className="max-w-full h-auto rounded-md mt-2 shadow-sm"
          loading="lazy"
          onError={(e) => {
            console.error("Image failed to load:", { src: src.slice(0, 50) + "...", length: src.length });
            e.currentTarget.src = "/assets/images/fallback-image.png";
          }}
        />
      );
    },
  }), []);

  return (
    <div className="w-full flex justify-center">
      <div
        className={`flex items-start gap-3 max-w-2xl w-full ${
          isUser ? "justify-end" : "justify-start"
        }`}
      >
        {!isUser && (
          <img
            className="h-8 w-8 self-start"
            src={botIcon}
            alt="Bot avatar"
            loading="lazy"
          />
        )}

        <div className={`py-3 px-4 rounded-xl shadow-md max-w-[90%] ${isUser ? "bg-gray-200" : "bg-gray-300"}`}>
          {messageText ? (
            <>
              {/* Render the text content using Markdown */}
              <Markdown
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
                className="whitespace-pre-wrap break-words"
              >
                {messageText}
              </Markdown>
              {/* Render user-uploaded image if present */}
              {hasImage && (
                <>
                  {imageData && isValidImageSrc(imageData) ? (
                    <img
                      src={imageData}
                      alt="Uploaded image"
                      className="max-w-full h-auto rounded-md mt-2 shadow-sm"
                      loading="lazy"
                      onError={(e) => {
                        console.error("Uploaded image failed to load:", { src: imageData.slice(0, 50) + "...", length: imageData.length });
                        e.currentTarget.src = "/assets/images/fallback-image.png";
                      }}
                    />
                  ) : (
                    <span className="text-gray-500 italic">
                     
                    </span>
                  )}
                </>
              )}
            </>
          ) : (
            <span className="text-gray-500 italic"></span>
          )}

          {/* Render ProductTile components */}
          {products?.length > 0 && (
            <div className="mt-4 space-y-4">
              {products.map((product, index) => (
                <ProductTile key={index} product={product} />
              ))}
            </div>
          )}
        </div>

        {isUser && (
          <img
            className="h-8 w-8 self-start"
            src={userIcon}
            alt="User avatar"
            loading="lazy"
          />
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex space-x-1">
      <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce"></span>
      <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce delay-150"></span>
      <span className="h-2 w-2 bg-gray-400 rounded-full animate-bounce delay-300"></span>
    </div>
  );
}

export default ChatMessages;