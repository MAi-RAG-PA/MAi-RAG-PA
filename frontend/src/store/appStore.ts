// frontend/src/store/appStore.ts

import { create } from 'zustand';

// Type definitions
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

interface Settings {
  currentModel: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
  theme: string;
}

interface AppState {
  // State
  currentModel: string;
  conversations: Conversation[];
  currentConversationId: string | null;
  settings: Settings;
  isLoading: boolean;
  error: string | null;

  // Model actions
  setModel: (model: string) => void;

  // Conversation actions
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;
  addMessage: (conversationId: string, message: Message) => void;

  // Settings actions
  updateSettings: (updates: Partial<Settings>) => void;
  resetSettings: () => void;

  // UI state actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

// Default settings
const defaultSettings: Settings = {
  currentModel: 'qwen2.5-coder:7b',
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt: '',
  theme: 'deep-space-teal'
};

// Create the store
export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  currentModel: 'qwen2.5-coder:7b',
  conversations: [],
  currentConversationId: null,
  settings: defaultSettings,
  isLoading: false,
  error: null,

  // Model actions
  setModel: (model) => set({
    currentModel: model,
    settings: { ...get().settings, currentModel: model }
  }),

  // Conversation actions
  addConversation: (conversation) => set((state) => ({
    conversations: [...state.conversations, conversation],
    currentConversationId: conversation.id
  })),

  updateConversation: (id, updates) => set((state) => ({
    conversations: state.conversations.map(conv =>
      conv.id === id ? { ...conv, ...updates, updatedAt: new Date().toISOString() } : conv
    )
  })),

  deleteConversation: (id) => set((state) => {
    const newState = {
      conversations: state.conversations.filter(conv => conv.id !== id)
    };

    // If we deleted the current conversation, clear the selection
    if (state.currentConversationId === id) {
      newState.currentConversationId = null;
    }

    return newState;
  }),

  setCurrentConversation: (id) => set({ currentConversationId: id }),

  addMessage: (conversationId, message) => set((state) => ({
    conversations: state.conversations.map(conv =>
      conv.id === conversationId
        ? {
            ...conv,
            messages: [...conv.messages, message],
            updatedAt: new Date().toISOString()
          }
        : conv
    )
  })),

  // Settings actions
  updateSettings: (updates) => set((state) => ({
    settings: { ...state.settings, ...updates }
  })),

  resetSettings: () => set({ settings: defaultSettings }),

  // UI state actions
  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null })
}));

// Optional: Create a selector hook for better performance
export const useCurrentConversation = () => {
  const conversations = useAppStore((state) => state.conversations);
  const currentId = useAppStore((state) => state.currentConversationId);

  return conversations.find(conv => conv.id === currentId) || null;
};

export const useSettings = () => useAppStore((state) => state.settings);
export const useIsLoading = () => useAppStore((state) => state.isLoading);
export const useError = () => useAppStore((state) => state.error);
