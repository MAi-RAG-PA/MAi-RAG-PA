// src/components/Toast.tsx
import React, { useEffect, useState } from 'react';

interface ToastProps {
  message: string;
  duration?: number;
  onClose?: () => void;
}

const Toast: React.FC<ToastProps> = ({ message, duration = 2600, onClose }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (message) {
      setVisible(true);
      const timer = setTimeout(() => {
        setVisible(false);
        if (onClose) onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [message, duration, onClose]);

  if (!visible) return null;

  return (
    <div
      className="toast show"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      style={{
        position: 'fixed',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'var(--accent, #7cf6d3)',
        color: '#000',
        padding: '12px 24px',
        borderRadius: 16,
        fontWeight: '700',
        boxShadow: '0 0 20px rgba(124, 246, 211, 0.6)',
        zIndex: 1000000,
        opacity: 1,
        transition: 'opacity 0.3s ease',
      }}
    >
      {message}
    </div>
  );
};

export default Toast;
