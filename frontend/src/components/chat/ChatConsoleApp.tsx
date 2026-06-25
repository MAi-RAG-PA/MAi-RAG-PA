import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
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
  
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  
  const [cpuPercent, setCpuPercent] = useState(0);
  const [ramUsed, setRamUsed] = useState(0);
  const [ramTotal, setRamTotal] = useState(0);
  const [ramPercent, setRamPercent] = useState(0);
  const [swapUsed, setSwapUsed] = useState(0);
  const [swapTotal, setSwapTotal] = useState(0);
  const [swapPercent, setSwapPercent] = useState(0);
  
  const chatLogRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const currentThread = threads.find(t => t.id === currentThreadId);
  const messages = currentThread?.messages || [];

  // Auto-close sidebar on mobile
  useEffect(() => {
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  // 1. LOAD FROM DATABASE ON MOUNT
  useEffect(() => {
    loadThreadsFromBackend();
    fetchModels();
  }, []);

  // 2. SYSTEM RESOURCES
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
      } catch (err) {
        console.error('Failed to fetch system resources:', err);
      }
    };
    fetchSystemResources();
    const interval = setInterval(fetchSystemResources, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatSize = (mb: number): string => {
    if (mb < 1024) return `${mb} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const abortRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      showToast('Request stopped');
    }
  };

  const fetchModels = async () => {
    try {
      const response = await apiClient.get('/api/ollama/models');
      if (response.data.models && response.data.models.length > 0) {
        const embeddingModelPatterns = ['embed', 'nomic-embed', 'mxbai-embed', 'all-minilm', 'bge-', 'e5-'];
        const chatModels = response.data.models.filter((model: string) => {
          const modelName = model.toLowerCase();
          return !embeddingModelPatterns.some(pattern => modelName.includes(pattern));
        });
        setAvailableModels(chatModels);
        const savedDefault = localStorage.getItem('mai-rag-default-model');
        if (savedDefault && chatModels.includes(savedDefault)) {
          setSelectedModel(savedDefault);
        } else if (chatModels.length > 0) {
          setSelectedModel(chatModels[0]);
        }
      }
    } catch (err) {
      console.error("Could not fetch Ollama models:", err);
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    const makeDefault = window.confirm(`Set "${newModel}" as your default model?`);
    setSelectedModel(newModel);
    localStorage.setItem('mai-rag-current-model', newModel);
    if (makeDefault) {
      localStorage.setItem('mai-rag-default-model', newModel);
      apiClient.post('/api/settings/default-model', { model: newModel })
        .then(() => showToast(`Default model updated`))
        .catch(() => showToast('Failed to save default model'));
    }
  };

  // 3. ROBUST DATABASE LOADER
  const loadThreadsFromBackend = async () => {
    setIsLoadingThreads(true);
    try {
      console.log('Loading chat threads from SQLite database...');
      const threadsRes = await apiClient.get('/api/memory/sqlite/chat/threads');
      const threadsData = threadsRes.data.threads || [];
      console.log(`Found ${threadsData.length} threads in database`);
      
      if (threadsData.length === 0) {
        createNewThread();
        setIsLoadingThreads(false);
        return;
      }
      
      const threadsWithMessages = await Promise.all(
        threadsData.map(async (thread: any) => {
          try {
            const messagesRes = await apiClient.get(`/api/memory/sqlite/chat/messages/${thread.id}`);
            const msgs = messagesRes.data.messages || [];
            console.log(`  Thread "${thread.title}": ${msgs.length} messages`);
            
            return {
              id: thread.id,
              title: thread.title,
              messages: msgs.map((msg: any) => ({
                id: msg.id,
                from: msg.from,
                text: msg.text,
                timestamp: msg.timestamp || Date.now()
              })),
              createdAt: new Date(thread.created_at).getTime(),
              lastUpdated: new Date(thread.last_message_at || thread.created_at).getTime()
            };
          } catch (err) {
            console.error(`Failed to load messages for thread ${thread.id}:`, err);
            return {
              id: thread.id,
              title: thread.title,
              messages: [],
              createdAt: new Date(thread.created_at).getTime(),
              lastUpdated: new Date(thread.last_message_at || thread.created_at).getTime()
            };
          }
        })
      );
      
      setThreads(threadsWithMessages);
      setCurrentThreadId(threadsWithMessages[0].id);
      console.log('All threads loaded successfully from database');
      showToast(`Loaded ${threadsWithMessages.length} chat threads from database`);
    } catch (err) {
      console.error('❌ Failed to load threads from backend:', err);
      showToast('Failed to load chat history from database');
      createNewThread();
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
      console.log('New thread created in database');
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
    if (confirm('Delete this chat thread?')) {
      try {
        await apiClient.delete(`/api/memory/sqlite/chat/thread/${id}`);
        console.log('Thread deleted from database');
      } catch (err) {
        console.error('Failed to delete thread from database:', err);
      }
      const updated = threads.filter(t => t.id !== id);
      setThreads(updated);
      if (currentThreadId === id) {
        setCurrentThreadId(updated.length > 0 ? updated[0].id : '');
        if (updated.length === 0) createNewThread();
      }
      showToast('Thread deleted');
    }
  };

  // 4. WORKING WEB AUDIO API RECORDING (16kHz Mono for Vosk)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true } 
      });
      streamRef.current = stream;
      audioChunksRef.current = [];
      
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = scriptProcessor;
      
      scriptProcessor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const chunk = new Float32Array(inputData.length);
        chunk.set(inputData);
        audioChunksRef.current.push(chunk);
      };
      
      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);
      
      setIsRecording(true);
      showToast('🎤 Recording started - speak clearly');
    } catch (err) {
      console.error('Failed to start recording:', err);
      showToast('❌ Microphone access denied');
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;
    try {
      if (scriptProcessorRef.current) { scriptProcessorRef.current.disconnect(); scriptProcessorRef.current = null; }
      if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
      if (audioContextRef.current) { await audioContextRef.current.close(); audioContextRef.current = null; }
      
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
      
      const pcmBytes = new Uint8Array(wavBuffer, 44);
      pcmBytes.set(new Uint8Array(pcmData.buffer));
      
      const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
      
      try {
        const formData = new FormData();
        formData.append('file', wavBlob, 'recording.wav');
        const response = await apiClient.post('/api/voice/transcribe', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000
        });
        const text = response.data.text;
        if (text) {
          setInput(prev => prev + (prev ? ' ' : '') + text);
          showToast('✅ Transcription complete');
        } else {
          showToast('⚠️ No speech detected');
        }
      } catch (err: any) {
        console.error('Transcription failed:', err);
        showToast('❌ Transcription failed: ' + (err.response?.data?.detail || err.message));
      }
    } catch (err) {
      console.error('Error stopping recording:', err);
      showToast('❌ Recording error');
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
    if (!input.trim() || isLoading || !currentThreadId) return;
    abortControllerRef.current = new AbortController();
    const extractedFilename = extractFilename(input);
    const userMsg: Message = { id: Date.now().toString(), from: 'user', text: input, model: selectedModel, timestamp: Date.now() };

    setThreads(prev => prev.map(t => 
      t.id === currentThreadId ? { ...t, messages: [...t.messages, userMsg], lastUpdated: Date.now(), title: t.messages.length === 1 ? input.slice(0, 30) : t.title } : t
    ));

    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      const payload = extractedFilename ? { query: currentInput, filename: extractedFilename, model: selectedModel } : { query: currentInput, model: selectedModel };
      const response = await apiClient.post('/api/agent', payload, { signal: abortControllerRef.current.signal, timeout: 3600000 });
      const content = response.data?.content || response.data?.message || response.data?.response || response.data?.text || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
      
      const aiMsg: Message = { id: (Date.now() + 1).toString(), from: 'ai', text: cleanAIResponse(content), filename: response.data?.filename, model: selectedModel, timestamp: Date.now() };
      setThreads(prev => prev.map(t => t.id === currentThreadId ? { ...t, messages: [...t.messages, aiMsg], lastUpdated: Date.now() } : t));
      if (filename) setFilename('');

      // SAVE TO DATABASE IMMEDIATELY
      setTimeout(async () => {
        try {
          await apiClient.post('/api/memory/sqlite/chat/thread', { id: currentThreadId, title: currentThread?.title || 'New Chat' });
          await apiClient.post('/api/memory/sqlite/chat/message', { thread_id: currentThreadId, role: 'user', content: currentInput });
          await apiClient.post('/api/memory/sqlite/chat/message', { thread_id: currentThreadId, role: 'assistant', content: aiMsg.text });
          console.log('Messages saved to SQLite database');
          
          const messageCount = currentThread?.messages.length || 0;
          if (messageCount > 0 && messageCount % 4 === 0) {
            apiClient.post('/api/memory/extract-facts', { thread_id: currentThreadId }).catch(err => console.warn('Fact extraction failed:', err));
          }
        } catch (err) { 
          console.error('❌ Failed to save chat to SQLite:', err);
          showToast('⚠️ Warning: Chat not saved to database');
        }
      }, 0);
    } catch (error: any) {
      if (error.name !== 'AbortError' && error.code !== 'ERR_CANCELED') {
        const errorMsg = error.response?.data?.detail || error.message || 'Connection error';
        setThreads(prev => prev.map(t => t.id === currentThreadId ? { ...t, messages: [...t.messages, { id: (Date.now() + 1).toString(), from: 'ai', text: `Error: ${errorMsg}`, model: selectedModel, timestamp: Date.now() }], lastUpdated: Date.now() } : t));
        showToast('Request failed');
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  useEffect(() => {
    if (chatLogRef.current) chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
  }, [messages, isLoading]);

  return (
    <div className="console reveal delay-2 glow-panel" aria-label="Assistant console" style={{ display: 'flex', flexDirection: 'column', height: isMobile ? 'calc(100vh - 180px)' : '700px', minHeight: isMobile ? '500px' : '540px', overflow: 'hidden' }}>
      <div style={{ width: '100%', padding: '12px 16px', borderBottom: '1px solid var(--line)', background: 'rgba(0,0,0,0.15)' }}>
        <h2 className="console-title" style={{ margin: 0, color: 'var(--accent)', fontSize: '1.4rem', fontWeight: 'bold', letterSpacing: '-0.02em' }}>Assistant Chat Console</h2>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {isSidebarOpen && (
          <>
          {/* Mobile backdrop */}
          {isMobile && (
            <div 
              onClick={() => setIsSidebarOpen(false)}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.5)',
                zIndex: 998,
              }}
            />
          )}
          <div style={{ 
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
          }}>
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: '40px' }}>
              <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Threads</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {isMobile && (
                  <button 
                    onClick={() => setIsSidebarOpen(false)}
                    style={{ 
                      background: 'none', 
                      border: 'none', 
                      color: 'var(--text)', 
                      cursor: 'pointer', 
                      fontSize: '1.5rem',
                      padding: '4px 8px',
                      lineHeight: 1
                    }}
                  >
                    ×
                  </button>
                )}
                <button onClick={createNewThread} title="New Chat" className="chip" style={{ padding: '6px 14px', background: 'none', border: '1px solid var(--accent)', color: 'var(--accent)', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1, borderRadius: '8px', height: '28px', display: 'flex', alignItems: 'center' }}>+</button>
              </div>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
              {isLoadingThreads ? (
                <div style={{ padding: '20px', textAlign: 'center', opacity: 0.7 }}>Loading threads from database...</div>
              ) : (threads || []).map(thread => (
                <div key={thread.id} onClick={() => { setCurrentThreadId(thread.id); if (isMobile) setIsSidebarOpen(false); }} style={{ padding: '10px 12px', borderRadius: '8px', marginBottom: '4px', cursor: 'pointer', background: thread.id === currentThreadId ? 'rgba(255,255,255,0.1)' : 'transparent', border: thread.id === currentThreadId ? '1px solid var(--accent)' : '1px solid transparent', fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: isMobile ? '180px' : '160px' }}>{thread.title}</span>
                  <button onClick={(e) => deleteThread(thread.id, e)} title="Delete thread" className="chip" style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', opacity: 0.7, fontSize: '1.2rem', padding: '2px 8px', borderRadius: '6px' }}>×</button>
                </div>
              ))}
            </div>
            
            {!isMobile && (
              <>
              <div style={{ borderTop: '1px solid var(--line)', margin: '0' }} />
              <div style={{ padding: '14px', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>System Resources</span>
                  <button onClick={async () => {
                    try {
                      const res = await apiClient.get('/api/system/ram');
                      setRamUsed(res.data.used || 0); setRamTotal(res.data.total || 0); setRamPercent(res.data.percent || 0);
                      setSwapUsed(res.data.swap_used || 0); setSwapTotal(res.data.swap_total || 0); setSwapPercent(res.data.swap_percent || 0);
                    } catch (err) { console.error('Failed to refresh:', err); }
                  }} style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', cursor: 'pointer', fontSize: '0.75rem' }} title="Refresh">↻</button>
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}><span>CPU</span><span style={{ opacity: 0.7 }}>{cpuPercent}%</span></div>
                  <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${cpuPercent}%`, background: cpuPercent > 80 ? '#ef4444' : cpuPercent > 60 ? '#f59e0b' : '#10b981', transition: 'width 0.3s' }} />
                  </div>
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}><span>RAM</span><span style={{ opacity: 0.7 }}>{formatSize(ramUsed)} / {formatSize(ramTotal)}</span></div>
                  <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${ramPercent}%`, background: ramPercent > 80 ? '#ef4444' : ramPercent > 60 ? '#f59e0b' : 'var(--accent)', transition: 'width 0.3s' }} />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}><span>Swap</span><span style={{ opacity: 0.7 }}>{formatSize(swapUsed)} / {formatSize(swapTotal)}</span></div>
                  <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${swapPercent}%`, background: swapPercent > 80 ? '#ef4444' : swapPercent > 60 ? '#f59e0b' : '#8b5cf6', transition: 'width 0.3s' }} />
                  </div>
                </div>
              </div>
              </>
            )}
          </div>
          </>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, position: 'relative' }}>
          <div style={{ padding: isMobile ? '6px 10px' : '8px 16px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: isMobile ? '6px' : '12px', flexWrap: 'wrap', minHeight: '40px' }}>
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="chip" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: '8px', padding: isMobile ? '4px 10px' : '6px 12px', cursor: 'pointer', fontSize: isMobile ? '0.75rem' : '0.85rem', fontWeight: 500, height: '28px', display: 'flex', alignItems: 'center' }}>
              {isMobile ? '☰' : (isSidebarOpen ? 'Hide' : 'Show')} {isMobile ? '' : 'Threads'}
            </button>
            <select value={selectedModel} onChange={handleModelChange} disabled={isLoading || availableModels.length === 0} className="chip" style={{ padding: isMobile ? '4px 8px' : '6px 12px', borderRadius: '8px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: isMobile ? '0.8rem' : '0.9rem', cursor: isLoading ? 'not-allowed' : 'pointer', outline: 'none', minWidth: isMobile ? '120px' : '180px', height: '28px', flex: isMobile ? 1 : 'none' }}>
              {availableModels.length > 0 ? availableModels.map(model => <option key={model} value={model}>{model}</option>) : <option value="" disabled>Loading models...</option>}
            </select>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', fontSize: isMobile ? '0.75rem' : '0.85rem', fontWeight: 500 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: isLoading ? '#f59e0b' : '#22c55e', display: 'inline-block', animation: isLoading ? 'none' : 'pulse 2s infinite', boxShadow: isLoading ? 'none' : '0 0 8px rgba(34, 197, 94, 0.6)' }} />
              <span style={{ color: isLoading ? '#f59e0b' : 'var(--accent)' }}>{isLoading ? 'Processing' : 'Ready'}</span>
            </div>
          </div>

          <div ref={chatLogRef} className="chat-log" aria-live="polite" style={{ flex: 1, overflowY: 'auto', padding: isMobile ? '10px' : '16px', scrollBehavior: 'smooth' }}>
            {(messages || []).map((msg) => <ChatMessage key={msg.id} type={msg.from} text={msg.text} filename={msg.filename} model={msg.model !== 'system' ? msg.model : undefined} timestamp={msg.timestamp} />)}
          </div>

          <div style={{ padding: isMobile ? '8px 10px' : '10px 16px', borderTop: '1px solid var(--line)', background: 'rgba(0,0,0,0.1)' }}>
            {!isMobile && (
              <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'nowrap' }}>
                <label htmlFor="fileUpload" className="chip" style={{ fontSize: '0.8rem', color: 'var(--text)', cursor: 'pointer', padding: '4px 10px', borderRadius: '6px', border: '1px dashed var(--line)', background: 'rgba(255,255,255,0.02)', height: '26px', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap' }}>Attach file</label>
                <input id="fileUpload" type="file" onChange={(e) => { const file = e.target.files?.[0]; if (file) { setFilename(file.name); showToast(`Selected: ${file.name}`); } }} style={{ display: 'none' }} />
                {filename && (
                  <span style={{ fontSize: '0.8rem', opacity: 0.9, display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.08)', border: '1px solid var(--line)', height: '26px', maxWidth: '300px' }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{filename}</span>
                    <button onClick={() => setFilename('')} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0', fontSize: '1rem', lineHeight: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '18px', height: '18px' }}>×</button>
                  </span>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: isMobile ? '6px' : '10px', alignItems: 'flex-end' }}>
              <textarea ref={textareaRef} placeholder={filename ? "Describe file content..." : "Ask MAi-RAG..."} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} rows={isMobile ? 2 : 4} disabled={isLoading} style={{ flex: 1, minHeight: isMobile ? '60px' : '110px', maxHeight: isMobile ? '100px' : '155px', padding: isMobile ? '8px 10px' : '12px 14px', borderRadius: '10px', border: '1px solid var(--line)', background: 'rgba(255,255,255,0.04)', color: 'var(--text)', fontSize: isMobile ? '0.9rem' : '1rem', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.5 }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? '4px' : '6px', alignItems: 'center' }}>
                <button 
                  onClick={isLoading ? abortRequest : sendMessage} 
                  disabled={!isLoading && !input.trim()} 
                  className="btn" 
                  style={{ width: isMobile ? 44 : 52, height: isMobile ? 44 : 52, borderRadius: '10px', border: 'none', background: isLoading ? '#ef4444' : (!input.trim() ? 'rgba(255,255,255,0.1)' : 'var(--accent, #7cf6d3)'), color: (!isLoading && !input.trim()) ? '#666' : '#fff', cursor: (!isLoading && !input.trim()) ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '1.1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' }}
                  title={isLoading ? 'Stop generation' : 'Send message'}
                >
                  {isLoading ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                  )}
                </button>
                <button 
                  aria-label="Record voice" 
                  title={isRecording ? 'Stop recording' : 'Voice input'} 
                  onClick={isRecording ? stopRecording : startRecording}
                  className="chip" 
                  style={{ width: isMobile ? 44 : 52, height: isMobile ? 44 : 52, borderRadius: '10px', border: isRecording ? '2px solid #ef4444' : '1px solid var(--line)', background: isRecording ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255,255,255,0.04)', color: isRecording ? '#ef4444' : 'var(--text)', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '1rem', animation: isRecording ? 'pulse 1s infinite' : 'none' }}
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
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 8px rgba(34, 197, 94, 0.6); } 50% { opacity: 0.7; transform: scale(0.95); box-shadow: 0 0 12px rgba(34, 197, 94, 0.9); } }`}</style>
    </div>
  );
};

export default ChatConsoleApp;
