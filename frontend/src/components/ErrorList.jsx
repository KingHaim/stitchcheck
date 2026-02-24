export default function ErrorList({ items, type, emptyMessage }) {
  if (!items?.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          {type === 'error' ? (
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          ) : (
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          )}
        </div>
        <div className="empty-state-text">{emptyMessage}</div>
      </div>
    )
  }

  return (
    <div className="error-list">
      {items.map((item, i) => (
        <div key={i} className={`error-card ${type}`}>
          <div className="error-card-icon">
            {type === 'error' ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            ) : type === 'warning' ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            )}
          </div>
          <div className="error-card-content">
            <div className="error-card-header">
              {item.row_label && (
                <span className="error-card-location">{item.row_label}</span>
              )}
              {item.line && (
                <span className="error-card-location">Line {item.line}</span>
              )}
              {item.size && (
                <span className="error-card-size">{item.size}</span>
              )}
              {item.severity && !item.size && (
                <span className="error-card-size">{item.severity}</span>
              )}
            </div>
            <div className="error-card-message">{item.message}</div>
            {item.raw_text && (
              <div className="error-card-source">{item.raw_text}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
