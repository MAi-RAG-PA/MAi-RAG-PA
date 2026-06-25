// frontend/src/components/planner/CalendarPlannerApp.tsx
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import apiClient from '../../api/client';

// =============================================================================
// Constants
// =============================================================================

const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December"
];

const WEEKDAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const WEEKDAY_LONG = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
const WEEKDAY_NAMES = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

// =============================================================================
// Types
// =============================================================================

interface CalendarEntry {
  id: string;
  title: string;
  type: string;
  details: string;
  start: string;
  end: string;
  is_recurring?: boolean;
  recurrence_type?: string;
  recurrence_days?: string[];
  recurrence_end_date?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

const pad = (n: number) => String(n).padStart(2, "0");

const startOfWeek = (date: Date) => {
  const d = new Date(date);
  d.setHours(0,0,0,0);
  d.setDate(d.getDate() - d.getDay());
  return d;
};

const endOfWeek = (date: Date) => {
  const d = startOfWeek(date);
  d.setDate(d.getDate() + 6);
  return d;
};

const addDays = (date: Date, days: number) => {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
};

const addMonths = (date: Date, months: number) => {
  const d = new Date(date);
  d.setMonth(d.getMonth() + months);
  return d;
};

const addYears = (date: Date, years: number) => {
  const d = new Date(date);
  d.setFullYear(d.getFullYear() + years);
  return d;
};

const formatDateKey = (date: Date) => {
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`;
};

const formatDateTimeLocal = (date: Date) => {
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const getMonthMatrix = (year: number, month: number) => {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const start = startOfWeek(first);
  const end = endOfWeek(last);

  const days: Date[] = [];
  let cursor = new Date(start);
  while(cursor <= end){
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
};

const getWeekDays = (date: Date) => {
  const start = startOfWeek(date);
  return Array.from({length:7}, (_, i) => addDays(start, i));
};

const getHoursOfDay = (date: Date) => {
  return Array.from({length:24}, (_, i) => {
    const d = new Date(date);
    d.setHours(i, 0, 0, 0);
    return d;
  });
};

// =============================================================================
// Sub-Component: EventModal
// =============================================================================

interface EventModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (entry: CalendarEntry) => void;
  onUpdate: (entry: CalendarEntry) => void;
  baseDate: Date;
  mode: string;
  entry: CalendarEntry | null;
}

const EventModal: React.FC<EventModalProps> = ({ open, onClose, onSave, onUpdate, baseDate, mode, entry }) => {
  const [title, setTitle] = useState("");
  const [type, setType] = useState("event");
  const [details, setDetails] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceType, setRecurrenceType] = useState('weekly');
  const [recurrenceDays, setRecurrenceDays] = useState<string[]>([]);
  const [recurrenceEndDate, setRecurrenceEndDate] = useState('');

  useEffect(() => {
    if (open) {
      if (entry && mode === "edit") {
        console.log('📝 Populating edit form with entry:', entry);
        setTitle(entry.title);
        setType(entry.type);
        setDetails(entry.details);
        setStart(entry.start);
        setEnd(entry.end);
        
        setIsRecurring(entry.is_recurring || false);
        setRecurrenceType(entry.recurrence_type || 'weekly');
        setRecurrenceDays(entry.recurrence_days || []);
        setRecurrenceEndDate(entry.recurrence_end_date || '');
      } else if (baseDate) {
        setTitle("");
        setType("event");
        setDetails("");
        setStart(formatDateTimeLocal(baseDate));
        const oneHourLater = new Date(baseDate.getTime() + 60 * 60 * 1000);
        setEnd(formatDateTimeLocal(oneHourLater));
        
        setIsRecurring(false);
        setRecurrenceType('weekly');
        setRecurrenceDays([]);
        setRecurrenceEndDate('');
      }
    }
  }, [open, entry, baseDate, mode]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if(!title.trim() || !start) return;

    const newEntry: CalendarEntry = {
      id: entry?.id || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now())),
      title: title.trim(),
      type,
      details: details.trim(),
      start,
      end,
      is_recurring: isRecurring,
      recurrence_type: isRecurring ? recurrenceType : undefined,
      recurrence_days: isRecurring && recurrenceType === 'weekly' ? recurrenceDays : undefined,
      recurrence_end_date: isRecurring && recurrenceEndDate ? recurrenceEndDate : undefined,
    };

    if(mode === "edit"){
      onUpdate(newEntry);
    } else {
      onSave(newEntry);
    }

    onClose();
  };

  const toggleDay = (dayName: string) => {
    if (recurrenceDays.includes(dayName)) {
      setRecurrenceDays(recurrenceDays.filter(d => d !== dayName));
    } else {
      setRecurrenceDays([...recurrenceDays, dayName]);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxHeight: '90vh', overflowY: 'auto' }}>
        <h3>{mode === "edit" ? "Edit" : "Create"} Entry</h3>
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="entryTitle">Title</label>
            <input id="entryTitle" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Project sync, dentist, reminder..." required />
          </div>

          <div className="field">
            <label htmlFor="entryType">Type</label>
            <select id="entryType" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="event">Event</option>
              <option value="appointment">Appointment</option>
              <option value="reminder">Reminder</option>
              <option value="task">Task</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="entryStart">Start</label>
            <input id="entryStart" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} required />
          </div>

          <div className="field">
            <label htmlFor="entryEnd">End</label>
            <input id="entryEnd" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>

          <div className="field">
            <label htmlFor="entryDetails">Notes</label>
            <textarea id="entryDetails" value={details} onChange={(e) => setDetails(e.target.value)} placeholder="Notes..."></textarea>
          </div>

          <div className="field" style={{ 
            marginTop: '16px', 
            padding: '12px', 
            background: 'rgba(255,255,255,0.04)', 
            borderRadius: '8px',
            border: '1px solid var(--line)'
          }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginBottom: isRecurring ? '12px' : '0' }}>
              <input
                type="checkbox"
                checked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <span style={{ fontWeight: 600 }}>Recurring Event</span>
            </label>

            {isRecurring && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', opacity: 0.8 }}>Repeat:</label>
                  <select
                    value={recurrenceType}
                    onChange={(e) => setRecurrenceType(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid var(--line)',
                      background: 'rgba(255,255,255,0.04)',
                      color: 'var(--text)',
                      fontSize: '0.9rem'
                    }}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                  </select>
                </div>

                {recurrenceType === 'weekly' && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', opacity: 0.8 }}>Days:</label>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((dayLetter, idx) => {
                        const dayName = WEEKDAY_NAMES[idx];
                        const isSelected = recurrenceDays.includes(dayName);
                        
                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => toggleDay(dayName)}
                            style={{
                              width: '36px',
                              height: '36px',
                              borderRadius: '50%',
                              border: isSelected ? '2px solid var(--accent)' : '1px solid var(--line)',
                              background: isSelected ? 'var(--accent)' : 'rgba(255,255,255,0.04)',
                              color: isSelected ? '#000' : 'var(--text)',
                              cursor: 'pointer',
                              fontWeight: 600,
                              fontSize: '0.9rem',
                              transition: 'all 0.2s'
                            }}
                          >
                            {dayLetter}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', opacity: 0.8 }}>Repeat Until:</label>
                  <input
                    type="date"
                    value={recurrenceEndDate}
                    onChange={(e) => setRecurrenceEndDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid var(--line)',
                      background: 'rgba(255,255,255,0.04)',
                      color: 'var(--text)',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="modal-actions">
            <button type="button" className="chip" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn">{mode === "edit" ? "Save changes" : "Save entry"}</button>
          </div>
        </form>
      </div>
    </div>
  );
};

// =============================================================================
// Main Component: CalendarPlannerApp
// =============================================================================

const CalendarPlannerApp: React.FC = () => {
  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState<"year" | "month" | "week" | "day">("year");
  const [anchorDate, setAnchorDate] = useState(today);
  const [selectedDate, setSelectedDate] = useState(today);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("entry");
  const [currentEntry, setCurrentEntry] = useState<CalendarEntry | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [entries, setEntries] = useState<CalendarEntry[]>([]);

  useEffect(() => {
    const loadEventsFromSQLite = async () => {
      try {
        setIsLoading(true);
        const res = await apiClient.get('/api/memory/sqlite/events/all?limit=1000');
        const sqliteEvents: CalendarEntry[] = (res.data.events || []).map((e: any) => ({
          id: e.id,
          title: e.title,
          type: e.category === 'appointment' ? 'appointment' : 'event',
          details: e.description || '',
          start: e.start_time,
          end: e.end_time || '',
          is_recurring: e.is_recurring || false,
          recurrence_type: e.recurrence_type,
          recurrence_days: e.recurrence_days,
          recurrence_end_date: e.recurrence_end_date,
        }));
        
        const remindersRes = await apiClient.get('/api/memory/sqlite/reminders/upcoming?limit=50');
        const reminderEntries: CalendarEntry[] = (remindersRes.data.reminders || []).map((r: any) => ({
          id: r.id,
          title: r.text,
          type: 'reminder',
          details: '',
          start: r.due_time,
          end: r.due_time,
        }));
        
        setEntries([...sqliteEvents, ...reminderEntries]);
      } catch (err) {
        console.warn('Failed to load events from SQLite:', err);
        setEntries([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadEventsFromSQLite();
  }, [today]);

  const entriesByDate = useMemo(() => {
    const map: Record<string, CalendarEntry[]> = {};
    entries.forEach(entry => {
      const d = new Date(entry.start);
      const key = formatDateKey(d);
      if(!map[key]) map[key] = [];
      map[key].push(entry);
    });
    return map;
  }, [entries]);

  const currentYear = anchorDate.getFullYear();
  const currentMonth = anchorDate.getMonth();

  const goPrev = useCallback(() => {
    if(view === "year") setAnchorDate(addYears(anchorDate, -1));
    if(view === "month") setAnchorDate(addMonths(anchorDate, -1));
    if(view === "week") setAnchorDate(addDays(anchorDate, -7));
    if(view === "day") setAnchorDate(addDays(anchorDate, -1));
  }, [view, anchorDate]);

  const goNext = useCallback(() => {
    if(view === "year") setAnchorDate(addYears(anchorDate, 1));
    if(view === "month") setAnchorDate(addMonths(anchorDate, 1));
    if(view === "week") setAnchorDate(addDays(anchorDate, 7));
    if(view === "day") setAnchorDate(addDays(anchorDate, 1));
  }, [view, anchorDate]);

  const resetToToday = () => {
    setAnchorDate(today);
    setSelectedDate(today);
    setView("year");
  };

  const openCreate = (date: Date, modeLabel = "entry") => {
    setCurrentEntry(null);
    setSelectedDate(date);
    setModalMode(modeLabel);
    setModalOpen(true);
  };

  const handleEditEntry = useCallback((entry: CalendarEntry) => {
    console.log('✏️ Editing entry:', entry);
    setCurrentEntry(entry);
    setSelectedDate(new Date(entry.start));
    setModalMode("edit");
    setModalOpen(true);
  }, []);

  const entryToPayload = (entry: CalendarEntry) => {
    let tableName = 'events';

    // CRITICAL: If recurring, ALWAYS use events table (only it supports recurrence)
    if (entry.is_recurring) {
      tableName = 'events';
    } else if (entry.type === 'reminder') {
      tableName = 'reminders';
    } else if (entry.type === 'task' || entry.type === 'todo') {
      tableName = 'todos';
    } else {
      tableName = 'events';
    }

    const payload: any = {
      id: entry.id,
      title: entry.title,
      description: entry.details,
      start_time: entry.start,
      end_time: entry.end,
    };

    // Add recurrence fields for events
    if (tableName === 'events') {
      payload.is_recurring = entry.is_recurring || false;
      payload.recurrence_type = entry.recurrence_type;
      payload.recurrence_days = entry.recurrence_days;
      payload.recurrence_end_date = entry.recurrence_end_date;

      if (entry.type === 'appointment') {
        payload.category = 'appointment';
      } else if (entry.type === 'reminder') {
        payload.category = 'reminder'; // Mark it as a reminder-type event
      } else {
        payload.category = 'general';
      }
    }

    // Add reminder-specific fields (only for non-recurring)
    if (tableName === 'reminders') {
      payload.text = entry.title;
      payload.due_time = entry.start;
      payload.priority = 'medium';
      payload.completed = false;
    }

    // Add todo-specific fields
    if (tableName === 'todos') {
      payload.priority = 'medium';
      payload.completed = false;
      payload.due_date = entry.start.split('T')[0];
    }

    console.log('Payload prepared:', {
      tableName,
      type: entry.type,
      is_recurring: payload.is_recurring,
      recurrence_type: payload.recurrence_type,
      recurrence_days: payload.recurrence_days,
      recurrence_end_date: payload.recurrence_end_date
    });

    return { tableName, payload };
  };

  const showToast = (message: string) => {
    window.dispatchEvent(new CustomEvent('show-toast', { detail: { message } }));
  };

  const handleSaveEntry = async (entry: CalendarEntry) => {
    console.log('handleSaveEntry called with:', entry);

    setEntries(prev => [...prev, entry]);

    try {
      const { tableName, payload } = entryToPayload(entry);

      console.log(`Sending to /api/memory/sqlite/${tableName}:`, payload);

      await apiClient.post(`/api/memory/sqlite/${tableName}`, payload);

      if (entry.is_recurring) {
        showToast(`${entry.title} saved as recurring`);
      } else {
        showToast(`${entry.title} saved`);
      }

      // Reload all events
      const res = await apiClient.get('/api/memory/sqlite/events/all?limit=10000');
      const sqliteEvents: CalendarEntry[] = (res.data.events || []).map((e: any) => ({
        id: e.id,
        title: e.title,
        type: e.category === 'appointment' ? 'appointment' : 'event',
        details: e.description || '',
        start: e.start_time,
        end: e.end_time || '',
        is_recurring: !!e.is_recurring,
        recurrence_type: e.recurrence_type,
        recurrence_days: e.recurrence_days,
        recurrence_end_date: e.recurrence_end_date,
      }));
      setEntries(prev => [...prev.filter(e => e.type !== 'event' && e.type !== 'appointment'), ...sqliteEvents]);

    } catch (err) {
      console.error('Failed to save entry:', err);
      showToast('Failed to save to database');
    }
  };

  const handleDeleteRecurring = async (entryId: string) => {
    const baseId = entryId.split('_')[0];
    const instances = entries.filter(e => e.id.startsWith(baseId));
    
    if (!window.confirm(`Delete this recurring event and all ${instances.length} instances?`)) {
      return;
    }
    
    try {
      await apiClient.delete(`/api/memory/sqlite/events/recurring/${baseId}`);
      setEntries(prev => prev.filter(e => !e.id.startsWith(baseId)));
      showToast(`Deleted ${instances.length} recurring event instances`);
    } catch (err) {
      console.error('Failed to delete recurring event:', err);
      showToast('Failed to delete recurring event');
    }
  };

  const handleDeleteEntry = async (entryId: string) => {
    if(!window.confirm("Are you sure you want to delete this entry?")) return;
    
    const entry = entries.find(e => e.id === entryId);
    if (!entry) return;
    
    setEntries(prev => prev.filter(e => e.id !== entryId));
    
    try {
      const { tableName } = entryToPayload(entry);
      await apiClient.delete(`/api/memory/sqlite/${tableName}/${entryId}`);
      showToast(`${entry.title} deleted`);
    } catch (err) {
      console.error('Failed to delete entry from SQLite:', err);
      showToast('Failed to delete from database');
      window.location.reload();
    }
  };

  const handleUpdateEntry = async (updatedEntry: CalendarEntry) => {
    console.log('💾 Updating entry:', updatedEntry);
    setEntries(prev => prev.map(e => e.id === updatedEntry.id ? updatedEntry : e));
    setCurrentEntry(null);
    
    try {
      const { tableName, payload } = entryToPayload(updatedEntry);
      await apiClient.post(`/api/memory/sqlite/${tableName}`, payload);
      showToast(`${updatedEntry.title} updated`);
    } catch (err) {
      console.error('Failed to update entry in SQLite:', err);
      showToast('Failed to update in database');
    }
  };

  const yearView = (
    <>
      <div className="calendar-grid year-grid" style={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px',
        padding: '8px 8px 8px 0'
      }}>
        {MONTHS.map((monthName, idx) => {
          const totalDays = new Date(currentYear, idx + 1, 0).getDate();
          return (
            <div 
              key={monthName} 
              className="month-card" 
              onClick={() => { 
                setAnchorDate(new Date(currentYear, idx, 1)); 
                setSelectedDate(new Date(currentYear, idx, 1)); 
                setView("month"); 
              }} 
              role="button" 
              tabIndex={0} 
              aria-label={`Open ${monthName} ${currentYear}`}
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--line)',
                borderRadius: '12px',
                padding: '12px',
                cursor: 'pointer',
                transition: 'transform 0.2s, border-color 0.2s',
              }}
              onMouseOver={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)';
              }}
              onMouseOut={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--line)';
              }}
            >
              <div className="month-name" style={{ 
                fontWeight: 600, 
                color: 'var(--accent)',
                marginBottom: '8px',
                textAlign: 'center'
              }}>{monthName}</div>
              
              <div className="month-mini"
                aria-hidden="true"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr)",
                  gap: "2px",
                  userSelect: "none",
                  fontSize: "0.6rem",
                  color: "var(--accent)",
                }}
              >
                {WEEKDAYS.map(day => (
                  <div key={`header-${day}`} style={{ 
                    textAlign: "center", 
                    fontWeight: "bold", 
                    color: "var(--text)", 
                    opacity: 0.7, 
                    fontSize: "0.5rem" 
                  }}>
                    {day.charAt(0)}
                  </div>
                ))}
                
                {Array.from({ length: new Date(currentYear, idx, 1).getDay() }).map((_, i) => (
                  <div key={`empty-${i}`} />
                ))}
                
                {Array.from({ length: totalDays }).map((_, i) => {
                  const dayNum = i + 1;
                  return (
                    <div key={dayNum} style={{
                      textAlign: "center",
                      lineHeight: "1.2",
                      padding: "2px 0",
                      color: "var(--accent)",
                      fontSize: "0.75rem",
                      fontWeight: 500,
                    }}>
                      {dayNum}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );

  const monthDays = getMonthMatrix(currentYear, currentMonth);
  const monthView = (
    <>
      <div className="calendar-caption">
        <h3 style={{ textAlign: 'center', margin: '0 0 12px 0' }}>{MONTHS[currentMonth]} {currentYear}</h3>
      </div>
      <div className="weekday-header">{WEEKDAYS.map(day => <span key={day}>{day}</span>)}</div>
      <div className="calendar-grid month-grid" style={{ padding: '0 8px' }}>
        {monthDays.map((day, i) => {
          const key = formatDateKey(day);
          const dayEntries = entriesByDate[key] || [];
          const isCurrentMonth = day.getMonth() === currentMonth;
          const isToday = formatDateKey(day) === formatDateKey(today);
          return (
            <div key={i} className={`day-cell ${!isCurrentMonth ? "other-month" : ""} ${isToday ? "today" : ""}`} onClick={() => { setAnchorDate(day); setSelectedDate(day); setView("week"); }} role="button" tabIndex={0} aria-label={`Open week of ${day.toDateString()}`}>
              <div className="day-number">{day.getDate()}</div>
              <div className="day-meta">{WEEKDAY_LONG[day.getDay()]}</div>
              {dayEntries.slice(0,2).map(item => <span key={item.id} className="event-pill">{item.title}</span>)}
              {dayEntries.length > 2 && <span className="day-meta">+{dayEntries.length - 2} more</span>}
            </div>
          );
        })}
      </div>
    </>
  );

  const weekDays = getWeekDays(anchorDate);
  const weekView = (
    <>
      <div className="calendar-caption">
        <h3 style={{ textAlign: 'center', margin: '0 0 12px 0' }}>
          Week of {weekDays[0].toLocaleDateString(undefined, { month:"short", day:"numeric" })} – {weekDays[6].toLocaleDateString(undefined, { month:"short", day:"numeric", year:"numeric" })}
        </h3>
      </div>
      <div className="calendar-grid week-grid">
        {weekDays.map((day) => {
          const key = formatDateKey(day);
          const dayEntries = entriesByDate[key] || [];
          const isToday = formatDateKey(day) === formatDateKey(today);
          return (
            <div key={key} className={`week-day-card ${isToday ? "today" : ""}`} onClick={() => { setAnchorDate(day); setSelectedDate(day); setView("day"); }} role="button" tabIndex={0} aria-label={`Open day view for ${day.toDateString()}`}>
              <div className="week-day-head">
                <div><div className="week-day-name">{WEEKDAY_LONG[day.getDay()]}</div><div className="week-day-date">{day.getDate()}</div></div>
                <div className="day-meta">{MONTHS[day.getMonth()].slice(0,3)}</div>
              </div>
              {dayEntries.length ? dayEntries.slice(0,4).map(item => <span key={item.id} className="event-pill">{item.title}</span>) : <div className="day-meta">No entries yet</div>}
            </div>
          );
        })}
      </div>
    </>
  );

  const dayHours = getHoursOfDay(anchorDate);
  const dayKey = formatDateKey(anchorDate);
  const dayEntries = (entriesByDate[dayKey] || []).sort((a,b) => new Date(a.start).getTime() - new Date(b.start).getTime());

  const dayView = (
    <>
      <div className="calendar-caption">
        <h3 style={{ textAlign: 'center', margin: '0 0 12px 0' }}>
          {anchorDate.toLocaleDateString(undefined, { weekday:"long", year:"numeric", month:"long", day:"numeric" })}
        </h3>
      </div>
      <div className="calendar-grid day-grid">
        {dayHours.map((hourDate) => {
          const hour = hourDate.getHours();
          const matching = dayEntries.filter(entry => new Date(entry.start).getHours() === hour);
          return (
            <div className="hour-row" key={hour}>
              <div className="hour-time">{pad(hour)}:00</div>
              <div className="hour-content" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {matching.length ? matching.map(item => (
                  <div key={item.id} className="event-pill" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{item.title} {item.id.includes('_') && <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>(recurring)</span>}</span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button className="chip" onClick={(e) => { e.stopPropagation(); handleEditEntry(item); }}>Edit</button>
                      {item.id.includes('_') ? (
                        <button className="chip delete-chip" onClick={(e) => { e.stopPropagation(); handleDeleteRecurring(item.id); }}>Delete All</button>
                      ) : (
                        <button className="chip delete-chip" onClick={(e) => { e.stopPropagation(); handleDeleteEntry(item.id); }}>Delete</button>
                      )}
                    </div>
                  </div>
                )) : <span className="day-meta">No scheduled item</span>}
              </div>
              <div className="hour-actions">
                <button className="chip" type="button" onClick={() => openCreate(hourDate, "entry")}>Add</button>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );

  return (
    <div className="calendar-shell" style={{ padding: '0 24px' }}>
      <div className="calendar-topbar" style={{ 
        paddingTop: '16px',
        paddingBottom: '8px',
        marginBottom: '16px',
        position: 'relative'
      }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          position: 'relative',
          minHeight: '60px'
        }}>
          <div className="console-title" style={{ 
            fontSize: '1.1rem', 
            fontWeight: 600,
            color: 'var(--accent)',
            zIndex: 1,
            paddingLeft: '8px'
          }}>
            MAi-RAG Calendar/Planner
          </div>
    
          <h1 style={{ 
            fontSize: '2.5rem', 
            fontWeight: 700, 
            color: 'var(--accent)',
            margin: 0,
            lineHeight: '1.2',
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1,
            whiteSpace: 'nowrap'
          }}>
            {currentYear}
          </h1>
    
          <div style={{ width: '100px' }} /> 
        </div>
      </div>

      <div className="calendar-footer" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '12px',
        padding: '12px 0',
        marginBottom: '16px'
      }}>
        <button className="nav-btn" type="button" onClick={goPrev} aria-label="Previous view range" style={{ 
          background: 'rgba(255,255,255,0.08)', 
          border: '1px solid var(--line)',
          width: '36px', 
          height: '36px',
          borderRadius: '8px',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          fontSize: '1.2rem',
          cursor: 'pointer'
        }}>←</button>
        
        <div className="center-tools" style={{ 
          display: 'flex', 
          gap: '8px',
          flexWrap: 'wrap',
          justifyContent: 'center',
          flex: 1
        }}>
          <button className="chip" type="button" onClick={() => openCreate(selectedDate, "event")} style={{ fontSize: '0.85rem', padding: '6px 12px' }}>+ Create Entry</button>
        </div>
        
        <button className="nav-btn" type="button" onClick={goNext} aria-label="Next view range" style={{ 
          background: 'rgba(255,255,255,0.08)', 
          border: '1px solid var(--line)',
          width: '36px', 
          height: '36px',
          borderRadius: '8px',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          fontSize: '1.2rem',
          cursor: 'pointer'
        }}>→</button>
      </div>

      <div className="calendar-actions" style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: '6px',
        padding: '8px 0',
        marginBottom: '24px'
      }}>
        {(['year', 'month', 'week', 'day'] as const).map((v) => (
          <button 
            key={v}
            className={`chip ${view === v ? 'active' : ''}`} 
            type="button" 
            onClick={() => setView(v)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: view === v ? '2px solid var(--accent)' : '1px solid var(--line)',
              background: view === v ? 'rgba(124, 246, 211, 0.15)' : 'transparent',
              color: view === v ? 'var(--accent)' : 'var(--text)',
              fontWeight: view === v ? 600 : 400,
              fontSize: '0.9rem',
              cursor: 'pointer',
              textTransform: 'capitalize'
            }}
          >
            {v}
          </button>
        ))}
      </div>

      <div className="calendar-stage" style={{ flex: 1, padding: '0 12px' }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0', opacity: 0.6 }}>
            Loading calendar events...
          </div>
        ) : (
          <>
            {view === "year" && yearView}
            {view === "month" && monthView}
            {view === "week" && weekView}
            {view === "day" && dayView}
          </>
        )}
      </div>

      <div className="calendar-footer" style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '12px',
        padding: '16px 0',
        marginTop: '24px',
        borderTop: '1px solid var(--line)'
      }}>
        <button className="nav-btn" type="button" onClick={goPrev} aria-label="Previous view range" style={{ 
          background: 'rgba(255,255,255,0.08)', 
          border: '1px solid var(--line)',
          width: '36px', 
          height: '36px',
          borderRadius: '8px',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          fontSize: '1.2rem',
          cursor: 'pointer'
        }}>←</button>
        
        <div className="center-tools" style={{ 
          display: 'flex', 
          gap: '8px',
          flexWrap: 'wrap',
          justifyContent: 'center',
          flex: 1
        }}>
          <button className="chip" type="button" onClick={() => openCreate(selectedDate, "event")} style={{ fontSize: '0.85rem', padding: '6px 12px' }}>+ Create Entry</button>
        </div>
        
        <button className="nav-btn" type="button" onClick={goNext} aria-label="Next view range" style={{ 
          background: 'rgba(255,255,255,0.08)', 
          border: '1px solid var(--line)',
          width: '36px', 
          height: '36px',
          borderRadius: '8px',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          fontSize: '1.2rem',
          cursor: 'pointer'
        }}>→</button>
      </div>

      <EventModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setCurrentEntry(null); }}
        onSave={handleSaveEntry}
        onUpdate={handleUpdateEntry}
        baseDate={selectedDate}
        mode={modalMode}
        entry={currentEntry}
      />
    </div>
  );
};

export default CalendarPlannerApp;
