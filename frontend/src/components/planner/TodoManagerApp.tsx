// frontend/src/components/planner/TodoManagerApp.tsx
import React, { useState, useMemo, useEffect, useCallback } from "react";
import apiClient from "../../api/client";

interface TodoItem {
  id: string;
  title: string;
  description?: string;
  priority: "low" | "medium" | "high";
  completed: boolean;
  due_date?: string;
  order_index?: number;
}

interface TodoManagerAppProps {
  showToast?: (msg: string) => void;
}

const TodoManagerApp: React.FC<TodoManagerAppProps> = ({ showToast }) => {
  const [items, setItems] = useState<TodoItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  const fetchTodos = useCallback(async () => {
    try {
      const res = await apiClient.get("/api/memory/sqlite/todos?limit=50");
      const todos: TodoItem[] = res.data.todos || [];
      const sorted = [...todos].sort((a, b) => (a.order_index ?? 999) - (b.order_index ?? 999));
      setItems(sorted);
    } catch (err) {
      console.warn("Failed to fetch todos:", err);
    }
  }, []);

  useEffect(() => {
    void fetchTodos();
  }, [fetchTodos]);

  const addItem = async () => {
    if (!inputText.trim()) return;

    setLoading(true);
    const newItem: TodoItem = {
      id: crypto.randomUUID(),
      title: inputText.trim(),
      priority: "medium",
      completed: false,
      order_index: items.length,
    };

    try {
      await apiClient.post("/api/memory/sqlite/todos", {
        id: newItem.id,
        title: newItem.title,
        priority: newItem.priority,
        completed: newItem.completed,
        order_index: newItem.order_index,
      });
      setInputText("");
      await fetchTodos();
      showToast?.("Task added");
    } catch (err) {
      console.error("Failed to save todo:", err);
      showToast?.("Failed to add task");
    } finally {
      setLoading(false);
    }
  };

  const deleteSelected = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected task(s)?`)) return;

    setLoading(true);
    const selectedCount = selectedIds.size;

    try {
      await Promise.all(
        Array.from(selectedIds).map((id) => apiClient.delete(`/api/memory/sqlite/todos/${id}`))
      );

      setSelectedIds(new Set());
      await fetchTodos();
      showToast?.(`Deleted ${selectedCount} task(s)`);
    } catch (err: any) {
      console.error("Failed to delete todos:", err);
      showToast?.(`Failed to delete: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const singleSelectedIndex = useMemo(() => {
    if (selectedIds.size !== 1) return -1;
    const selectedId = Array.from(selectedIds)[0];
    return items.findIndex((item) => item.id === selectedId);
  }, [selectedIds, items]);

  const moveItem = async (direction: "up" | "down") => {
    const index = singleSelectedIndex;
    if (index === -1) return;

    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= items.length) return;

    const newItems = [...items];
    const [movedItem] = newItems.splice(index, 1);
    newItems.splice(newIndex, 0, movedItem);

    const updated = newItems.map((item, idx) => ({ ...item, order_index: idx }));
    setItems(updated);

    setLoading(true);
    try {
      const swappedItems = [updated[index], updated[newIndex]];
      await Promise.all(
        swappedItems.map((item) =>
          apiClient.post("/api/memory/sqlite/todos", {
            id: item.id,
            title: item.title,
            priority: item.priority,
            completed: item.completed,
            order_index: item.order_index,
          })
        )
      );
      showToast?.(`Moved item ${direction}`);
    } catch (err) {
      console.error("Failed to sync reorder:", err);
      await fetchTodos();
    } finally {
      setLoading(false);
    }
  };

  const toggleComplete = async (id: string) => {
    const item = items.find((i) => i.id === id);
    if (!item) return;

    try {
      await apiClient.post("/api/memory/sqlite/todos", {
        id: item.id,
        title: item.title,
        priority: item.priority,
        completed: !item.completed,
        order_index: item.order_index,
      });
      await fetchTodos();
    } catch (err) {
      console.error("Failed to toggle complete:", err);
    }
  };

  const isSelected = (id: string) => selectedIds.has(id);

  return (
    <section
      className="panel reveal delay-2 glow-panel"
      role="region"
      aria-label="To Do List Manager"
      style={{
        flex: "1 1 45%",
        minWidth: 300,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        height: 425,
      }}
    >
      <div
        className="panel-inner"
        style={{
          padding: "22px 22px 16px",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minHeight: 0,
          boxSizing: "border-box",
        }}
      >
        <div
          className="console-title"
          style={{
            color: "var(--accent)",
            fontSize: "1.3rem",
            fontWeight: "bold",
            marginBottom: "12px",
          }}
        >
          To Do List
        </div>

        <ul
          role="list"
          aria-label="List of todo items"
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            flexGrow: 1,
            overflowY: "auto",
            minHeight: 0,
          }}
        >
          {items.length === 0 ? (
            <li role="status" aria-live="polite" style={{ textAlign: "center", padding: "20px 0", opacity: 0.6 }}>
              No tasks saved to The To Do List yet
            </li>
          ) : (
            items.map((item) => (
              <li
                key={item.id}
                role="listitem"
                aria-label={`${item.title} ${item.completed ? "completed" : "pending"}`}
                tabIndex={0}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "8px",
                  background: isSelected(item.id)
                    ? "rgba(124, 246, 211, 0.1)"
                    : item.completed
                      ? "rgba(47, 133, 90, 0.2)"
                      : "rgba(255,255,255,0.05)",
                  borderRadius: 6,
                  marginBottom: 6,
                  cursor: "pointer",
                  wordBreak: "break-word",
                  transition: "background 0.2s",
                }}
              >
                <input
                  type="checkbox"
                  checked={isSelected(item.id)}
                  onChange={() => toggleSelect(item.id)}
                  style={{ marginRight: 12, cursor: "pointer", accentColor: "var(--accent)" }}
                  aria-label={`Select ${item.title} for reordering or deletion`}
                  onClick={(e) => e.stopPropagation()}
                />

                <span
                  onClick={() => toggleComplete(item.id)}
                  role="button"
                  tabIndex={0}
                  aria-label={item.completed ? `Mark ${item.title} as incomplete` : `Mark ${item.title} as complete`}
                  style={{
                    flex: 1,
                    textDecoration: item.completed ? "line-through" : "none",
                    opacity: item.completed ? 0.6 : 1,
                    userSelect: "none",
                  }}
                >
                  {item.title}
                </span>
              </li>
            ))
          )}
        </ul>

        <div
          style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}
          role="group"
          aria-label="Task input and controls"
        >
          <div className="field">
            <label htmlFor="task-input" style={{ display: "none" }}>
              New Task
            </label>
            <input
              id="task-input"
              type="text"
              placeholder="Add items here. Check boxes and use Up & Down to change order, or to delete items."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void addItem();
              }}
              aria-label="New task text"
              aria-describedby="input-help"
              style={{
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "var(--text)",
                fontSize: "0.9rem",
              }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }} role="group" aria-label="Task management buttons">
            <div style={{ display: "flex", gap: 8 }} role="group" aria-label="Reorder controls">
              <button
                className="btn"
                onClick={() => void moveItem("up")}
                disabled={singleSelectedIndex <= 0 || loading}
                aria-label="Move selected task up"
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.08)",
                  color: "var(--text)",
                  cursor: singleSelectedIndex <= 0 || loading ? "not-allowed" : "pointer",
                }}
              >
                Up
              </button>
              <button
                className="btn"
                onClick={() => void moveItem("down")}
                disabled={singleSelectedIndex === -1 || singleSelectedIndex === items.length - 1 || loading}
                aria-label="Move selected task down"
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.08)",
                  color: "var(--text)",
                  cursor:
                    singleSelectedIndex === -1 || singleSelectedIndex === items.length - 1 || loading
                      ? "not-allowed"
                      : "pointer",
                }}
              >
                Down
              </button>
            </div>

            <div style={{ display: "flex", gap: 8 }} role="group" aria-label="Action buttons">
              <button
                className="btn"
                onClick={() => void addItem()}
                disabled={!inputText.trim() || loading}
                aria-label="Add new task"
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  background: !inputText.trim() || loading ? "rgba(255,255,255,0.08)" : "var(--accent)",
                  color: !inputText.trim() || loading ? "#666" : "#000",
                  cursor: !inputText.trim() || loading ? "not-allowed" : "pointer",
                }}
              >
                {loading ? "..." : "Add"}
              </button>
              <button
                className="btn"
                onClick={() => void deleteSelected()}
                disabled={selectedIds.size === 0 || loading}
                aria-label={`Delete ${selectedIds.size} selected task(s)`}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  background: selectedIds.size === 0 || loading ? "rgba(255,255,255,0.08)" : "rgba(239, 68, 68, 0.2)",
                  color: selectedIds.size === 0 || loading ? "#666" : "#ef4444",
                  cursor: selectedIds.size === 0 || loading ? "not-allowed" : "pointer",
                }}
              >
                Delete
              </button>
            </div>
          </div>

          <div id="input-help" style={{ fontSize: "0.75rem", opacity: 0.6, marginTop: "4px" }} role="note" aria-label="Usage instructions">
            Check boxes and use Up &amp; Down to change order, or to delete items.
          </div>
        </div>
      </div>
    </section>
  );
};

export default TodoManagerApp;
