// frontend/src/components/VirtualizedDocumentList.tsx
import React, { useCallback, useMemo } from "react";
import { FixedSizeList as List, ListChildComponentProps } from "react-window";

interface Document {
  id: string;
  title: string;
  content: string;
  created_at: string;
}

interface VirtualizedDocumentListProps {
  documents: Document[];
  onDelete: (id: string) => void;
  height?: number;
}

const ITEM_SIZE = 96;

const VirtualizedDocumentList: React.FC<VirtualizedDocumentListProps> = ({
  documents,
  onDelete,
  height = 400,
}) => {
  const formatDate = useMemo(
    () => (value: string) => {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? "Unknown date" : date.toLocaleDateString();
    },
    []
  );

  const Row = useCallback(
    ({ index, style }: ListChildComponentProps) => {
      const doc = documents[index];

      return (
        <div style={{ ...style, padding: "8px" }}>
          <div
            role="listitem"
            aria-label={`Document: ${doc.title}`}
            tabIndex={0}
            style={{
              padding: "12px",
              background: "rgba(255,255,255,0.03)",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: "4px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {doc.title}
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
                {formatDate(doc.created_at)}
              </div>
            </div>

            <button
              type="button"
              onClick={() => onDelete(doc.id)}
              aria-label={`Delete ${doc.title}`}
              style={{
                padding: "6px 12px",
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "6px",
                color: "#ef4444",
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              Delete
            </button>
          </div>
        </div>
      );
    },
    [documents, formatDate, onDelete]
  );

  if (documents.length === 0) {
    return (
      <div
        style={{ padding: "20px", textAlign: "center", color: "var(--muted)" }}
        role="status"
        aria-live="polite"
      >
        No documents found
      </div>
    );
  }

  return (
    <List
      height={height}
      itemCount={documents.length}
      itemSize={ITEM_SIZE}
      width="100%"
      role="list"
      aria-label="List of documents"
      itemKey={(index) => documents[index].id}
    >
      {Row}
    </List>
  );
};

export default VirtualizedDocumentList;
