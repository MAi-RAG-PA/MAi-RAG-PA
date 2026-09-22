// frontend/src/components/chat/RolesModal.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';

export interface Role {
  id: string;
  name: string;
  system_prompt: string;
  collection_name: string | null;
  citations_enabled: boolean;
  model_override: string | null;
  created_at: string;
  updated_at: string;
}

interface RolesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRolesChanged: () => void;
  showToast: (msg: string) => void;
}

const emptyForm = {
  name: '',
  system_prompt: '',
  collection_name: '' as string,
  citations_enabled: true,
  model_override: '' as string,
};

const RolesModal: React.FC<RolesModalProps> = ({ isOpen, onClose, onRolesChanged, showToast }) => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [collections, setCollections] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);
  const [form, setForm] = useState({ ...emptyForm });

  const isNewRole = editing === null && form.name === '' && form.system_prompt === '';

  // Fetch roles + collections + models whenever the modal opens
  useEffect(() => {
    if (!isOpen) return;

    const load = async () => {
      setIsLoading(true);
      try {
        const [rolesRes, collRes, modelsRes] = await Promise.all([
          apiClient.get('/api/v1/roles'),
          apiClient.get('/api/memory/qdrant/collections'),
          apiClient.get('/api/ollama/models'),
        ]);
        setRoles(rolesRes.data || []);
        setCollections(collRes.data?.collections || []);
        const allModels: string[] = modelsRes.data?.models || [];
        const embeddingPatterns = ['embed', 'nomic-embed', 'mxbai-embed', 'all-minilm', 'bge-', 'e5-'];
        setModels(allModels.filter(m => !embeddingPatterns.some(p => m.toLowerCase().includes(p))));
      } catch (err: any) {
        console.error('Failed to load roles data:', err);
        showToast(`Failed to load roles: ${err.response?.data?.detail || err.message}`);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [isOpen]);

  const resetForm = () => {
    setEditing(null);
    setForm({ ...emptyForm });
  };

  const beginEdit = (role: Role) => {
    setEditing(role);
    setForm({
      name: role.name,
      system_prompt: role.system_prompt,
      collection_name: role.collection_name || '',
      citations_enabled: role.citations_enabled,
      model_override: role.model_override || '',
    });
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.system_prompt.trim()) {
      showToast('Name and System Prompt are required');
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        system_prompt: form.system_prompt.trim(),
        collection_name: form.collection_name || null,
        citations_enabled: form.citations_enabled,
        model_override: form.model_override || null,
      };

      if (editing) {
        await apiClient.put(`/api/v1/roles/${editing.id}`, payload);
        showToast(`Role "${payload.name}" updated`);
      } else {
        await apiClient.post('/api/v1/roles', payload);
        showToast(`Role "${payload.name}" created`);
      }

      // Refresh list + notify parent
      const res = await apiClient.get('/api/v1/roles');
      setRoles(res.data || []);
      resetForm();
      onRolesChanged();
    } catch (err: any) {
      console.error('Save failed:', err);
      showToast(`Save failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (role: Role) => {
    if (role.id === 'default') {
      showToast('The Default role cannot be deleted');
      return;
    }
    if (!window.confirm(`Delete role "${role.name}"? This cannot be undone.`)) return;

    try {
      await apiClient.delete(`/api/v1/roles/${role.id}`);
      showToast(`Role "${role.name}" deleted`);
      const res = await apiClient.get('/api/v1/roles');
      setRoles(res.data || []);
      if (editing?.id === role.id) resetForm();
      onRolesChanged();
    } catch (err: any) {
      console.error('Delete failed:', err);
      showToast(`Delete failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Manage Roles"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.65)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg-secondary, #161b22)',
          border: '1px solid var(--line)',
          borderRadius: '12px',
          width: 'min(920px, 100%)',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid var(--line)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ margin: 0, color: 'var(--accent)', fontSize: '1.1rem', fontWeight: 600 }}>
            Manage Roles
          </h3>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text)',
              fontSize: '1.5rem',
              lineHeight: 1,
              cursor: 'pointer',
              padding: '4px 10px',
            }}
          >
            ×
          </button>
        </div>

        {/* Body: two-column layout on wide screens */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(220px, 1fr) minmax(320px, 2fr)',
            gap: '16px',
            padding: '16px 20px',
            overflowY: 'auto',
            flex: 1,
          }}
        >
          {/* Column 1: Role list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                ROLES ({roles.length})
              </span>
              <button
                onClick={resetForm}
                className="chip"
                style={{
                  padding: '3px 10px',
                  fontSize: '0.75rem',
                  border: '1px solid var(--accent)',
                  color: 'var(--accent)',
                  background: 'none',
                  cursor: 'pointer',
                  borderRadius: '6px',
                }}
              >
                + New
              </button>
            </div>

            {isLoading ? (
              <div style={{ padding: '12px', opacity: 0.6, fontSize: '0.85rem' }}>Loading…</div>
            ) : roles.length === 0 ? (
              <div style={{ padding: '12px', opacity: 0.6, fontSize: '0.85rem' }}>No roles yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {roles.map(r => (
                  <div
                    key={r.id}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: editing?.id === r.id ? '1px solid var(--accent)' : '1px solid var(--line)',
                      background: editing?.id === r.id ? 'rgba(124,246,211,0.08)' : 'rgba(255,255,255,0.02)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {r.name}
                        {r.id === 'default' && (
                          <span style={{ marginLeft: '6px', fontSize: '0.65rem', opacity: 0.6 }}>(system)</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.7rem', opacity: 0.55 }}>
                        {r.collection_name ? `📚 ${r.collection_name}` : 'no collection'}
                        {r.citations_enabled ? ' · cites' : ' · no cites'}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                      <button
                        onClick={() => beginEdit(r)}
                        title="Edit"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text)',
                          cursor: 'pointer',
                          padding: '2px 6px',
                          fontSize: '0.9rem',
                          opacity: 0.7,
                        }}
                      >
                        ✎
                      </button>
                      {r.id !== 'default' && (
                        <button
                          onClick={() => handleDelete(r)}
                          title="Delete"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#ef4444',
                            cursor: 'pointer',
                            padding: '2px 6px',
                            fontSize: '0.9rem',
                            opacity: 0.7,
                          }}
                        >
                          ×
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Column 2: Editor form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              {editing ? `EDITING: ${editing.name}` : 'NEW ROLE'}
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px', opacity: 0.7 }}>
                Name
              </label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Bookeeping Accountant, Tax Consultant, Market Analyst, Research Assistant"
                style={inputStyle}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px', opacity: 0.7 }}>
                LTM Collection (optional)
              </label>
              <select
                value={form.collection_name}
                onChange={e => setForm({ ...form, collection_name: e.target.value })}
                style={inputStyle}
              >
                <option value="">— No LTM knowledgebase (chat only) —</option>
                {collections.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px', opacity: 0.7 }}>
                Model Override (optional)
              </label>
              <select
                value={form.model_override}
                onChange={e => setForm({ ...form, model_override: e.target.value })}
                style={inputStyle}
              >
                <option value="">— Use current model —</option>
                {models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form.citations_enabled}
                onChange={e => setForm({ ...form, citations_enabled: e.target.checked })}
              />
              Enable citations / References section
            </label>

            <div>
              <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px', opacity: 0.7 }}>
                System Prompt
              </label>
              <textarea
                value={form.system_prompt}
                onChange={e => setForm({ ...form, system_prompt: e.target.value })}
                rows={12}
                placeholder="You are an expert in…"
                style={{ ...inputStyle, fontFamily: 'monospace', fontSize: '0.8rem', resize: 'vertical', minHeight: '180px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              {editing && (
                <button
                  onClick={resetForm}
                  className="chip"
                  style={{ padding: '6px 16px', borderRadius: '6px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
              )}
              <button
                onClick={handleSave}
                disabled={isSaving || !form.name.trim() || !form.system_prompt.trim()}
                className="btn"
                style={{
                  padding: '6px 20px',
                  borderRadius: '6px',
                  cursor: isSaving ? 'wait' : 'pointer',
                  opacity: isSaving ? 0.6 : 1,
                }}
              >
                {isSaving ? 'Saving…' : editing ? 'Save Changes' : 'Create Role'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: '6px',
  border: '1px solid var(--line)',
  background: 'rgba(255,255,255,0.04)',
  color: 'var(--text)',
  fontSize: '0.9rem',
  outline: 'none',
  fontFamily: 'inherit',
};

export default RolesModal;
