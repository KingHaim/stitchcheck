import { useState, useMemo, useCallback } from 'react'
import SummaryCards from './SummaryCards'
import SizeSelector from './SizeSelector'
import PatternView from './PatternView'
import ErrorList from './ErrorList'

const TABS = [
  { id: 'pattern', label: 'Pattern View' },
  { id: 'errors', label: 'Stitch Errors' },
  { id: 'warnings', label: 'Warnings' },
  { id: 'grammar', label: 'Grammar' },
  { id: 'format', label: 'Format' },
]

export default function ResultsView({ data, onReset }) {
  const [activeTab, setActiveTab] = useState('pattern')
  const [selectedSize, setSelectedSize] = useState(data.sizes?.[0] || '')
  const [scrollToRowKey, setScrollToRowKey] = useState(null)

  const { rowLocationByNumber, rowLocationByRawText } = useMemo(() => {
    const byNumber = {}
    const byRawText = {}
    data.sections?.forEach((section, si) => {
      section.rows?.forEach((row, ri) => {
        if (row.number != null && byNumber[row.number] == null) {
          byNumber[row.number] = { sectionIndex: si, rowIndex: ri }
        }
        const key = (row.raw_text || '').trim()
        if (key && byRawText[key] == null) {
          byRawText[key] = { sectionIndex: si, rowIndex: ri }
        }
      })
    })
    return { rowLocationByNumber: byNumber, rowLocationByRawText: byRawText }
  }, [data.sections])

  const handleGoToLocation = useCallback((item) => {
    let key = null
    if (item.row != null && rowLocationByNumber[item.row] != null) {
      key = rowLocationByNumber[item.row]
    } else if (item.raw_text != null) {
      const trimmed = (item.raw_text || '').trim()
      if (trimmed && rowLocationByRawText[trimmed] != null) {
        key = rowLocationByRawText[trimmed]
      }
    }
    if (key) {
      setScrollToRowKey(key)
      setActiveTab('pattern')
    }
  }, [rowLocationByNumber, rowLocationByRawText])

  const clearScrollTarget = useCallback(() => setScrollToRowKey(null), [])

  const badgeCounts = {
    errors: data.summary?.stitch_count_errors || 0,
    warnings: (data.summary?.repetition_mismatches || 0) + (data.summary?.consistency_warnings || 0),
    grammar: data.summary?.grammar_issues || 0,
    format: data.summary?.format_warnings || 0,
  }

  return (
    <div>
      <div className="results-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 className="results-title">Analysis Results</h2>
          {data.llm_enhanced && (
            <span className="llm-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              AI-Enhanced
            </span>
          )}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onReset}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
          New Analysis
        </button>
      </div>

      <SummaryCards summary={data.summary} />

      {data.sizes?.length > 1 && (
        <SizeSelector
          sizes={data.sizes}
          selected={selectedSize}
          onSelect={setSelectedSize}
          castOnCounts={data.cast_on_counts}
        />
      )}

      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {badgeCounts[tab.id] > 0 && (
              <span className={`tab-badge ${tab.id === 'errors' ? 'error' : tab.id === 'warnings' ? 'warning' : 'info'}`}>
                {badgeCounts[tab.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'pattern' && (
        <PatternView
          sections={data.sections}
          selectedSize={selectedSize}
          scrollToRowKey={scrollToRowKey}
          onScrolled={clearScrollTarget}
        />
      )}
      {activeTab === 'errors' && (
        <ErrorList
          items={data.errors}
          type="error"
          emptyMessage="No stitch count errors found"
          onGoToLocation={handleGoToLocation}
        />
      )}
      {activeTab === 'warnings' && (
        <ErrorList
          items={data.warnings}
          type="warning"
          emptyMessage="No warnings found"
          onGoToLocation={handleGoToLocation}
        />
      )}
      {activeTab === 'grammar' && (
        <ErrorList
          items={data.grammar_issues}
          type="info"
          emptyMessage="No grammar issues found"
          onGoToLocation={handleGoToLocation}
        />
      )}
      {activeTab === 'format' && (
        <ErrorList
          items={data.format_issues}
          type="info"
          emptyMessage="No format issues found"
          onGoToLocation={handleGoToLocation}
        />
      )}
    </div>
  )
}
