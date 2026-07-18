// frontend/src/hooks/useChat.ts
import { useState } from 'react';
import apiClient from '../api/client';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isCode?: boolean;
  filename?: string;
  model?: string;
}

interface ChatResponse {
  content: string;
  model: string;
  warning?: string;
}

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (text: string, filename?: string, model?: string) => {
    setIsLoading(true);
    const userMsg: Message = { role: 'user', content: text, filename };
    setMessages((prev) => [...prev, userMsg]);

    try {
      // Single endpoint handles both chat and file creation
      const response = await apiClient.post<ChatResponse>('/api/chat', {
        query: text,
        filename: filename || undefined,
        model: model || undefined,
      });

      const assistantMsg: Message = {
        role: 'assistant',
        content: response.data.content,
        model: response.data.model,
      };

      // Add warning if present (e.g., repetition loop detected)
      if (response.data.warning) {
        assistantMsg.content += `\n\n**Warning:** ${response.data.warning}`;
      }

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      console.error('Chat error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Unknown error';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `**Error:** ${errorMsg}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return { messages, sendMessage, clearMessages, isLoading };
};
