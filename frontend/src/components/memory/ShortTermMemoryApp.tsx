// frontend/src/components/memory/ShortTermMemoryApp.tsx
import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../../api/client';

const ShortTermMemoryApp: React.FC = () => {
  const [instruction, setInstruction] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  // Storage & Backup state
  const [stmSize, setStmSize] = useState(0);
  const [isExportingSTM, setIsExportingSTM] = useState(false);
  const [isImportingSTM, setIsImportingSTM] = useState(false);
  const stmFileInputRef = useRef<HTMLInputElement>(null);
  
  // Database entries count
  const [totalEntries, setTotalEntries] = useState(0);

  // Fetch STM size
  useEffect(() => {
    const fetchSTMSize = async () => {
      try {
        const res = await apiClient.get('/api/memory/analytics/stm-size');
        setStmSize(res.data.size || 0);
      } catch (err) {
        console.error('Failed to fetch STM size:', err);
      }
    };
    
    fetchSTMSize();
    const interval = setInterval(fetchSTMSize, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch total database entries
  useEffect(() => {
    const fetchEntries = async () => {
      try {
        const [eventsRes, remindersRes, todosRes, chatsRes, notesRes] = await Promise.all([
          apiClient.get('/api/memory/sqlite/events/all?limit=10000'),
          apiClient.get('/api/memory/sqlite/reminders/upcoming?limit=10000'),
          apiClient.get('/api/memory/sqlite/todos?limit=10000'),
          apiClient.get('/api/memory/sqlite/chat/threads'),
          apiClient.get('/api/notes')
        ]);

        const events = eventsRes.data.events?.length || 0;
        const reminders = remindersRes.data.reminders?.length || 0;
        const todos = todosRes.data.todos?.length || 0;
        const chats = chatsRes.data.threads?.length || 0;
        const notes = notesRes.data.notes?.length || 0;

        setTotalEntries(events + reminders + todos + chats + notes);
      } catch (err) {
        console.error('Failed to fetch entries:', err);
      }
    };

    fetchEntries();
    const interval = setInterval(fetchEntries, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveInstruction = async () => {
    if (!instruction.trim()) return;
    setStatus('saving');
    try {
      // Changed URL from '/api/memory/sqlite/profile' to '/api/memory/sqlite/user-profile'
        await apiClient.post('/api/memory/sqlite/user-profile', { 
        key: 'short_term_instruction', 
        value: { 
          text: instruction.trim(), 
          timestamp: new Date().toISOString(), 
          active: true 
        } 
      });
      setStatus('saved'); 
      setInstruction(''); 
      setTimeout(() => setStatus('idle'), 3000);
    } catch (err) { 
      console.error('Failed to save instruction:', err); 
      setStatus('error'); 
      setTimeout(() => setStatus('idle'), 3000); 
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSaveInstruction(); }
  };

  const handleExportSTM = async () => {
    setIsExportingSTM(true);
    try {
      const [eventsRes, remindersRes, todosRes, chatsRes, notesRes, profileRes] = await Promise.all([
        apiClient.get('/api/memory/sqlite/events/all?limit=10000'),
        apiClient.get('/api/memory/sqlite/reminders/upcoming?limit=10000'),
        apiClient.get('/api/memory/sqlite/todos?limit=10000'),
        apiClient.get('/api/memory/sqlite/chat/threads'),
        apiClient.get('/api/notes'),
        apiClient.get('/api/memory/sqlite/user-profile')
      ]);

      const backup = {
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        type: 'sqlite',
        events: eventsRes.data.events || [],
        reminders: remindersRes.data.reminders || [],
        todos: todosRes.data.todos || [],
        chats: chatsRes.data.threads || [],
        notes: notesRes.data.notes || [],
        profile: profileRes.data.profile || {}
      };

      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mai-rag-stm-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      alert('✅ STM backup exported');
    } catch (err) {
      console.error('STM export failed:', err);
      alert('❌ Failed to export STM');
    } finally {
      setIsExportingSTM(false);
    }
  };

  const handleImportSTM = () => {
    stmFileInputRef.current?.click();
  };

  const handleSTMFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!window.confirm('⚠️ This will merge STM backup data. Continue?')) {
      return;
    }
    
    setIsImportingSTM(true);
    try {
      const text = await file.text();
      const backup = JSON.parse(text);
      
      const response = await apiClient.post('/api/memory/restore', backup);
      const restored = response.data.restored;
      
      alert(`✅ STM backup restored!\nEvents: ${restored.events}\nReminders: ${restored.reminders}\nTodos: ${restored.todos}\nChats: ${restored.chats}\nNotes: ${restored.notes}`);
    } catch (err: any) {
      console.error('STM import failed:', err);
      alert(`❌ Import failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsImportingSTM(false);
      if (stmFileInputRef.current) {
        stmFileInputRef.current.value = '';
      }
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <section className="console reveal delay-3 file-upload-panel glow-panel" 
    style={{ minHeight: 'auto', height: 'auto', display: 'flex', flexDirection: 'column', padding: '16px 24px', boxSizing: 'border-box', marginBottom: '24px' }}>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        <div 
          className="console-title" 
          style={{ 
            color: 'var(--accent)', 
            fontSize: '1.3rem', 
            fontWeight: 'bold', 
            marginBottom: '12px' 
          }}
        >
          Short-Term Memory
        </div>
        <p style={{ fontSize: '0.9rem', opacity: 0.9, margin: '0 0 4px 0', lineHeight: 1.4 }}>All planner data and chat history are <strong>automatically saved by the system</strong>.</p>
        <p style={{ fontSize: '0.85rem', opacity: 0.7, margin: 0 }}> MAi-RAG learns about you over time, as a Personal Assistant should.</p>
      </div>
      <div style={{ paddingTop: '8px', borderTop: '1px dashed var(--line)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <textarea
          placeholder="Use this field to; Add facts, Correct Information, or Inject Short-Term Instructions. 
Example: 'Remember my deadline is Friday'"
          value={instruction} onChange={e => setInstruction(e.target.value)} onKeyDown={handleKeyDown}
          rows={18}
          style={{ 
            width: '100%', 
            padding: '10px', 
            borderRadius: '6px', 
            border: '1px solid var(--line)', 
            background: 'rgba(255,255,255,0.04)', 
            color: 'var(--text)', 
            fontSize: '0.9rem', 
            fontFamily: 'inherit', 
            resize: 'vertical',
            outline: 'none', 
            boxSizing: 'border-box',
            minHeight: '100px'  // Added minimum height
          }}
        />
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button onClick={handleSaveInstruction} disabled={status === 'saving' || !instruction.trim()} style={{ flex: 1, padding: '8px 12px', borderRadius: '6px', background: status === 'saving' ? 'rgba(255,255,255,0.1)' : instruction.trim() ? 'var(--accent)' : 'rgba(255,255,255,0.1)', color: status === 'saving' || !instruction.trim() ? '#666' : '#000', border: 'none', cursor: status === 'saving' || !instruction.trim() ? 'not-allowed' : 'pointer', fontWeight: 500, fontSize: '0.85rem' }}>
            {status === 'idle' ? 'Remember' : status === 'saving' ? 'Saving...' : status === 'saved' ? '✓ Saved' : '✗ Failed'}
          </button>
          <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>Enter to save</span>
        </div>
      </div>

      {/* Storage & Stats Section - 2 COLUMNS */}
      <div style={{ 
        paddingTop: '12px', 
        borderTop: '1px solid var(--line)', 
        marginTop: '12px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px'
      }}>
        {/* Left Column: STM Storage */}
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
            Short-Term Memory Storage
          </div>
          <div style={{ 
            padding: '10px', 
            borderRadius: '6px', 
            background: 'rgba(255,255,255,0.04)', 
            border: '1px solid var(--line)'
          }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent)' }}>
              {formatSize(stmSize)}
            </div>
          </div>
        </div>
        
        {/* Right Column: Database Entries */}
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
            Number of Database Entries
          </div>
          <div style={{ 
            padding: '10px', 
            borderRadius: '6px', 
            background: 'rgba(255,255,255,0.04)', 
            border: '1px solid var(--line)'
          }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent)' }}>
              {totalEntries}
            </div>
          </div>
        </div>
      </div>
      
      {/* Backup Buttons */}
      <div style={{ marginTop: '12px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>
          Short-Term Memory Backup
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={handleExportSTM} 
            disabled={isExportingSTM}
            style={{ 
              flex: 1, 
              padding: '8px', 
              borderRadius: '6px', 
              border: 'none', 
              background: isExportingSTM ? 'rgba(255,255,255,0.1)' : 'var(--accent)', 
              color: isExportingSTM ? '#666' : '#000', 
              cursor: isExportingSTM ? 'not-allowed' : 'pointer', 
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            {isExportingSTM ? 'Exporting...' : 'Export STM'}
          </button>
          <button 
            onClick={handleImportSTM} 
            disabled={isImportingSTM}
            style={{ 
              flex: 1, 
              padding: '8px', 
              borderRadius: '6px', 
              border: '1px solid var(--accent)', 
              background: 'transparent', 
              color: isImportingSTM ? '#666' : 'var(--accent)', 
              cursor: isImportingSTM ? 'not-allowed' : 'pointer', 
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            {isImportingSTM ? 'Importing...' : 'Import STM'}
          </button>
        </div>
      </div>

      <input
        type="file"
        ref={stmFileInputRef}
        onChange={handleSTMFileSelect}
        accept=".json"
        style={{ display: 'none' }}
      />
    </section>
  );
};
export default ShortTermMemoryApp;
