import React from "react";

const ContextPanel = ({ conversationId, context }) => {
  return (
    <aside className="context-panel">
      <h2>Conversation State</h2>
      <div className="context-section">
        <div className="label">Conversation ID</div>
        <div className="value mono">{conversationId}</div>
      </div>
      {context ? (
        <>
          <div className="context-section">
            <div className="label">Detected Intent</div>
            <div className="value mono">{context.intent || "—"}</div>
          </div>
          <div className="context-section">
            <div className="label">Slots</div>
            <pre className="value mono small">
              {JSON.stringify(context.slots, null, 2)}
            </pre>
          </div>
          <div className="context-section">
            <div className="label">History (latest first)</div>
            <div className="history-list">
              {[...(context.history || [])]
                .slice()
                .reverse()
                .map((m, idx) => (
                  <div key={idx} className="history-item">
                    <span className="tag">{m.role}</span>
                    <span className="text">{m.content}</span>
                  </div>
                ))}
            </div>
          </div>
        </>
      ) : (
        <div className="context-section">
          <div className="value">Loading context…</div>
        </div>
      )}
    </aside>
  );
};

export default ContextPanel;

