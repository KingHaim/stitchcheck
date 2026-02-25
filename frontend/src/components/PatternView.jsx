import { useEffect, useRef } from 'react'

export default function PatternView({ sections, selectedSize, scrollToRowKey, onScrolled }) {
  const highlightTimeoutRef = useRef(null)

  useEffect(() => {
    if (!scrollToRowKey || scrollToRowKey.sectionIndex == null || scrollToRowKey.rowIndex == null) return
    const id = `pattern-row-${scrollToRowKey.sectionIndex}-${scrollToRowKey.rowIndex}`
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('pattern-row-highlight')
      if (highlightTimeoutRef.current) clearTimeout(highlightTimeoutRef.current)
      highlightTimeoutRef.current = setTimeout(() => {
        el.classList.remove('pattern-row-highlight')
        highlightTimeoutRef.current = null
        onScrolled?.()
      }, 2500)
    } else {
      onScrolled?.()
    }
  }, [scrollToRowKey, onScrolled])

  if (!sections?.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <div className="empty-state-text">No pattern rows parsed</div>
      </div>
    )
  }

  return (
    <div>
      {sections.map((section, si) => (
        <div key={si}>
          {section.name && section.name !== 'Main' && (
            <div className="section-header">{section.name}</div>
          )}
          <div className="pattern-rows">
            {section.rows.map((row, ri) => {
              const sizeErrors = row.errors?.filter((e) =>
                !selectedSize || e.includes(`[${selectedSize}]`)
              ) || []
              const sizeWarnings = row.warnings?.filter((w) =>
                !selectedSize || w.includes(`[${selectedSize}]`)
              ) || []
              const hasError = sizeErrors.length > 0
              const hasWarning = !hasError && sizeWarnings.length > 0

              const calcSts = row.calculated_sts?.[selectedSize]
              const expSts = row.expected_sts?.[selectedSize]
              // Only show as mismatch (red) when we actually reported an error — not when backend suppressed a stale "expected"
              const mismatch = hasError && expSts != null && calcSts != null && expSts !== calcSts

              return (
                <div
                  key={ri}
                  id={`pattern-row-${si}-${ri}`}
                  className={`pattern-row ${hasError ? 'has-error' : ''} ${hasWarning ? 'has-warning' : ''}`}
                >
                  <div className="row-number">
                    {row.number != null ? (
                      <>
                        {row.is_round ? 'Rnd' : 'Row'} {row.number}
                        {row.side && <div className="row-side">{row.side}</div>}
                      </>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </div>

                  <div className="row-text">{row.raw_text}</div>

                  <div className={`row-sts ${mismatch ? 'mismatch' : calcSts != null ? 'match' : ''}`}>
                    {calcSts != null && (
                      <>
                        {calcSts} sts
                        {mismatch && expSts != null && (
                          <div style={{ fontSize: 11, fontWeight: 400 }}>
                            exp: {expSts}
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {(sizeErrors.length > 0 || sizeWarnings.length > 0) && (
                    <div className="row-errors">
                      {sizeErrors.map((e, ei) => (
                        <div key={ei} className="row-error-item">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 2 }}>
                            <circle cx="12" cy="12" r="10" />
                            <line x1="15" y1="9" x2="9" y2="15" />
                            <line x1="9" y1="9" x2="15" y2="15" />
                          </svg>
                          {e}
                        </div>
                      ))}
                      {sizeWarnings.map((w, wi) => (
                        <div key={wi} className="row-warning-item">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 2 }}>
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                            <line x1="12" y1="9" x2="12" y2="13" />
                            <line x1="12" y1="17" x2="12.01" y2="17" />
                          </svg>
                          {w}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
