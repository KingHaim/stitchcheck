import { useState, useRef } from 'react'

export default function FileUpload({ onFileSelect, onTextSubmit, useLlm, onToggleLlm }) {
  const [dragging, setDragging] = useState(false)
  const [text, setText] = useState('')
  const inputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFileSelect(file)
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) onFileSelect(file)
  }

  return (
    <div className="upload-section">
      <h1 className="upload-title">Analyze Your Pattern</h1>
      <p className="upload-subtitle">
        Upload a knitting pattern or paste it below. We'll validate stitch counts,
        check for errors, and review formatting.
      </p>

      <div className="llm-toggle">
        <label className="toggle-wrapper" onClick={onToggleLlm}>
          <div className={`toggle-track ${useLlm ? 'active' : ''}`}>
            <div className="toggle-thumb" />
          </div>
          <div className="toggle-label">
            <span className="toggle-title">
              {useLlm ? 'AI-Enhanced' : 'Standard'}
            </span>
            <span className="toggle-description">
              {useLlm
                ? 'LLM parses complex instructions + grammar review'
                : 'Deterministic regex parsing only'}
            </span>
          </div>
        </label>
      </div>

      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div className="upload-zone-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div className="upload-zone-text">
          <strong>Click to upload</strong> or drag and drop
        </div>
        <div className="upload-zone-hint">.docx, .pdf, or .txt files</div>
        <input
          ref={inputRef}
          type="file"
          accept=".docx,.pdf,.txt"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
      </div>

      <div className="upload-divider">or paste your pattern</div>

      <div className="paste-area">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={`Sizes: XS (S, M, L, XL)
CO 57 (61, 65, 69, 73) sts
Row 1 (WS): *p1, k1* repeat to end (57 sts)
Row 2 (RS): *k1, p1* repeat to end
Row 3: k2tog, k to end (56 sts)
...`}
        />
        <div className="analyze-btn-wrapper">
          <button
            className="btn btn-primary"
            disabled={!text.trim()}
            onClick={() => onTextSubmit(text)}
          >
            {useLlm && (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z" />
                <circle cx="12" cy="15" r="2" />
              </svg>
            )}
            {!useLlm && (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
            )}
            {useLlm ? 'Analyze with AI' : 'Analyze Pattern'}
          </button>
        </div>
      </div>
    </div>
  )
}
