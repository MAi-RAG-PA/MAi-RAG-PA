// frontend/src/components/layout/Header.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';

interface HeaderProps {
  onNavigate?: (id: string) => void;
  showToast?: (msg: string) => void;
}

const Header: React.FC<HeaderProps> = ({ onNavigate, showToast }) => {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [systemStatus, setSystemStatus] = useState<'running' | 'stopped' | 'unknown'>('running');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) {
        setIsMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkSystemStatus = async () => {
    try {
      const response = await apiClient.get('/api/system/status');
      const newStatus = response.data.status;
      
      if (isProcessing && newStatus !== 'unknown') {
        setIsProcessing(false);
      }
      
      setSystemStatus(newStatus);
    } catch (err) {
      setSystemStatus('stopped');
      if (isProcessing) {
        setIsProcessing(false);
      }
    }
  };

  const handleStopSystem = async () => {
    if (!window.confirm('Are you sure you want to stop MAi-RAG? All services will be shut down.')) {
      return;
    }
    
    setIsProcessing(true);
    try {
      await apiClient.post('/api/system/stop');
      setTimeout(() => {
        setSystemStatus('stopped');
        setIsProcessing(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to stop MAi-RAG:', err);
      setIsProcessing(false);
      alert('Failed to stop MAi-RAG. Please try again.');
    }
  };

  const handleStartSystem = async () => {
    setIsProcessing(true);
    try {
      await fetch('http://127.0.0.1:8001/start', { 
        method: 'POST',
        mode: 'no-cors'
      });
      
      setIsProcessing(false);
      
      let attempts = 0;
      const checkInterval = setInterval(async () => {
        attempts++;
        try {
          await apiClient.get('/api/health');
          clearInterval(checkInterval);
          window.location.reload();
        } catch (err) {
          if (attempts > 30) {
            clearInterval(checkInterval);
            alert('Start timed out. Please check logs.');
            setIsProcessing(false);
          }
        }
      }, 500);
      
    } catch (err) {
      console.error('Failed to contact Watchdog:', err);
      setIsProcessing(false);
      alert('Failed to start. Is the Watchdog running?');
    }
  };

const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
  e.preventDefault();
  setIsMobileMenuOpen(false);
  
  if (onNavigate) {
    onNavigate(id);
  } else {
    const el = document.getElementById(id);
    if (el) {
      // Get actual header height dynamically
      const header = document.querySelector('header');
      const headerHeight = header ? header.offsetHeight : 88;
      const headerOffset = headerHeight + 0;
      const elementPosition = el.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  }
};

  const getButtonText = () => {
    if (isProcessing) {
      return systemStatus === 'running' ? 'Stopping...' : 'Starting...';
    }
    return systemStatus === 'running' ? 'Stop' : 'Start';
  };

  const getButtonIcon = () => {
    if (systemStatus === 'running') {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      );
    } else {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="5,3 19,12 5,21" />
        </svg>
      );
    }
  };

  const getButtonColor = () => {
    if (isProcessing) {
      return {
        background: 'rgba(245, 158, 11, 0.2)',
        color: '#f59e0b',
        border: '1px solid rgba(245, 158, 11, 0.3)'
      };
    }
    if (systemStatus === 'running') {
      return {
        background: 'rgba(239, 68, 68, 0.1)',
        color: '#ef4444',
        border: '1px solid rgba(239, 68, 68, 0.3)'
      };
    } else {
      return {
        background: 'rgba(34, 197, 94, 0.1)',
        color: '#22c55e',
        border: '1px solid rgba(34, 197, 94, 0.3)'
      };
    }
  };

  const handleButtonClick = () => {
    if (isProcessing) return;
    
    if (systemStatus === 'running') {
      handleStopSystem();
    } else {
      handleStartSystem();
    }
  };

  return (
    <header style={{ 
      position: 'sticky',
      top: 0,
      zIndex: 1000,
      backdropFilter: 'blur(18px)',
      background: `
        linear-gradient(180deg, rgba(12,15,20,0.92), rgba(12,15,20,0.65)),
        radial-gradient(ellipse at top, rgba(124, 246, 211, 0.08), transparent 70%)
      `,
      borderBottom: '1px solid rgba(255,255,255,0.08)',
      boxShadow: '0 4px 24px rgba(124, 246, 211, 0.12)'
    }}>
      <div className="nav" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        maxWidth: '1400px',
        width: '100%',
        margin: '0 auto',
        padding: isMobile ? '12px' : '16px 24px',
        gap: isMobile ? '8px' : '20px',
        boxSizing: 'border-box',
        position: 'relative'
      }}>
        
        {/* Logo */}
        <a 
          href="#home" 
          onClick={(e) => {
            e.preventDefault();
            handleClick(e, 'home');
          }}
          aria-label="MAi-RAG Home" 
          style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            transition: 'opacity 0.2s ease',
            opacity: 0.9,
            flexShrink: 0
          }}
          onMouseOver={(e) => (e.currentTarget.style.opacity = '1')}
          onMouseOut={(e) => (e.currentTarget.style.opacity = '0.9')}
        >
          <img 
            src="/MAi-RAG.png" 
            alt="MAi-RAG Logo" 
            style={{ 
              width: isMobile ? '50px' : '100px',  
              height: isMobile ? '36px' : '72px', 
              objectFit: 'contain',
              filter: 'drop-shadow(0 0 8px rgba(124, 246, 211, 0.4))'
            }}
          />
        </a>

        {/* Desktop Nav Links */}
        {!isMobile && (
          <nav 
            className="nav-links" 
            aria-label="Primary navigation" 
            style={{ 
              display: 'flex',
              gap: '20px',
              flexWrap: 'nowrap'
            }}
          >
            <a href="#console" onClick={(e) => handleClick(e, 'console')} 
               onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
               onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted)'}
               style={{
                 color: 'var(--muted)',
                 fontSize: '0.95rem',
                 fontWeight: 'bold',
                 textDecoration: 'none',
                 transition: 'color 0.2s ease',
                 padding: '4px 8px',
                 borderRadius: '6px'
               }}>Chat Console</a>
            <a href="#notes" onClick={(e) => handleClick(e, 'notes')}
               onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
               onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted)'}
               style={{
                 color: 'var(--muted)',
                 fontSize: '0.95rem',
                 fontWeight: 'bold',
                 textDecoration: 'none',
                 transition: 'color 0.2s ease',
                 padding: '4px 8px',
                 borderRadius: '6px'
               }}>Text Editor</a>
            <a href="#memory" onClick={(e) => handleClick(e, 'memory')}
               onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
               onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted)'}
               style={{
                 color: 'var(--muted)',
                 fontSize: '0.95rem',
                 fontWeight: 'bold',
                 textDecoration: 'none',
                 transition: 'color 0.2s ease',
                 padding: '4px 8px',
                 borderRadius: '6px'
               }}>Memory</a>
            <a href="#planner" onClick={(e) => handleClick(e, 'planner')}
               onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
               onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted)'}
               style={{
                 color: 'var(--muted)',
                 fontSize: '0.95rem',
                 fontWeight: 'bold',
                 textDecoration: 'none',
                 transition: 'color 0.2s ease',
                 padding: '4px 8px',
                 borderRadius: '6px'
               }}>Calendar Planner</a>
            <a href="#settings" onClick={(e) => handleClick(e, 'settings')}
               onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
               onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted)'}
               style={{
                 color: 'var(--muted)',
                 fontSize: '0.95rem',
                 fontWeight: 'bold',
                 textDecoration: 'none',
                 transition: 'color 0.2s ease',
                 padding: '4px 8px',
                 borderRadius: '6px'
               }}>Assistant Settings</a>
          </nav>
        )}

        {/* Right-Aligned Actions */}
        <div className="nav-actions" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: isMobile ? '8px' : '12px',
          flexShrink: 0
        }}>
          
          {/* Theme Selector */}
          <select
            onChange={(e) => {
              const theme = e.target.value;
              document.documentElement.setAttribute('data-theme', theme);
              localStorage.setItem('mai-rag-theme', theme);
            }}
            defaultValue={localStorage.getItem('mai-rag-theme') || 'default'}
            style={{
              padding: isMobile ? '6px 8px' : '8px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--text)',
              fontSize: isMobile ? '0.8rem' : '0.9rem',
              cursor: 'pointer',
              outline: 'none',
              fontWeight: 500,
              height: '36px',
              minWidth: isMobile ? '80px' : '140px'
            }}
            aria-label="Select color theme"
          >
            <option value="default">Default</option>
            <option value="purple-yellow">Purple & Yellow</option>
            <option value="blue-orange">Blue & Orange</option>
            <option value="pink-cyan">Pink & Cyan</option>
            <option value="dark-grey">Dark Grey</option>
            <option value="forest-green">Forest Green</option>
            <option value="sunset-orange">Sunset Orange</option>
            <option value="ocean-blue">Ocean Blue</option>
            <option value="royal-purple">Royal Purple</option>
            <option value="monochrome">Blue Grey</option>
            <option value="crimson-red">Crimson Red</option>
            <option value="amber-gold">Amber Gold</option>
            <option value="midnight-blue">Midnight Blue</option>
            <option value="emerald-mint">Emerald Mint</option>
            <option value="lavender-dream">Lavender Dream</option>
            <option value="cyberpunk-neon">Cyberpunk Neon</option>
            <option value="arctic-frost">Arctic Frost</option>
            <option value="volcanic-ash">Volcanic Ash</option>
            <option value="bamboo-grove">Bamboo Grove</option>
            <option value="nebula-drift">Nebula Drift</option>
            <option value="copper-teal">Copper & Teal</option>
            <option value="rose-quartz">Rose Quartz</option>
            <option value="graphite">Radioactive</option>
            <option value="solar-flare">Solar Flare</option>
          </select>

          {/* Status Indicator - Desktop only */}
          {!isMobile && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--line)',
              fontSize: '0.85rem',
              height: '36px',
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: systemStatus === 'running' ? '#22c55e' : 
                           systemStatus === 'stopped' ? '#ef4444' : '#f59e0b',
                boxShadow: systemStatus === 'running' ? '0 0 8px rgba(34, 197, 94, 0.6)' : 'none',
                animation: isProcessing ? 'pulse 1s infinite' : 'none',
              }} />
              <span style={{ color: 'var(--text)', fontWeight: 500 }}>
                {systemStatus === 'running' ? 'Running' : 
                 systemStatus === 'stopped' ? 'Stopped' : 'Checking...'}
              </span>
            </div>
          )}

          {/* Stop/Start Button */}
          <button 
            onClick={handleButtonClick}
            disabled={isProcessing}
            title={systemStatus === 'running' ? 'Stop MAi-RAG services' : 'Start MAi-RAG services'}
            style={{
              padding: isMobile ? '8px 12px' : '8px 16px',
              borderRadius: '8px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              fontSize: isMobile ? '0.8rem' : '0.9rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: isProcessing ? 0.7 : 1,
              height: '36px',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
              ...getButtonColor()
            }}
          >
            {getButtonIcon()}
            {!isMobile && getButtonText()}
          </button>

          {/* Hamburger Menu Button - PROMINENT on mobile */}
          {isMobile && (
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle navigation menu"
              style={{
                background: isMobileMenuOpen ? 'var(--accent)' : 'rgba(255,255,255,0.06)',
                border: '2px solid var(--accent)',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '48px',
                height: '48px',
                color: isMobileMenuOpen ? 'var(--bg)' : 'var(--text)',
                fontSize: '1.8rem',
                fontWeight: 'bold',
                flexShrink: 0,
                transition: 'all 0.2s ease'
              }}
            >
              {isMobileMenuOpen ? '×' : '☰'}
            </button>
          )}
        </div>

        {/* Mobile Navigation Menu - Fixed position overlay */}
        {isMobile && isMobileMenuOpen && (
          <>
            {/* Backdrop */}
            <div
              onClick={() => setIsMobileMenuOpen(false)}
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.5)',
                zIndex: 998,
              }}
            />
            
            {/* Menu Panel */}
            <nav
              style={{
                position: 'fixed',
                top: '72px',
                left: 0,
                right: 0,
                maxHeight: 'calc(100vh - 72px)',
                overflowY: 'auto',
                background: 'rgba(12,15,20,0.98)',
                backdropFilter: 'blur(18px)',
                borderBottom: '1px solid var(--line)',
                zIndex: 999,
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                boxShadow: '0 8px 24px rgba(0,0,0,0.6)'
              }}
            >
              {/* Status Indicator */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px',
                borderRadius: '8px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--line)',
                marginBottom: '8px'
              }}>
                <div style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: systemStatus === 'running' ? '#22c55e' : 
                             systemStatus === 'stopped' ? '#ef4444' : '#f59e0b',
                  boxShadow: systemStatus === 'running' ? '0 0 8px rgba(34, 197, 94, 0.6)' : 'none',
                }} />
                <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: '0.9rem' }}>
                  System: {systemStatus === 'running' ? 'Running' : 
                           systemStatus === 'stopped' ? 'Stopped' : 'Checking...'}
                </span>
              </div>

              {/* Navigation Links */}
              <a href="#console" onClick={(e) => handleClick(e, 'console')}
                 style={{
                   color: 'var(--text)',
                   fontSize: '1rem',
                   fontWeight: 600,
                   textDecoration: 'none',
                   padding: '14px 16px',
                   borderRadius: '8px',
                   background: 'rgba(255,255,255,0.04)',
                   border: '1px solid var(--line)',
                   minHeight: '44px',
                   display: 'flex',
                   alignItems: 'center'
                 }}>
                Chat Console
              </a>
              <a href="#notes" onClick={(e) => handleClick(e, 'notes')}
                 style={{
                   color: 'var(--text)',
                   fontSize: '1rem',
                   fontWeight: 600,
                   textDecoration: 'none',
                   padding: '14px 16px',
                   borderRadius: '8px',
                   background: 'rgba(255,255,255,0.04)',
                   border: '1px solid var(--line)',
                   minHeight: '44px',
                   display: 'flex',
                   alignItems: 'center'
                 }}>
                Text Editor
              </a>
              <a href="#memory" onClick={(e) => handleClick(e, 'memory')}
                 style={{
                   color: 'var(--text)',
                   fontSize: '1rem',
                   fontWeight: 600,
                   textDecoration: 'none',
                   padding: '14px 16px',
                   borderRadius: '8px',
                   background: 'rgba(255,255,255,0.04)',
                   border: '1px solid var(--line)',
                   minHeight: '44px',
                   display: 'flex',
                   alignItems: 'center'
                 }}>
                Memory
              </a>
              <a href="#planner" onClick={(e) => handleClick(e, 'planner')}
                 style={{
                   color: 'var(--text)',
                   fontSize: '1rem',
                   fontWeight: 600,
                   textDecoration: 'none',
                   padding: '14px 16px',
                   borderRadius: '8px',
                   background: 'rgba(255,255,255,0.04)',
                   border: '1px solid var(--line)',
                   minHeight: '44px',
                   display: 'flex',
                   alignItems: 'center'
                 }}>
                Calendar Planner
              </a>
              <a href="#settings" onClick={(e) => handleClick(e, 'settings')}
                 style={{
                   color: 'var(--text)',
                   fontSize: '1rem',
                   fontWeight: 600,
                   textDecoration: 'none',
                   padding: '14px 16px',
                   borderRadius: '8px',
                   background: 'rgba(255,255,255,0.04)',
                   border: '1px solid var(--line)',
                   minHeight: '44px',
                   display: 'flex',
                   alignItems: 'center'
                 }}>
                Assistant Settings
              </a>
            </nav>
          </>
        )}
        
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </header>
  );
};

export default Header;
