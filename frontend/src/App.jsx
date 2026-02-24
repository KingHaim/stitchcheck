import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ResultsView from './components/ResultsView'

const API_BASE = ''

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const analyzeFile = async (file) => {
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: form })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.status}`)
      }
      setResults(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const analyzeText = async (text) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/analyze-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.status}`)
      }
      setResults(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setResults(null)
    setError(null)
  }

  return (
    <>
      <header className="app-header">
        <div className="app-logo">
          <div className="logo-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <span>StitchCheck</span>
        </div>
        <span className="app-tagline">Grammarly for knitting patterns — with real stitch math</span>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-card error" style={{ marginBottom: 20 }}>
            <div className="error-card-icon">!</div>
            <div className="error-card-content">
              <div className="error-card-message">{error}</div>
            </div>
          </div>
        )}

        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <div className="loading-text">Analyzing your pattern…</div>
          </div>
        )}

        {!loading && !results && (
          <FileUpload onFileSelect={analyzeFile} onTextSubmit={analyzeText} />
        )}

        {!loading && results && (
          <ResultsView data={results} onReset={reset} />
        )}
      </main>
    </>
  )
}

export default App
