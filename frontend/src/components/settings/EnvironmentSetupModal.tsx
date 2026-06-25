// ~/MAi-RAG/frontend/src/components/settings/EnvironmentSetupModal.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';

interface ServiceStatus {
  available: boolean;
  url?: string;
  download_url?: string;
  error?: string;
}

interface EnvironmentStatus {
  ollama: ServiceStatus;
  qdrant: ServiceStatus;
  all_services_available: boolean;
}

const EnvironmentSetupModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<EnvironmentStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    checkEnvironment();
  }, []);

  const checkEnvironment = async () => {
    setIsChecking(true);
    try {
      const response = await apiClient.get('/api/system/environment');
      setStatus(response.data);
      
      // Show modal if not all services are available
      if (!response.data.all_services_available) {
        setIsOpen(true);
      }
    } catch (err) {
      console.error('Failed to check environment:', err);
    } finally {
      setIsChecking(false);
    }
  };

  const handleRetry = async () => {
    await checkEnvironment();
    if (status?.all_services_available) {
      setIsOpen(false);
    }
  };

  if (!isOpen || !status) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-secondary, #1a1a1a)',
        borderRadius: '12px',
        padding: '32px',
        maxWidth: '600px',
        width: '100%',
        border: '1px solid var(--line, #333)',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)'
      }}>
        <h2 style={{
          color: 'var(--accent, #7cf6d3)',
          fontSize: '1.5rem',
          marginBottom: '16px',
          marginTop: 0
        }}>
          ⚠️ Setup Required
        </h2>
        
        <p style={{
          color: 'var(--text, #fff)',
          marginBottom: '24px',
          lineHeight: 1.6
        }}>
          MAi-RAG requires the following services to be running for full functionality:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
          {/* Ollama Status */}
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            background: status.ollama.available ? 'rgba(124, 246, 211, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${status.ollama.available ? 'var(--accent, #7cf6d3)' : '#ef4444'}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--text, #fff)', fontSize: '1.1rem' }}>
                {status.ollama.available ? '✅' : '❌'} Ollama
              </strong>
              {!status.ollama.available && (
                <a
                  href={status.ollama.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: 'var(--accent, #7cf6d3)',
                    color: '#000',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    fontWeight: 600
                  }}
                >
                  Download
                </a>
              )}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary, #aaa)' }}>
              {status.ollama.available 
                ? `Running at ${status.ollama.url}`
                : 'Required for AI model inference. Download and install from ollama.com'
              }
            </div>
          </div>

          {/* Qdrant Status */}
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            background: status.qdrant.available ? 'rgba(124, 246, 211, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${status.qdrant.available ? 'var(--accent, #7cf6d3)' : '#ef4444'}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <strong style={{ color: 'var(--text, #fff)', fontSize: '1.1rem' }}>
                {status.qdrant.available ? '✅' : '❌'} Qdrant
              </strong>
              {!status.qdrant.available && (
                <a
                  href={status.qdrant.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: 'var(--accent, #7cf6d3)',
                    color: '#000',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    fontWeight: 600
                  }}
                >
                  Setup Guide
                </a>
              )}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary, #aaa)' }}>
              {status.qdrant.available 
                ? `Running at ${status.qdrant.url}`
                : 'Required for long-term memory (RAG). See setup guide for installation instructions.'
              }
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleRetry}
            disabled={isChecking}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '8px',
              background: isChecking ? 'rgba(255, 255, 255, 0.1)' : 'var(--accent, #7cf6d3)',
              color: isChecking ? '#666' : '#000',
              border: 'none',
              cursor: isChecking ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem'
            }}
          >
            {isChecking ? 'Checking...' : 'Retry Connection'}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            style={{
              flex: 1,
              padding: '12px',
              borderRadius: '8px',
              background: 'transparent',
              color: 'var(--text, #fff)',
              border: '1px solid var(--line, #333)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.95rem'
            }}
          >
            Continue Anyway
          </button>
        </div>

        <p style={{
          fontSize: '0.8rem',
          color: 'var(--text-secondary, #aaa)',
          marginTop: '16px',
          marginBottom: 0,
          textAlign: 'center'
        }}>
          💡 You can continue using MAi-RAG, but some features will be limited until services are running.
        </p>
      </div>
    </div>
  );
};

export default EnvironmentSetupModal;
