// frontend/src/components/chat/ChatConsoleApp.tsx
import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../../api/client';

interface Message {
  id: string;
  from: 'user' | 'ai';
  text: string;
  filename?: string;
  model?: string;
  timestamp: number;
}

interface ChatThread {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  lastUpdated: number;
}

const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
};

const cleanAIResponse = (text: string): string => {
  if (!text) return 'No response received.';
  let cleaned = text;
  cleaned = cleaned.replace(/<\|end\|>/g, '');
  cleaned = cleaned.replace(/<\|start\|>assistant<\|channel\|>final<\|message\|>/g, '');
  cleaned = cleaned.replace(/<\|start\|>assistant<\|channel\|>/g, '');
  cleaned = cleaned.replace(/<\|start\|>.*?<\|channel\|>/g, '');
  cleaned = cleaned.replace(/<\|.*?\|>/g, '');
  cleaned = cleaned.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '');
  cleaned = cleaned.replace(/<reasoning>[\s\S]*?<\/reasoning>/gi, '');
  cleaned = cleaned.replace(/```thinking[\s\S]*?```/gi, '');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  return cleaned || 'No response received.';
};

const ChatConsoleApp: React.FC<{ showToast: (msg: string) => void }> = ({ showToast }) => {
  const isMobile = useIsMobile();

  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string>('');
  const [input, setInput] = useState('');
  const [filename, setFilename] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = useState(true);
  const [isRefreshingResources, setIsRefreshingResources] = useState(false);

  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');

  const [cpuPercent, setCpuPercent] = useState(0);
  const [ramUsed, setRamUsed] = useState(0);
  const [ramTotal, setRamTotal] = useState(0);
  const [ramPercent, setRamPercent] = useState(0);
  const [gpuAvailable, setGpuAvailable] = useState(false);
  const [gpuPercent, setGpuPercent] = useState(0);
  const [gpuMessage, setGpuMessage] = useState('');
  const [swapUsed, setSwapUsed] = useState(0);
  const [swapTotal, setSwapTotal] = useState(0);
  const [swapPercent, setSwapPercent] = useState(0);
  const [protectedModelsWarning, setProtectedModelsWarning] = useState<string | null>(null);

  const chatLogContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const currentThread = threads.find(t => t.id === currentThreadId);
  const messages = currentThread?.messages || [];

  useEffect(() => {
    if (chatLogContainerRef.current) {
      chatLogContainerRef.current.scrollTop = chatLogContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (isMobile) setIsSidebarOpen(false);
  }, [isMobile]);

  useEffect(() => {
    loadThreadsFromBackend();
    fetchModels();
  }, []);

  useEffect(() => {
    const checkProtectedModels = async () => {
      try {
        const response = await apiClient.get('/api/system/protected-models');
        const missingModels = response.data.protected_models.filter((m: any) => !m.installed);
        
        if (missingModels.length > 0) {
          const warnings = missingModels.map((m: any) => m.warning).join('\n');
          setProtectedModelsWarning(warnings);
          showToast(warnings);
        }
      } catch (err) {
        console.error('Failed to check protected models:', err);
      }
    };
    
    checkProtectedModels();
  }, []);

  useEffect(() => {
    const fetchSystemResources = async () => {
      try {
        const res = await apiClient.get('/api/system/ram');
        setRamUsed(res.data.used || 0);
        setRamTotal(res.data.total || 0);
        setRamPercent(res.data.percent || 0);
        setSwapUsed(res.data.swap_used || 0);
        setSwapTotal(res.data.swap_total || 0);
        setSwapPercent(res.data.swap_percent || 0);
        
        const cpuRes = await apiClient.get('/api/system/cpu');
        setCpuPercent(cpuRes.data.percent || 0);

        // GPU Fetch integrated here
        const gpuRes = await apiClient.get('/api/system/gpu');
        if (gpuRes.data.available) {
          setGpuAvailable(true);
          setGpuPercent(gpuRes.data.utilization_percent || 0);
          setGpuMessage(gpuRes.data.message || `${gpuRes.data.memory_used_mb} / ${gpuRes.data.memory_total_mb} MB`);
        } else {
          setGpuAvailable(false);
        }
      } catch (err) {
        console.error('Failed to fetch system resources:', err);
      }
    };

    fetchSystemResources();
    const interval = setInterval(fetchSystemResources, 30000);
    return () => clearInterval(interval);
  }, []);

  const refreshSystemResources = async () => {
    if (isRefreshingResources) return;
    setIsRefreshingResources(true);
    try {
      const ramResponse = await apiClient.get('/api/system/ram');
      const cpuResponse = await apiClient.get('/api/system/cpu');
      const gpuResponse = await apiClient.get('/api/system/gpu');

      setRamUsed(Number(ramResponse.data.used) || 0);
      setRamTotal(Number(ramResponse.data.total) || 0);
      setRamPercent(Number(ramResponse.data.percent) || 0);
      setSwapUsed(Number(ramResponse.data.swap_used) || 0);
      setSwapTotal(Number(ramResponse.data.swap_total) || 0);
      setSwapPercent(Number(ramResponse.data.swap_percent) || 0);
      setCpuPercent(Number(cpuResponse.data.percent) || 0);

      if (gpuResponse.data.available) {
        setGpuAvailable(true);
        setGpuPercent(gpuResponse.data.utilization_percent || 0);
        setGpuMessage(gpuResponse.data.message || `${gpuResponse.data.memory_used_mb} / ${gpuResponse.data.memory_total_mb} MB`);
      } else {
        setGpuAvailable(false);
      }

      showToast('System resources updated');
    } catch (err: any) {
      console.error('Failed to refresh system resources:', err);
      showToast(`Failed to refresh: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsRefreshingResources(false);
    }
  };

  const formatSize = (mb: number): string => {
    if (mb < 1024) return `${mb} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const fetchModels = async () => {
    try {
      const response = await apiClient.get('/api/ollama/models');
      if (response.data.models && response.data.models.length > 0) {
        const embeddingPatterns = ['embed', 'nomic-embed', 'mxbai-embed', 'all-minilm', 'bge-', 'e5-'];
        const chatModels = response.data.models.filter((model: string) =>
          !embeddingPatterns.some(p => model.toLowerCase().includes(p))
        );

        setAvailableModels(chatModels);

        const savedCurrent = localStorage.getItem('mai-rag-current-model');
        const savedDefault = localStorage.getItem('mai-rag-default-model');

        if (savedCurrent && chatModels.includes(savedCurrent)) {
          setSelectedModel(savedCurrent);
        } else if (savedDefault && chatModels.includes(savedDefault)) {
          setSelectedModel(savedDefault);
        } else if (chatModels.length > 0) {
          setSelectedModel(chatModels[0]);
          localStorage.setItem('mai-rag-current-model', chatModels[0]);
        }
      }
    } catch (err) {
      console.error('Could not fetch Ollama models:', err);
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    const makeDefault = window.confirm(`Set "${newModel}" as your default model?`);
    setSelectedModel(newModel);
    localStorage.setItem('mai-rag-current-model', newModel);
    if (makeDefault) {
      localStorage.setItem('mai-rag-default-model', newModel);
      apiClient
        .post('/api/settings/default-model', { model: newModel })
        .then(() => showToast('Default model updated'))
        .catch(() => showToast('Failed to save default model'));
    }
  };

  const loadThreadsFromBackend = async () => {
    setIsLoadingThreads(true);
    try {
      const threadsRes = await apiClient.get('/api/memory/sqlite/chat/threads');
      const threadsData = threadsRes.data.threads || [];


      if (threadsData.length === 0) {
        await createNewThread();
        setIsLoadingThreads(false);
        return;
      }

      const threadsWithMessages = await Promise.all(
        threadsData.map(async (thread: any) => {
          try {
            const messagesRes = await apiClient.get(`/api/memory/sqlite/chat/messages/${thread.id}`);
            const msgs = messagesRes.data.messages || [];
          
            const mappedMessages = msgs.map((msg: any) => {
              let parsedTimestamp = Date.now();
              
              if (msg.timestamp && msg.timestamp > 0) {
                const ts = new Date(msg.timestamp).getTime();
                if (!isNaN(ts) && ts > 0) {
                  parsedTimestamp = ts;
                }
              }

              return {
                id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                from: msg.from === 'user' || msg.role === 'user' ? 'user' : 'ai',
                text: msg.text || msg.content || '',
                filename: msg.filename || undefined,
                model: msg.model && msg.model !== 'default' && msg.model !== 'unknown'
                  ? msg.model
                  : localStorage.getItem('mai-rag-current-model') || selectedModel,
                timestamp: parsedTimestamp, 
              };
            });

            return {
              id: thread.id,
              title: thread.title,
              messages: mappedMessages,
              createdAt: new Date(thread.created_at).getTime(),
              lastUpdated: new Date(thread.last_message_at || thread.created_at).getTime(),
            };

          } catch (err) {
            console.error(`[CHAT] Failed to load messages for thread ${thread.id}:`, err);
            return {
              id: thread.id,
              title: thread.title,
              messages: [],
              createdAt: new Date(thread.created_at).getTime(),
              lastUpdated: new Date(thread.last_message_at || thread.created_at).getTime(),
            };
          }
        })
      );

      setThreads(threadsWithMessages);
      
      const firstThread = threadsWithMessages[0];
      if (firstThread) {
        setCurrentThreadId(firstThread.id);
      }
    } catch (err) {
      console.error('[CHAT] Failed to load threads from backend:', err);
      showToast('Failed to load chat history from database');
      if (threads.length === 0) {
        await createNewThread();
      }
    } finally {
      setIsLoadingThreads(false);
    }
  };

  const createNewThread = async () => {
    const newThreadId = Date.now().toString();
    const newThread: ChatThread = {
      id: newThreadId,
      title: 'New Chat',
      messages: [{ 
        id: 'welcome-' + Date.now(), 
        from: 'ai', 
        text: 'System online. Select a model and ask me to create a file, or just chat.', 
        model: 'system', 
        timestamp: Date.now() 
      }],
      createdAt: Date.now(),
      lastUpdated: Date.now()
    };
  
    try {
      await apiClient.post('/api/memory/sqlite/chat/thread', { id: newThreadId, title: 'New Chat' });
    } catch (err) {
      console.error('Failed to create thread in database:', err);
    }
  
    setThreads(prev => [newThread, ...prev]);
    setCurrentThreadId(newThreadId);
    setIsSidebarOpen(false);
    showToast('New chat started');
  };

  const deleteThread = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this chat thread?')) return;

    try {
      // DEBUG: Check exactly what is in localStorage right now
      const debugKey = localStorage.getItem('mai-rag-api-key');

      await apiClient.delete(`/api/memory/sqlite/chat/thread/${id}`);

      setThreads(prev => prev.filter(t => t.id !== id));

      if (currentThreadId === id) {
        const remaining = threads.filter(t => t.id !== id);
        setCurrentThreadId(remaining.length > 0 ? remaining[0].id : '');
        if (remaining.length === 0) createNewThread();
      }
      showToast('Thread deleted permanently');
    } catch (err: any) {
      console.error('Thread deletion failed:', err);
      showToast(`Failed to delete: ${err.response?.data?.detail || err.message}`);
      loadThreadsFromBackend();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;
      audioChunksRef.current = [];

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = scriptProcessor;

      scriptProcessor.onaudioprocess = event => {
        const inputData = event.inputBuffer.getChannelData(0);
        const chunk = new Float32Array(inputData.length);
        chunk.set(inputData);
        audioChunksRef.current.push(chunk);
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);
      setIsRecording(true);
      showToast('Recording started - speak clearly');
    } catch (err) {
      console.error('Failed to start recording:', err);
      showToast('Microphone access denied');
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;

    try {
      if (scriptProcessorRef.current) {
        scriptProcessorRef.current.disconnect();
        scriptProcessorRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (audioContextRef.current) {
        await audioContextRef.current.close();
        audioContextRef.current = null;
      }

      setIsRecording(false);
      showToast('Processing audio...');

      const totalLength = audioChunksRef.current.reduce((acc, chunk) => acc + chunk.length, 0);
      const audioData = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of audioChunksRef.current) {
        audioData.set(chunk, offset);
        offset += chunk.length;
      }

      const pcmData = new Int16Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        const s = Math.max(-1, Math.min(1, audioData[i]));
        pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      const wavBuffer = new ArrayBuffer(44 + pcmData.length * 2);
      const view = new DataView(wavBuffer);
      const writeString = (offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
      };

      writeString(0, 'RIFF');
      view.setUint32(4, 36 + pcmData.length * 2, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, 1, true);
      view.setUint32(24, 16000, true);
      view.setUint32(28, 32000, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeString(36, 'data');
      view.setUint32(40, pcmData.length * 2, true);

      const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });

      try {
        const formData = new FormData();
        formData.append('file', wavBlob, 'recording.wav');
        const response = await apiClient.post('/api/voice/transcribe', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000,
        });
        const text = response.data.text;
        if (text) {
          setInput(prev => prev + (prev ? ' ' : '') + text);
          showToast('Transcription complete');
        } else {
          showToast('No speech detected');
        }
      } catch (err: any) {
        console.error('Transcription failed:', err);
        showToast('Transcription failed: ' + (err.response?.data?.detail || err.message));
      }
    } catch (err) {
      console.error('Error stopping recording:', err);
      showToast('Recording error');
    }
  };

  const sanitizeFilename = (filename: string): string => {
    let sanitized = filename.replace(/[^\w\-_\.]/g, '-');
    sanitized = sanitized.replace(/-+/g, '-').replace(/^-+|-+$/g, '');
    return sanitized;
  };

  const extractFilename = (query: string): string | null => {
    const lower = query.toLowerCase();
    if (lower.includes('[file]') || lower.includes('[file]:')) {
      const match = query.match(/\[FILE\]:?\s*(.+?\.(?:txt|md|py|js|ts|json|yaml|yml|toml|html|css|sql|sh|csv|xml|ini|cfg|log))/i);
      if (match?.[1]) return sanitizeFilename(match[1].trim());
    }
    const createFileMatch = query.match(/create\s+(?:a\s+)?(?:file|document|script)\s+(?:called\s+|named\s+)?["']?([^"'\n]+?\.(?:txt|md|py|js|ts|json|yaml|yml|toml|html|css|sql|sh|csv|xml|ini|cfg|log))["']?/i);
    if (createFileMatch?.[1]) return sanitizeFilename(createFileMatch[1].trim());
    const saveMatch = query.match(/(?:save|write)\s+(?:this|the|that|it)?\s*(?:to|as)\s+(?:file\s+)?["']?([^"'\n]+?\.(?:txt|md|py|js|ts|json|yaml|yml|toml|html|css|sql|sh|csv|xml|ini|cfg|log))["']?/i);
    if (saveMatch?.[1]) return sanitizeFilename(saveMatch[1].trim());
    const generateMatch = query.match(/(?:generate|make|produce)\s+(?:a\s+)?(?:file\s+)?["']?([^"'\n]+?\.(?:txt|md|py|js|ts|json|yaml|yml|toml|html|css|sql|sh|csv|xml|ini|cfg|log))["']?/i);
    if (generateMatch?.[1]) return sanitizeFilename(generateMatch[1].trim());
    return null;
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) {
      console.warn('[CHAT] Send blocked:', { input: input.trim(), isLoading });
      return;
    }
  
    if (!currentThreadId) {
      console.error('[CHAT] No current thread ID!');
      showToast('Error: No active chat thread');
      return;
    }

    abortControllerRef.current = new AbortController();
    const extractedFilename = extractFilename(input);

    const userMsg: Message = {
      id: Date.now().toString(),
      from: 'user',
      text: input,
      filename: extractedFilename || undefined,
      model: selectedModel,
      timestamp: Date.now(),
    };


   // Update local state
    setThreads(prev => {
      const updated = prev.map(t =>
        t.id === currentThreadId
          ? {
              ...t,
              messages: [...t.messages, userMsg],
              lastUpdated: Date.now(),
              title: t.messages.length === 0 ? input.slice(0, 30) : t.title,
            }
          : t
      );
      return updated;
    });

    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      // =================================================================
      // SAVE THREAD AND USER MESSAGE TO DATABASE
      // =================================================================
      try {
        await apiClient.post('/api/memory/sqlite/chat/thread', {
          id: currentThreadId,
          title: currentThread?.title || 'New Chat',
        });
      
        await apiClient.post('/api/memory/sqlite/chat/message', {
          thread_id: currentThreadId,
          role: 'user',
          content: currentInput,
          model: selectedModel,
          timestamp: userMsg.timestamp,
        });
      } catch (saveErr: any) {
        console.error('[CHAT] Failed to save user message:', saveErr);
        showToast('Failed to save message to database');
      }

      // =================================================================
      // SEND TO LLM
      // =================================================================
      const payload = extractedFilename
        ? { query: currentInput, filename: extractedFilename, model: selectedModel }
        : { query: currentInput, model: selectedModel };


      const response = await apiClient.post('/api/chat', payload, {
        signal: abortControllerRef.current.signal,
        timeout: 3600000,
      });


      const content =
        response.data?.content ||
        response.data?.message ||
        response.data?.response ||
        response.data?.text ||
        (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        from: 'ai',
        text: cleanAIResponse(content),
        model: response.data?.model || selectedModel,
        timestamp: Date.now(),
      };


      // Update local state with AI response
      setThreads(prev => {
        const updated = prev.map(t =>
          t.id === currentThreadId 
            ? { ...t, messages: [...t.messages, aiMsg], lastUpdated: Date.now() } 
            : t
        );
        return updated;
      });

      // =================================================================
      // SAVE AI MESSAGE TO DATABASE
      // =================================================================
      try {
        await apiClient.post('/api/memory/sqlite/chat/message', {
          thread_id: currentThreadId,
          role: 'assistant',
          content: aiMsg.text,
          model: aiMsg.model,
          timestamp: aiMsg.timestamp,
        });
      } catch (saveErr: any) {
        console.error('[CHAT] Failed to save AI message:', saveErr);
        showToast('Failed to save AI response to database');
      }

      if (filename) setFilename('');

    } catch (error: any) {
      console.error('[CHAT] Request failed:', error);
      if (error.name !== 'AbortError' && error.code !== 'ERR_CANCELED') {
        const errorMsg = error.response?.data?.detail || error.message || 'Connection error';
      
        const errorMsgObj: Message = {
          id: (Date.now() + 1).toString(),
          from: 'ai',
          text: `Error: ${errorMsg}`,
          model: selectedModel,
          timestamp: Date.now(),
        };
      
        setThreads(prev =>
          prev.map(t =>
            t.id === currentThreadId
              ? { ...t, messages: [...t.messages, errorMsgObj], lastUpdated: Date.now() }
              : t
          )
        );
        showToast('Request failed');
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      if (textareaRef.current) textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const abortRequest = () => {
    try {
      if (abortControllerRef.current) abortControllerRef.current.abort();
    } catch (err) {
      console.warn('Abort error:', err);
    } finally {
      abortControllerRef.current = null;
      setIsLoading(false);
      showToast('Request stopped');
      if (textareaRef.current) textareaRef.current.focus();
    }
  };

  return (
    <div
      className="console reveal delay-2 glow-panel"
      role="region"
      aria-label="Assistant console"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: isMobile ? 'calc(100vh - 180px)' : '700px',
        minHeight: isMobile ? '500px' : '540px',
        overflow: 'hidden',
      }}
    >
      <div style={{ width: '100%', padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'rgba(0,0,0,0.15)', flexShrink: 0 }}>
        <h2 className="console-title" style={{ margin: 0, color: 'var(--accent)', fontSize: '1.4rem', fontWeight: 'bold', letterSpacing: '-0.02em' }}>
          Assistant Chat Console
        </h2>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0, height: '100%' }}>
        {isSidebarOpen && (
          <>
            {isMobile && (
              <div
                onClick={() => setIsSidebarOpen(false)}
                style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 998 }}
                aria-hidden="true"
              />
            )}

            <div
              style={{
                width: isMobile ? '85%' : '250px',
                maxWidth: isMobile ? '300px' : '250px',
                borderRight: '1px solid var(--line)',
                display: 'flex',
                flexDirection: 'column',
                background: 'rgba(0,0,0,0.2)',
                height: '100%',
                position: isMobile ? 'fixed' : 'relative',
                left: 0,
                top: 0,
                bottom: 0,
                zIndex: isMobile ? 999 : 'auto',
                boxShadow: isMobile ? '4px 0 20px rgba(0,0,0,0.5)' : 'none',
                flexShrink: 0,
              }}
              role="navigation"
              aria-label="Chat threads sidebar"
            >
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: '40px', flexShrink: 0 }}>
                <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>
                  Threads
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {isMobile && (
                    <button onClick={() => setIsSidebarOpen(false)} aria-label="Close sidebar" title="Close sidebar" style={{ background: 'none', border: 'none', color: 'var(--text)', cursor: 'pointer', fontSize: '1.5rem', padding: '4px 8px', lineHeight: 1 }}>
                      ×
                    </button>
                  )}
                  <button onClick={createNewThread} title="New Chat" className="chip" aria-label="Create new chat thread" style={{ padding: '6px 14px', background: 'none', border: '1px solid var(--accent)', color: 'var(--accent)', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1, borderRadius: '8px', height: '28px', display: 'flex', alignItems: 'center' }}>
                    +
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: '8px', minHeight: 0 }} role="list" aria-label="Chat threads list">
                {isLoadingThreads ? (
                  <div style={{ padding: '20px', textAlign: 'center', opacity: 0.7 }} role="status" aria-live="polite">
                    Loading threads...
                  </div>
                ) : (
                  (threads || []).map(thread => (
                    <div
                      key={thread.id}
                      onClick={() => {
                        setCurrentThreadId(thread.id);
                        if (isMobile) setIsSidebarOpen(false);
                      }}
                      onKeyDown={e => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setCurrentThreadId(thread.id);
                          if (isMobile) setIsSidebarOpen(false);
                        }
                      }}
                      role="listitem"
                      aria-label={`${thread.title}, ${thread.messages.length} messages`}
                      aria-selected={thread.id === currentThreadId}
                      tabIndex={0}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        marginBottom: '4px',
                        cursor: 'pointer',
                        background: thread.id === currentThreadId ? 'rgba(255,255,255,0.1)' : 'transparent',
                        border: thread.id === currentThreadId ? '1px solid var(--accent)' : '1px solid transparent',
                        fontSize: '0.9rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        userSelect: 'none',
                      }}
                    >
                      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: isMobile ? '180px' : '160px' }}>
                        {thread.title}
                      </span>
                      <button
                        onClick={e => deleteThread(thread.id, e)}
                        title="Delete thread"
                        className="chip"
                        aria-label={`Delete thread ${thread.title}`}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', opacity: 0.7, fontSize: '1.2rem', padding: '2px 8px', borderRadius: '6px', flexShrink: 0 }}
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>

              {!isMobile && (
                <div style={{ borderTop: '1px solid var(--line)', padding: '14px', background: 'rgba(255,255,255,0.02)', flexShrink: 0 }} role="region" aria-label="System resources">
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>System Resources</span>
                    <button
                      onClick={refreshSystemResources}
                      disabled={isRefreshingResources}
                      aria-label="Refresh system resources"
                      title="Refresh system resources"
                      style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        border: '1px solid var(--line)',
                        background: isRefreshingResources ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)',
                        color: isRefreshingResources ? '#666' : 'var(--text)',
                        cursor: isRefreshingResources ? 'not-allowed' : 'pointer',
                        fontSize: '0.75rem',
                        opacity: isRefreshingResources ? 0.5 : 1,
                        transition: 'all 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minWidth: '24px',
                        height: '24px',
                      }}
                    >
                      {isRefreshingResources ? (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 1s linear infinite' }}>
                          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="24 8" />
                        </svg>
                      ) : (
                        '↻'
                      )}
                    </button>
                  </div>

                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>CPU</span>
                      <span style={{ opacity: 0.7 }}>{cpuPercent}%</span>
                    </div>
                    <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }} role="progressbar" aria-valuenow={cpuPercent} aria-valuemin={0} aria-valuemax={100} aria-label="CPU usage">
                      <div style={{ height: '100%', width: `${cpuPercent}%`, background: cpuPercent > 80 ? '#ef4444' : cpuPercent > 60 ? '#f59e0b' : '#10b981', transition: 'width 0.3s' }} />
                    </div>
                  </div>

                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>RAM</span>
                      <span style={{ opacity: 0.7 }}>
                        {formatSize(ramUsed)} / {formatSize(ramTotal)}
                      </span>
                    </div>
                    <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }} role="progressbar" aria-valuenow={ramPercent} aria-valuemin={0} aria-valuemax={100} aria-label="RAM usage">
                      <div style={{ height: '100%', width: `${ramPercent}%`, background: ramPercent > 80 ? '#ef4444' : ramPercent > 60 ? '#f59e0b' : 'var(--accent)', transition: 'width 0.3s' }} />
                    </div>
                  </div>

                  {gpuAvailable && (
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                        <span>GPU ({gpuMessage.includes('MB') ? 'VRAM' : 'Usage'})</span>
                        <span style={{ opacity: 0.7 }}>{gpuMessage}</span>
                      </div>
                      <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }} role="progressbar" aria-valuenow={gpuPercent} aria-valuemin={0} aria-valuemax={100} aria-label="GPU usage">
                        <div style={{ height: '100%', width: `${gpuPercent}%`, background: gpuPercent > 80 ? '#ef4444' : gpuPercent > 60 ? '#f59e0b' : '#8b5cf6', transition: 'width 0.3s' }} />
                      </div>
                    </div>
                  )}

                  <div>
                    <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Swap</span>
                      <span style={{ opacity: 0.7 }}>
                        {formatSize(swapUsed)} / {formatSize(swapTotal)}
                      </span>
                    </div>
                    <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }} role="progressbar" aria-valuenow={swapPercent} aria-valuemin={0} aria-valuemax={100} aria-label="Swap usage">
                      <div style={{ height: '100%', width: `${swapPercent}%`, background: swapPercent > 80 ? '#ef4444' : swapPercent > 60 ? '#f59e0b' : '#8b5cf6', transition: 'width 0.3s' }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            position: 'relative',
            minWidth: 0,
            overflow: 'hidden',
            minHeight: 0,
            height: '100%',
          }}
          role="region"
          aria-label="Chat interface"
        >
          <div style={{ padding: isMobile ? '6px 10px' : '8px 16px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: isMobile ? '6px' : '12px', flexWrap: 'wrap', minHeight: '40px', flexShrink: 0 }} role="toolbar" aria-label="Chat controls">
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="chip" aria-label={isSidebarOpen ? 'Hide threads' : 'Show threads'} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: '8px', padding: isMobile ? '4px 10px' : '6px 12px', cursor: 'pointer', fontSize: isMobile ? '0.75rem' : '0.85rem', fontWeight: 500, height: '28px', display: 'flex', alignItems: 'center' }}>
              {isMobile ? '☰' : isSidebarOpen ? 'Hide' : 'Show'} {isMobile ? '' : 'Threads'}
            </button>

            <select value={selectedModel} onChange={handleModelChange} disabled={isLoading || availableModels.length === 0} className="chip" aria-label="Select AI model" style={{ padding: isMobile ? '4px 8px' : '6px 12px', borderRadius: '8px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: isMobile ? '0.8rem' : '0.9rem', cursor: isLoading ? 'not-allowed' : 'pointer', outline: 'none', minWidth: isMobile ? '120px' : '180px', height: '28px', flex: isMobile ? 1 : 'none' }}>
              {availableModels.length > 0 ? availableModels.map(model => <option key={model} value={model}>{model}</option>) : <option value="" disabled>Loading models...</option>}
            </select>

            {protectedModelsWarning && (
              <div style={{ 
                fontSize: '0.75rem', 
                color: '#f59e0b', 
                marginTop: '4px', 
                padding: '6px 10px',
                background: 'rgba(245, 158, 11, 0.1)',
                borderRadius: '6px',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                whiteSpace: 'pre-line'
              }}>
                {protectedModelsWarning}
              </div>
            )}

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', fontSize: isMobile ? '0.75rem' : '0.85rem', fontWeight: 500 }} role="status" aria-live="polite">
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: isLoading ? '#f59e0b' : '#22c55e', display: 'inline-block', animation: isLoading ? 'none' : 'pulse 2s infinite', boxShadow: isLoading ? 'none' : '0 0 8px rgba(34, 197, 94, 0.6)' }} aria-hidden="true" />
              <span style={{ color: isLoading ? '#f59e0b' : 'var(--accent)' }}>{isLoading ? 'Processing' : 'Ready'}</span>
            </div>
          </div>

          <div ref={chatLogContainerRef} style={{ flex: 1, overflowY: 'auto', padding: isMobile ? '10px' : '16px', minHeight: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {messages.length === 0 && !isLoading && (
              <div style={{ textAlign: 'center', opacity: 0.5, marginTop: '40px' }}>
                No messages yet. Start a conversation!
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id} style={{ display: 'flex', justifyContent: msg.from === 'user' ? 'flex-end' : 'flex-start', width: '100%' }}>
                <div style={{ maxWidth: '75%', padding: '10px 14px', borderRadius: '12px', background: msg.from === 'user' ? 'var(--accent)' : 'rgba(255,255,255,0.08)', color: msg.from === 'user' ? '#000' : 'var(--text)', wordBreak: 'break-word', lineHeight: 1.5, position: 'relative' }}>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                  <div style={{ fontSize: '0.65rem', opacity: 0.6, marginTop: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {msg.from === 'ai' && msg.model && msg.model !== 'system' && (
                        <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', opacity: 0.8, background: 'rgba(255,255,255,0.06)', padding: '1px 6px', borderRadius: '4px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {msg.model}
                        </span>
                      )}
                      {/* Copy Button */}
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(msg.text).then(() => {
                            showToast('Copied to clipboard');
                          }).catch(err => {
                            console.error('Failed to copy:', err);
                            showToast('Failed to copy');
                          });
                        }}
                        title="Copy message"
                        aria-label="Copy message to clipboard"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: msg.from === 'user' ? '#000' : 'var(--text)',
                          cursor: 'pointer',
                          padding: '2px 4px',
                          borderRadius: '4px',
                          opacity: 0.6,
                          transition: 'opacity 0.2s',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.6'; }}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '8px 14px', color: 'var(--accent)', fontSize: '0.85rem', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1.5s infinite' }} />
                LLM is thinking...
              </div>
            )}
          </div>

          <div style={{ padding: isMobile ? '8px 10px' : '10px 16px', borderTop: '1px solid var(--line)', background: 'rgba(0,0,0,0.1)', flexShrink: 0, zIndex: 10 }}>
            {!isMobile && (
              <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'nowrap' }} role="group" aria-label="File attachment">
                <label htmlFor="fileUpload" className="chip" style={{ fontSize: '0.8rem', color: 'var(--text)', cursor: 'pointer', padding: '4px 10px', borderRadius: '6px', border: '1px dashed var(--line)', background: 'rgba(255,255,255,0.02)', height: '26px', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
                  Attach file
                </label>
                <input
                  id="fileUpload"
                  type="file"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setFilename(file.name);
                      showToast(`Selected: ${file.name}`);
                    }
                  }}
                  style={{ display: 'none' }}
                  aria-label="Upload file"
                />
                {filename && (
                  <span style={{ fontSize: '0.8rem', opacity: 0.9, display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.08)', border: '1px solid var(--line)', height: '26px', maxWidth: '300px' }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{filename}</span>
                    <button onClick={() => setFilename('')} aria-label="Remove file" title="Remove file" style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0', fontSize: '1rem', lineHeight: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px' }}>
                      ×
                    </button>
                  </span>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: isMobile ? '6px' : '10px', alignItems: 'flex-end' }} role="group" aria-label="Message input">
              <textarea
                ref={textareaRef}
                placeholder={filename ? 'Describe file content...' : 'Ask MAi-RAG-PA...'}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={isMobile ? 2 : 4}
                disabled={isLoading}
                aria-label="Type your message"
                style={{
                  flex: 1,
                  minHeight: isMobile ? '60px' : '110px',
                  maxHeight: isMobile ? '100px' : '155px',
                  padding: isMobile ? '8px 10px' : '12px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--line)',
                  background: 'rgba(255,255,255,0.04)',
                  color: 'var(--text)',
                  fontSize: isMobile ? '0.9rem' : '1rem',
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'inherit',
                  lineHeight: 1.5,
                }}
              />

              <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? '4px' : '6px', alignItems: 'center', flexShrink: 0 }}>
                <button
                  onClick={isLoading ? abortRequest : sendMessage}
                  disabled={!isLoading && !input.trim()}
                  className="btn"
                  aria-label={isLoading ? 'Stop generation' : 'Send message'}
                  style={{
                    width: isMobile ? 44 : 52,
                    height: isMobile ? 44 : 52,
                    borderRadius: '10px',
                    border: 'none',
                    background: isLoading ? '#ef4444' : !input.trim() ? 'rgba(255,255,255,0.1)' : 'var(--accent, #7cf6d3)',
                    color: !isLoading && !input.trim() ? '#666' : '#fff',
                    cursor: !isLoading && !input.trim() ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '1.1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  {isLoading ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <rect x="6" y="6" width="12" height="12" rx="2" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                  )}
                </button>

                <button
                  aria-label={isRecording ? 'Stop recording' : 'Record voice'}
                  title={isRecording ? 'Stop recording' : 'Voice input'}
                  onClick={isRecording ? stopRecording : startRecording}
                  className="chip"
                  style={{
                    width: isMobile ? 44 : 52,
                    height: isMobile ? 44 : 52,
                    borderRadius: '10px',
                    border: isRecording ? '2px solid #ef4444' : '1px solid var(--line)',
                    background: isRecording ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.04)',
                    color: isRecording ? '#ef4444' : 'var(--text)',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    fontSize: '1rem',
                    animation: isRecording ? 'pulse 1s infinite' : 'none',
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ strokeWidth: 2 }}>
                    <rect x="9" y="3" width="6" height="12" rx="3" stroke="currentColor" />
                    <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8.5 21h7" stroke="currentColor" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 8px rgba(34, 197, 94, 0.6); }
          50% { opacity: 0.7; transform: scale(0.95); box-shadow: 0 0 12px rgba(34, 197, 94, 0.9); }
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .file-indicator {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 6px;
          background: rgba(124, 246, 211, 0.15);
          border: 1px solid rgba(124, 246, 211, 0.3);
          color: var(--accent);
          font-size: 0.85rem;
          margin-left: 8px;
        }
      `}</style>
    </div>
  );
};

export default ChatConsoleApp;
