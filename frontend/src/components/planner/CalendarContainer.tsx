// src/components/planner/CalendarContainer.tsx
import React from 'react';
import CalendarApp from './CalendarApp';

const CalendarContainer: React.FC = () => {
  return (
    <div style={{
      background: 'transparent',
      padding: '20px'
    }}>
      <CalendarApp />
    </div>
  );
};

export default CalendarContainer;