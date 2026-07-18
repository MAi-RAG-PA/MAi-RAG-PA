// frontend/src/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            padding: "2rem",
            margin: "2rem auto",
            backgroundColor: "rgba(255, 100, 100, 0.1)",
            border: "2px solid var(--danger, #ff6464)",
            borderRadius: "0.5rem",
            maxWidth: "600px",
          }}
        >
          <h2
            style={{
              color: "var(--danger, #ff6464)",
              marginBottom: "1rem",
              fontSize: "1.5rem",
            }}
          >
            Something went wrong
          </h2>

          <p
            style={{
              color: "var(--text, #edf2f7)",
              marginBottom: "1rem",
              lineHeight: "1.5",
            }}
          >
            An unexpected error occurred. You can reload the page or try resetting the component.
          </p>

          <details
            style={{
              whiteSpace: "pre-wrap",
              marginTop: "1rem",
              backgroundColor: "rgba(0, 0, 0, 0.2)",
              padding: "1rem",
              borderRadius: "0.25rem",
            }}
          >
            <summary
              style={{
                cursor: "pointer",
                marginBottom: "0.5rem",
                color: "var(--muted, #9aa7b7)",
                fontWeight: "bold",
              }}
            >
              Error details
            </summary>
            <p
              style={{
                color: "var(--text, #edf2f7)",
                fontSize: "0.875rem",
                fontFamily: "monospace",
                marginTop: "0.5rem",
              }}
            >
              {this.state.error?.toString() || "Unknown error"}
            </p>
          </details>

          <div
            style={{
              marginTop: "1.5rem",
              display: "flex",
              gap: "1rem",
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              onClick={this.handleReload}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: "var(--accent, #7cf6d3)",
                color: "var(--bg, #0c0f14)",
                border: "none",
                borderRadius: "0.375rem",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.875rem",
                transition: "all 0.2s ease",
              }}
            >
              Reload Page
            </button>

            <button
              type="button"
              onClick={this.handleReset}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: "transparent",
                color: "var(--text, #edf2f7)",
                border: "1px solid var(--line, rgba(255,255,255,0.12))",
                borderRadius: "0.375rem",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.875rem",
                transition: "all 0.2s ease",
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
