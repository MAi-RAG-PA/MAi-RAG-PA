// frontend/src/components/chat/ChatMessage.tsx
import React, { useState } from 'react';

interface ChatMessageProps {
  type: 'user' | 'ai';
  text: string;
  filename?: string;
  model?: string;
  timestamp?: number; // ✅ Add timestamp prop
}

const ChatMessage: React.FC<ChatMessageProps> = ({ type, text, filename, model, timestamp }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const isUser = type === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '12px',
      position: 'relative',
    }}>
      <div style={{
        maxWidth: '80%',
        padding: '10px 14px',
        borderRadius: '12px',
        background: isUser ? 'var(--accent, #7cf6d3)' : 'rgba(255,255,255,0.08)',
        color: isUser ? '#000' : 'var(--text)',
        position: 'relative',
      }}>
        {/* Copy Button - Only for AI messages */}
        {!isUser && (
          <button
            onClick={copyToClipboard}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
            style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              opacity: 0.6,
              transition: 'opacity 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onMouseOver={(e) => (e.currentTarget.style.opacity = '1')}
            onMouseOut={(e) => (e.currentTarget.style.opacity = '0.6')}
          >
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            )}
          </button>
        )}

        {/* Message Content */}
        <div style={{ 
          whiteSpace: 'pre-wrap', 
          wordBreak: 'break-word',
          paddingRight: !isUser ? '24px' : '0',
        }}>
          {text}
        </div>

        {/* Timestamp */}
        {timestamp && (
          <div style={{ fontSize: '0.7rem', opacity: 0.5, marginTop: '4px', textAlign: 'right' }}>
            {new Date(timestamp).toLocaleTimeString()}
          </div>
        )}

        {/* Filename if present */}
        {filename && (
          <div style={{
            marginTop: '8px',
            padding: '4px 8px',
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '4px',
            fontSize: '0.85rem',
            opacity: 0.9,
          }}>
            📄 {filename}
          </div>
        )}

        {/* Model info */}
        {model && !isUser && (
          <div style={{
            marginTop: '6px',
            fontSize: '0.75rem',
            opacity: 0.6,
            textAlign: 'right',
          }}>
            {model}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
