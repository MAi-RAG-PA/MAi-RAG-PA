// frontend/src/components/layout/Header.tsx
import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../../api/client';

interface HeaderProps {
  onNavigate?: (id: string) => void;
  showToast?: (msg: string) => void;
}

const Header: React.FC<HeaderProps> = ({ onNavigate, showToast }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [theme, setTheme] = useState('default');
  const [systemStatus, setSystemStatus] = useState<'running' | 'stopped' | 'unknown'>('running');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const mobileMenuRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const updateIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    updateIsMobile();
    window.addEventListener('resize', updateIsMobile);

    return () => window.removeEventListener('resize', updateIsMobile);
  }, []);

  useEffect(() => {
    const savedTheme = localStorage.getItem('mai-rag-theme') || 'default';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mai-rag-theme', theme);
  }, [theme]);

  useEffect(() => {
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isMobileMenuOpen && mobileMenuRef.current) {
      const firstLink = mobileMenuRef.current.querySelector('a');
      firstLink?.focus();
    } else if (!isMobileMenuOpen && menuButtonRef.current) {
      menuButtonRef.current.focus();
    }
  }, [isMobileMenuOpen]);

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        menuButtonRef.current?.focus();
        return;
      }

      if (e.key === 'Tab' && mobileMenuRef.current) {
        const focusableElements = mobileMenuRef.current.querySelectorAll<HTMLElement>(
          'a, button, [tabindex]:not([tabindex="-1"])'
        );

        if (!focusableElements.length) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

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
    if (!window.confirm('Are you sure you want to stop MAi-RAG-PA? All services will be shut down.')) {
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
      console.error('Failed to stop MAi-RAG-PA:', err);
      setIsProcessing(false);
      alert('Failed to stop MAi-RAG-PA. Please try again.');
    }
  };

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent parent handlers from interfering
    setIsMobileMenuOpen(false);

    if (onNavigate) {
      onNavigate(id);
      return;
    }

    const el = document.getElementById(id);
    if (el) {
      const header = document.querySelector('header');
      const headerHeight = header ? header.offsetHeight : 88;

      // Calculate exact position and add a 20px buffer so it's not cramped under the header
      const elementPosition = el.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - headerHeight - 20;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth',
      });
    }
  };

  const getButtonText = () => {
    return isProcessing ? 'Stopping...' : 'Stop System';
  };

  const getButtonIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );

  const getButtonColor = () => {
    if (isProcessing) {
      return {
        background: 'rgba(245, 158, 11, 0.2)',
        color: '#f59e0b',
        border: '1px solid rgba(245, 158, 11, 0.3)',
      };
    }
    // Always show as "Stop" style since we only stop
    return {
      background: 'rgba(239, 68, 68, 0.1)',
      color: '#ef4444',
      border: '1px solid rgba(239, 68, 68, 0.3)',
    };
  };

  const handleButtonClick = () => {
    if (isProcessing || systemStatus !== 'running') return;
    handleStopSystem();
  };

  const getStatusText = () => {
    if (systemStatus === 'running') return 'Running';
    if (systemStatus === 'stopped') return 'Stopped';
    return 'Checking...';
  };

  const getStatusColor = () => {
    if (systemStatus === 'running') return '#22c55e';
    if (systemStatus === 'stopped') return '#ef4444';
    return '#f59e0b';
  };

  return (
    <>
      <a
        href="#console"
        onClick={(e) => handleClick(e, 'console')}
        style={{
          position: 'absolute',
          left: '-9999px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
          zIndex: 10000,
          padding: '12px 20px',
          background: 'var(--accent)',
          color: 'var(--bg)',
          textDecoration: 'none',
          fontWeight: 700,
          borderRadius: '0 0 8px 0',
          fontSize: '0.9rem',
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'fixed';
          e.currentTarget.style.left = '0';
          e.currentTarget.style.top = '0';
          e.currentTarget.style.width = 'auto';
          e.currentTarget.style.height = 'auto';
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute';
          e.currentTarget.style.left = '-9999px';
          e.currentTarget.style.width = '1px';
          e.currentTarget.style.height = '1px';
        }}
      >
        Skip to main content
      </a>

      <header
        role="banner"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          backdropFilter: 'blur(18px)',
          background: `
            linear-gradient(180deg, rgba(12,15,20,0.92), rgba(12,15,20,0.65)),
            radial-gradient(ellipse at top, rgba(124, 246, 211, 0.08), transparent 70%)
          `,
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 4px 24px rgba(124, 246, 211, 0.12)',
        }}
      >
        <div
          className="nav"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            maxWidth: '1400px',
            width: '100%',
            margin: '0 auto',
            padding: isMobile ? '12px' : '16px 24px',
            gap: isMobile ? '8px' : '20px',
            boxSizing: 'border-box',
            position: 'relative',
          }}
        >
          <a
            href="#home"
            onClick={(e) => {
              e.preventDefault();
              handleClick(e, 'home');
            }}
            aria-label="MAi-RAG-PA Home - Return to top of page"
            style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              transition: 'opacity 0.2s ease',
              opacity: 0.9,
              flexShrink: 0,
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
                filter: 'drop-shadow(0 0 8px rgba(124, 246, 211, 0.4))',
              }}
            />
          </a>

          {!isMobile && (
            <nav
              className="nav-links"
              aria-label="Primary navigation"
              style={{
                display: 'flex',
                gap: '20px',
                flexWrap: 'nowrap',
              }}
            >
              <a
                href="#console"
                onClick={(e) => handleClick(e, 'console')}
                style={navLinkStyle}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)'; }}
              >
                Chat Console
              </a>
              <a
                href="#notes"
                onClick={(e) => handleClick(e, 'notes')}
                style={navLinkStyle}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)'; }}
              >
                Text Editor
              </a>
              <a
                href="#memory"
                onClick={(e) => handleClick(e, 'memory')}
                style={navLinkStyle}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)'; }}
              >
                Memory
              </a>
              <a
                href="#planner"
                onClick={(e) => handleClick(e, 'planner')}
                style={navLinkStyle}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)'; }}
              >
                Calendar Planner
              </a>
              <a
                href="#settings"
                onClick={(e) => handleClick(e, 'settings')}
                style={navLinkStyle}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--muted)'; }}
              >
                Assistant Settings
              </a>
            </nav>
          )}

          <div
            className="nav-actions"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: isMobile ? '8px' : '12px',
              flexShrink: 0,
            }}
          >
            <label htmlFor="theme-selector" className="sr-only" style={srOnlyStyle}>
              Select color theme
            </label>

            <select
              id="theme-selector"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
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
                minWidth: isMobile ? '80px' : '140px',
              }}
              aria-label="Select color theme"
            >
              <option value="default">Deep Blue & Cyan</option>
              <option value="purple-yellow">Purple & Yellow</option>
              <option value="blue-orange">Blue & Orange</option>
              <option value="pink-cyan">Pink & Cyan</option>
              <option value="dark-grey">Slate Grey</option>
              <option value="forest-green">Deep Forest</option>
              <option value="sunset-orange">Royal Sunset</option>
              <option value="ocean-blue">Caribbean Teal</option>
              <option value="royal-purple">Royal Purple</option>
              <option value="antique-bronze">Antique Bronze</option>
              <option value="crimson-red">Crimson Red</option>
              <option value="amber-gold">Amber Gold</option>
              <option value="midnight-blue">Midnight Blue</option>
              <option value="emerald-mint">Emerald Mint</option>
              <option value="indigo-coral">Indigo Coral</option>
              <option value="cyberpunk-neon">Cyberpunk Neon</option>
              <option value="seafoam-apricot">Seafoam Apricot</option>
              <option value="volcanic-ash">Volcanic Ash</option>
              <option value="bamboo-grove">Forest Mystic</option>
              <option value="nebula-drift">Nebula Drift</option>
              <option value="copper-teal">Copper & Teal</option>
              <option value="rose-quartz">Rose Quartz</option>
              <option value="graphite">Radioactive</option>
              <option value="solar-flare">Solar Flare</option>
            </select>

            {!isMobile && (
              <div
                role="status"
                aria-live="polite"
                aria-label={`System status: ${getStatusText()}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid var(--line)',
                  fontSize: '0.85rem',
                  height: '36px',
                }}
              >
                <div
                  aria-hidden="true"
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: getStatusColor(),
                    boxShadow:
                      systemStatus === 'running' ? '0 0 8px rgba(34, 197, 94, 0.6)' : 'none',
                    animation: isProcessing ? 'pulse 1s infinite' : 'none',
                  }}
                />
                <span style={{ color: 'var(--text)', fontWeight: 500 }}>{getStatusText()}</span>
              </div>
            )}

            <button
              onClick={handleButtonClick}
              disabled={isProcessing}
              aria-label={
                isProcessing
                  ? systemStatus === 'running'
                    ? 'Stopping MAi-RAG-PA services, please wait'
                    : 'Starting MAi-RAG services, please wait'
                  : systemStatus === 'running'
                    ? 'Stop MAi-RAG-PA services'
                    : 'Start MAi-RAG-PA services'
              }
              aria-busy={isProcessing}
              title={systemStatus === 'running' ? 'Stop MAi-RAG-PA services' : 'Start MAi-RAG-PA services'}
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
                ...getButtonColor(),
              }}
            >
              {getButtonIcon()}
              {!isMobile && <span>{getButtonText()}</span>}
            </button>

            <a
              href="https://www.paypal.com/ncp/payment/GSTCK29MSGCH4"
              target="_blank"
              rel="noopener noreferrer"
              title="PayPal me - If you find MAi-RAG-PA useful, Please donate to help contine updates & new features"
              className="donate-button"
              aria-label="Support MAi-RAG-PA with a donation via PayPal (opens in new tab)"
            >
              Coffee & Donate 🍩
            </a>

            {isMobile && (
              <button
                ref={menuButtonRef}
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
                aria-expanded={isMobileMenuOpen}
                aria-controls="mobile-nav-menu"
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
                  transition: 'all 0.2s ease',
                }}
              >
                <span aria-hidden="true">{isMobileMenuOpen ? '×' : '☰'}</span>
              </button>
            )}
          </div>

          {isMobile && isMobileMenuOpen && (
            <>
              <div
                onClick={() => setIsMobileMenuOpen(false)}
                aria-hidden="true"
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

              <nav
                ref={mobileMenuRef}
                id="mobile-nav-menu"
                role="navigation"
                aria-label="Mobile navigation menu"
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
                  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                }}
              >
                <div
                  role="status"
                  aria-live="polite"
                  aria-label={`System status: ${getStatusText()}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '12px',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--line)',
                    marginBottom: '8px',
                  }}
                >
                  <div
                    aria-hidden="true"
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: getStatusColor(),
                      boxShadow:
                        systemStatus === 'running' ? '0 0 8px rgba(34, 197, 94, 0.6)' : 'none',
                    }}
                  />
                  <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: '0.9rem' }}>
                    System: {getStatusText()}
                  </span>
                </div>

                <a href="#console" onClick={(e) => handleClick(e, 'console')} style={mobileLinkStyle}>
                  Chat Console
                </a>
                <a href="#notes" onClick={(e) => handleClick(e, 'notes')} style={mobileLinkStyle}>
                  Text Editor
                </a>
                <a href="#memory" onClick={(e) => handleClick(e, 'memory')} style={mobileLinkStyle}>
                  Memory
                </a>
                <a href="#planner" onClick={(e) => handleClick(e, 'planner')} style={mobileLinkStyle}>
                  Calendar Planner
                </a>
                <a href="#settings" onClick={(e) => handleClick(e, 'settings')} style={mobileLinkStyle}>
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
    </>
  );
};

const navLinkStyle: React.CSSProperties = {
  color: 'var(--muted)',
  fontSize: '0.95rem',
  fontWeight: 'bold',
  textDecoration: 'none',
  transition: 'color 0.2s ease',
  whiteSpace: 'nowrap',
  cursor: 'pointer',
};

const mobileLinkStyle: React.CSSProperties = {
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
  alignItems: 'center',
};

const srOnlyStyle: React.CSSProperties = {
  position: 'absolute',
  left: '-9999px',
};

export default Header;
