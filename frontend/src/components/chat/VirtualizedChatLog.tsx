// frontend/src/components/chat/VirtualizedChatLog.tsx
import React, { useRef, useEffect, useCallback, useMemo } from "react";
import { FixedSizeList as List, ListChildComponentProps } from "react-window";
import ChatMessage from "./ChatMessage";

interface Message {
  id: string;
  from: "user" | "ai";
  text: string;
  filename?: string;
  model?: string;
  timestamp: number;
}

interface VirtualizedChatLogProps {
  messages: Message[];
  isLoading: boolean;
  isMobile: boolean;
  height: number;
}

const MESSAGE_HEIGHT_DESKTOP = 120;
const MESSAGE_HEIGHT_MOBILE = 100;

const VirtualizedChatLog: React.FC<VirtualizedChatLogProps> = ({
  messages,
  isLoading,
  isMobile,
  height,
}) => {
  const listRef = useRef<List>(null);
  const itemSize = isMobile ? MESSAGE_HEIGHT_MOBILE : MESSAGE_HEIGHT_DESKTOP;

  const scrollToBottom = useCallback(() => {
    if (listRef.current && messages.length > 0) {
      listRef.current.scrollToItem(messages.length - 1, "end");
    }
  }, [messages.length]);

  useEffect(() => {
    scrollToBottom();
  }, [messages.length, isLoading, scrollToBottom]);

  const Row = useCallback(
    ({ index, style }: ListChildComponentProps) => {
      const msg = messages[index];

      return (
        <div style={{ ...style, paddingBottom: "8px" }}>
          <ChatMessage
            type={msg.from}
            text={msg.text}
            filename={msg.filename}
            model={msg.model !== "system" ? msg.model : undefined}
            timestamp={msg.timestamp}
          />
        </div>
      );
    },
    [messages]
  );

  const loadingIndicator = useMemo(
    () =>
      isLoading ? (
        <div
          role="status"
          aria-label="AI is generating response"
          style={{
            padding: "8px 16px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "var(--accent)",
            fontSize: "0.85rem",
          }}
        >
          <span aria-hidden="true">⟳</span>
          <span>AI is thinking...</span>
        </div>
      ) : null,
    [isLoading]
  );

  if (messages.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "var(--muted)",
          fontStyle: "italic",
        }}
        role="status"
        aria-live="polite"
      >
        No messages yet. Start a conversation below.
      </div>
    );
  }

  return (
    <div role="log" aria-label="Chat conversation" aria-live="polite" aria-atomic="false" style={{ height: "100%" }}>
      <List
        ref={listRef}
        height={height}
        itemCount={messages.length}
        itemSize={itemSize}
        width="100%"
        overscanCount={5}
      >
        {Row}
      </List>

      {loadingIndicator}
    </div>
  );
};

export default VirtualizedChatLog;
