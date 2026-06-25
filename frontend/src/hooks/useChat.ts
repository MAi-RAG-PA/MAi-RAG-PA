// src/hooks/useChat.ts
import { useState } from 'react';
import { sendChatMessage } from '../api/chat'; // Your existing chat API
import { sendAgentRequest, AgentResponse } from '../api/agent';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isCode?: boolean;
  filename?: string;
}

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (text: string, filename?: string) => {
    setIsLoading(true);
    const userMsg: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);

    try {
      let responseContent = "";
      
      // Simple heuristic: If a filename is provided or "code" is mentioned, use Agent
      if (filename || text.toLowerCase().includes("create") && text.toLowerCase().includes(".py")) {
        const agentRes: AgentResponse = await sendAgentRequest({ query: text, filename });
        responseContent = agentRes.message + "\n\n" + agentRes.content;
      } else {
        // Use existing standard chat
        const res = await sendChatMessage(text);
        responseContent = res.content; // Adjust based on your existing chat API response
      }

      const assistantMsg: Message = { 
        role: 'assistant', 
        content: responseContent,
        filename: filename
      };
      setMessages((prev) => [...prev, assistantMsg]);

    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [...prev, { role: 'assistant', content: "Error processing request." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return { messages, sendMessage, isLoading };
};
