import { useState } from 'react'
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

  const badgeCounts = {
    errors: data.summary?.stitch_count_errors || 0,
    warnings: (data.summary?.repetition_mismatches || 0) + (data.summary?.consistency_warnings || 0),
    grammar: data.summary?.grammar_issues || 0,
    format: data.summary?.format_warnings || 0,
  }

  return (
    <div>
      <div className="results-header">
        <h2 className="results-title">Analysis Results</h2>
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
        <PatternView sections={data.sections} selectedSize={selectedSize} />
      )}
      {activeTab === 'errors' && (
        <ErrorList items={data.errors} type="error" emptyMessage="No stitch count errors found" />
      )}
      {activeTab === 'warnings' && (
        <ErrorList items={data.warnings} type="warning" emptyMessage="No warnings found" />
      )}
      {activeTab === 'grammar' && (
        <ErrorList items={data.grammar_issues} type="info" emptyMessage="No grammar issues found" />
      )}
      {activeTab === 'format' && (
        <ErrorList items={data.format_issues} type="info" emptyMessage="No format issues found" />
      )}
    </div>
  )
}
