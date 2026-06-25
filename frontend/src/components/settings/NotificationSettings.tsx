// frontend/src/components/settings/NotificationSettings.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';

interface NotificationInterval {
  label: string;
  minutes: number;
  enabled: boolean;
}

interface NotificationSettingsProps {
  showToast: (msg: string) => void;
}

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ showToast }) => {
  const [intervals, setIntervals] = useState<NotificationInterval[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await apiClient.get('/api/settings/notifications');
      setIntervals(response.data.intervals);
    } catch (err) {
      console.error('Failed to load notification settings:', err);
    }
  };

  const toggleInterval = (index: number) => {
    setIntervals(prev => prev.map((item, i) => 
      i === index ? { ...item, enabled: !item.enabled } : item
    ));
  };

  const saveSettings = async () => {
    setIsLoading(true);
    try {
      await apiClient.post('/api/settings/notifications', { intervals });
      showToast('Notification settings saved');
    } catch (err) {
      showToast('Failed to save settings');
    } finally {
      setIsLoading(false);
    }
  };

  const getLabel = (label: string) => {
    switch(label) {
      case '24h': return '1 Day Before';
      case '1h': return '1 Hour Before';
      case '30m': return '30 Minutes Before';
      case '15m': return '15 Minutes Before';
      case '5m': return '5 Minutes Before';
      case '0m': return 'At Event Time';
      default: return label;
    }
  };

  const getDescription = (interval: NotificationInterval) => {
    if (interval.minutes === 0) return 'Notify exactly when event starts';
    if (interval.minutes >= 60) return `Notify ${interval.minutes / 60} hour(s) before`;
    return `Notify ${interval.minutes} minutes before`;
  };

  return (
    <div style={{ padding: '16px', background: 'rgba(255,255,255,0.04)', borderRadius: '12px' }}>
      <h3 style={{ marginBottom: '16px', color: 'var(--accent)', fontSize: '1.1rem', fontWeight: 600 }}>
        Notification Schedule
      </h3>
      <p style={{ fontSize: '0.9rem', opacity: 0.8, marginBottom: '16px', lineHeight: 1.4 }}>
        Choose when you want to be notified before events and reminders:
      </p>

      {/* ✅ TWO-COLUMN GRID LAYOUT */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(2, 1fr)', 
        gap: '12px',
        marginBottom: '16px'
      }}>
        {(intervals || []).map((interval, index) => (
          <label 
            key={interval.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px',
              background: interval.enabled ? 'rgba(124, 246, 211, 0.08)' : 'rgba(255,255,255,0.04)',
              borderRadius: '8px',
              cursor: 'pointer',
              border: interval.enabled ? '1px solid var(--accent)' : '1px solid var(--line)',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              type="checkbox"
              checked={interval.enabled}
              onChange={() => toggleInterval(index)}
              style={{ width: '20px', height: '20px', cursor: 'pointer', accentColor: 'var(--accent)' }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: interval.enabled ? 'var(--accent)' : 'var(--text)' }}>
                {getLabel(interval.label)}
              </div>
              <div style={{ fontSize: '0.85rem', opacity: 0.7 }}>
                {getDescription(interval)}
              </div>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={saveSettings}
        disabled={isLoading}
        className="btn"
        style={{
          padding: '10px 20px',
          borderRadius: '8px',
          background: isLoading ? 'rgba(255,255,255,0.1)' : 'var(--accent, #7cf6d3)',
          color: isLoading ? '#666' : '#000',
          border: 'none',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          fontWeight: 600,
          width: '100%',
        }}
      >
        {isLoading ? 'Saving...' : 'Save Notification Settings'}
      </button>
    </div>
  );
};

export default NotificationSettings;
