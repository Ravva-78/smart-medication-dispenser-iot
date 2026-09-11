/**
 * ErrorBoundary — Sprint 4 shared component
 *
 * Catches uncaught render errors in the subtree and shows a
 * recovery UI instead of a blank / crashed screen.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <SomeComponent />
 *   </ErrorBoundary>
 */
import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    /* In production this would send to a logging service */
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    /* Reload the page as the safest recovery for an in-memory app */
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", flexDirection: "column", gap: 20,
        background: "var(--bg-base)", fontFamily: "var(--font-body)",
        padding: 32,
      }}>
        {/* Icon */}
        <div style={{
          width: 64, height: 64, borderRadius: "50%",
          background: "rgba(231,76,60,0.10)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="#E74C3C" strokeWidth="1.6"
            width="28" height="28">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0
              1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>

        {/* Message */}
        <div style={{ textAlign: "center", maxWidth: 420 }}>
          <div style={{
            fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 800,
            color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: 8,
          }}>
            Something went wrong
          </div>
          <p style={{
            margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6,
          }}>
            An unexpected error occurred in this component.
            {" "}Click below to reload the application.
          </p>
          {this.state.error && (
            <p style={{
              margin: "12px 0 0", fontSize: 11, color: "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}>
              {this.state.error.message}
            </p>
          )}
        </div>

        <button
          onClick={this.handleReset}
          style={{
            padding: "10px 28px", borderRadius: "var(--radius-sm)",
            border: "none", background: "var(--cyan)",
            fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
            color: "#fff", cursor: "pointer",
            boxShadow: "0 2px 10px rgba(58,141,255,0.25)",
          }}
        >
          Reload Application
        </button>
      </div>
    );
  }
}
