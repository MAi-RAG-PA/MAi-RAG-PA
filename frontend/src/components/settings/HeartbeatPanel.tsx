// frontend/src/components/settings/HeartbeatPanel.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';

interface HeartbeatPanelProps {
  showToast: (msg: string) => void;
}

const HeartbeatPanel: React.FC<HeartbeatPanelProps> = ({ showToast }) => {
  const [interval, setIntervalState] = useState(30);
  const [isLoading, setIsLoading] = useState(false);
  const [heartbeatPrompt, setHeartbeatPrompt] = useState('');
  const [lastStatus, setLastStatus] = useState('UNKNOWN');
  const [nextBeat, setNextBeat] = useState('Calculating...');
  const [heartbeatStatus, setHeartbeatStatus] = useState({
    last_check: null,
    last_status: 'UNKNOWN',
    last_message: 'Not yet run',
    next_check: null,
    is_running: false
  });

  useEffect(() => {
    loadHeartbeat();
    loadHeartbeatPrompt();
    fetchStatus();
    
    // Poll every 2 seconds for responsive updates
    const statusInterval = setInterval(fetchStatus, 2000);
    
    return () => clearInterval(statusInterval);
  }, []);

  const loadHeartbeat = async () => {
    try {
      const response = await apiClient.get('/api/settings/heartbeat');
      if (response.data?.interval !== undefined) {
        setIntervalState(response.data.interval);
      }
    } catch (error) {
      console.error('Failed to load heartbeat settings:', error);
    }
  };

  const loadHeartbeatPrompt = async () => {
    try {
      const response = await apiClient.get('/api/settings/heartbeat-prompt');
      if (response.data?.prompt) {
        setHeartbeatPrompt(response.data.prompt);
      }
    } catch (error) {
      console.warn('Could not load saved heartbeat prompt (using default)');
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await apiClient.get('/api/heartbeat/status');
      const data = response.data;
      
      setHeartbeatStatus(data);
      setLastStatus(data.last_status || 'UNKNOWN');
      
      if (data.next_check) {
        const nextCheckDate = new Date(data.next_check);
        setNextBeat(nextCheckDate.toLocaleTimeString());
      } else {
        setNextBeat('Calculating...');
      }
      
    } catch (error) {
      console.error('Failed to fetch heartbeat status:', error);
      setLastStatus('Offline');
    }
  };

  const saveInterval = async () => {
    if (interval < 1 || interval > 1440) {
      showToast('Interval must be 1-1440 minutes');
      return;
    }
    setIsLoading(true);
    try {
      await apiClient.post('/api/settings/heartbeat', { interval });
      showToast(`Heartbeat set to ${interval} minutes ✓`);
      fetchStatus();
    } catch (error) {
      console.error('Failed to save heartbeat:', error);
      showToast('Failed to save heartbeat settings');
    } finally {
      setIsLoading(false);
    }
  };

  const triggerNow = async () => {
    setIsLoading(true);
    try {
      await apiClient.post('/api/heartbeat/trigger');
      showToast('✅ Heartbeat triggered');
      fetchStatus();
    } catch (error) {
      console.error('Failed to trigger heartbeat:', error);
      showToast('❌ Failed to trigger heartbeat');
    } finally {
      setIsLoading(false);
    }
  };

  const saveHeartbeatPrompt = async () => {
    if (!heartbeatPrompt.trim()) {
      showToast('Heartbeat prompt cannot be empty');
      return;
    }
    setIsLoading(true);
    try {
      await apiClient.post('/api/settings/heartbeat-prompt', { 
        prompt: heartbeatPrompt.trim() 
      });
      showToast('✅ Heartbeat prompt saved');
    } catch (error) {
      console.error('Failed to save heartbeat prompt:', error);
      showToast('❌ Failed to save heartbeat prompt');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section 
      className="panel reveal delay-3 glow-panel" 
      aria-label="Heartbeat Settings"
    >
      <div className="panel-inner" style={{ padding: '22px 22px 16px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 className="console-title" style={{ margin: 0 }}>Heartbeat</h3>
          <span style={{ 
            fontSize: '0.8rem', 
            padding: '4px 12px', 
            borderRadius: 20,
            backgroundColor: lastStatus === 'OK' ? 'rgba(34,197,94,0.2)' : 
                           lastStatus === 'ERROR' ? 'rgba(239,68,68,0.2)' : 
                           lastStatus === 'RUNNING' ? 'rgba(245,158,11,0.2)' : 'rgba(107,114,128,0.2)',
            color: lastStatus === 'OK' ? '#22c55e' : 
                   lastStatus === 'ERROR' ? '#ef4444' : 
                   lastStatus === 'RUNNING' ? '#f59e0b' : '#6b7280'
          }}>
            {lastStatus === 'OK' ? '● Active' : 
             lastStatus === 'ERROR' ? '● Error' : 
             lastStatus === 'RUNNING' ? '⏳ Running' : '○ Unknown'}
          </span>
        </div>

        {/* Description */}
        <p style={{ fontSize: '0.9rem', opacity: 0.8, lineHeight: 1.4, marginBottom: 16, margin: 0 }}>
          Configure how often the assistant runs self-checks, memory cleanup, and maintenance tasks.
        </p>

        {/* Interval Controls */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 16 }}>
          <label htmlFor="heartbeatInterval" style={{ fontSize: '0.9rem' }}>
            Check every:
          </label>
          
          <input
            id="heartbeatInterval"
            type="number"
            min={1}
            max={1440}
            value={interval}
            onChange={(e) => setIntervalState(Math.max(1, Math.min(1440, Number(e.target.value))))}
            disabled={isLoading}
            style={{
              width: 80,
              padding: '8px 12px',
              borderRadius: 8,
              border: '1px solid var(--line)',
              background: 'rgba(255,255,255,0.04)',
              color: 'var(--text)',
              fontSize: '1rem',
              textAlign: 'center'
            }}
          />
          
          <span style={{ fontSize: '0.9rem', opacity: 0.8 }}>minutes</span>
          
          <button
            onClick={saveInterval}
            disabled={isLoading}
            className="btn"
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              backgroundColor: 'var(--accent, #7cf6d3)',
              color: '#000',
              border: 'none',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              marginLeft: 'auto'
            }}
          >
            {isLoading ? 'Saving...' : 'Save'}
          </button>
        </div>

        {/* Status Info */}
        <div style={{ 
          padding: 12, 
          borderRadius: 8, 
          background: 'rgba(255,255,255,0.04)',
          fontSize: '0.85rem',
          marginBottom: 16
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ opacity: 0.7 }}>Last status:</span>
            <span style={{ 
              color: lastStatus === 'OK' ? '#22c55e' : 
                     lastStatus === 'ERROR' ? '#ef4444' : 
                     lastStatus === 'RUNNING' ? '#f59e0b' : '#6b7280'
            }}>
              {lastStatus}
            </span>
          </div>
          {heartbeatStatus.last_message && heartbeatStatus.last_message !== 'Not yet run' && (
            <div style={{ fontSize: '0.8rem', opacity: 0.7, marginTop: 4 }}>
              {heartbeatStatus.last_message}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
            <span style={{ opacity: 0.7 }}>Next check:</span>
            <span>
              {heartbeatStatus.is_running ? 'After current check' : nextBeat}
            </span>
          </div>
          {heartbeatStatus.is_running && (
            <div style={{ marginTop: 4, fontSize: '0.8rem', color: '#f59e0b' }}>
              ⏳ Heartbeat check in progress...
            </div>
          )}
        </div>
        
        {/* Heartbeat Prompt Section */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--line)' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px', display: 'block' }}>
            Heartbeat Prompt
          </label>
          <textarea
            value={heartbeatPrompt}
            onChange={(e) => setHeartbeatPrompt(e.target.value)}
            placeholder="Enter custom heartbeat instructions..."
            style={{
              width: '100%',
              minHeight: '100px',
              padding: '10px',
              borderRadius: '6px',
              border: '1px solid var(--line)',
              background: 'rgba(255,255,255,0.04)',
              color: 'var(--text)',
              fontSize: '0.9rem',
              fontFamily: 'monospace',
              resize: 'vertical'
            }}
          />
          <button
            onClick={saveHeartbeatPrompt}
            disabled={isLoading || !heartbeatPrompt.trim()}
            className="chip"
            style={{
              marginTop: '8px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: '1px solid var(--accent)',
              background: isLoading || !heartbeatPrompt.trim() ? 'rgba(124, 246, 211, 0.08)' : 'rgba(124, 246, 211, 0.15)',
              color: 'var(--accent)',
              cursor: isLoading || !heartbeatPrompt.trim() ? 'not-allowed' : 'pointer',
              fontSize: '0.85rem'
            }}
          >
            {isLoading ? 'Saving...' : 'Save Heartbeat Prompt'}
          </button>
        </div>

        {/* Manual Trigger Button */}
        <button
          onClick={triggerNow}
          disabled={isLoading || heartbeatStatus.is_running}
          className="chip"
          style={{
            marginTop: '16px',
            padding: '10px 20px',
            borderRadius: 6,
            backgroundColor: 'rgba(255,255,255,0.08)',
            color: 'var(--text)',
            border: '1px solid var(--line)',
            cursor: (isLoading || heartbeatStatus.is_running) ? 'not-allowed' : 'pointer'
          }}
        >
          {heartbeatStatus.is_running ? 'Running...' : 'Run Heartbeat Now'}
        </button>

        {/* Helper Text */}
        <div style={{ marginTop: 16, fontSize: '0.75rem', opacity: 0.6, lineHeight: 1.4 }}>
          <strong>Note:</strong> Shorter intervals = more responsive maintenance, but higher CPU usage. 
          Recommended: 15-60 minutes for most systems.
        </div>
      </div>
    </section>
  );
};

export default HeartbeatPanel;
