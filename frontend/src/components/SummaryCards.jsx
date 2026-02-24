export default function SummaryCards({ summary }) {
  if (!summary) return null

  const cards = [
    {
      value: summary.total_rows_parsed,
      label: 'Rows Parsed',
      className: 'success',
    },
    {
      value: summary.total_sizes,
      label: 'Sizes',
      className: 'success',
    },
    {
      value: summary.stitch_count_errors,
      label: 'Stitch Errors',
      className: summary.stitch_count_errors > 0 ? 'error' : 'success',
    },
    {
      value: summary.repetition_mismatches,
      label: 'Repeat Issues',
      className: summary.repetition_mismatches > 0 ? 'warning' : 'success',
    },
    {
      value: summary.grammar_issues,
      label: 'Grammar Issues',
      className: summary.grammar_issues > 0 ? 'info' : 'success',
    },
    {
      value: summary.format_warnings,
      label: 'Format Warnings',
      className: summary.format_warnings > 0 ? 'info' : 'success',
    },
  ]

  return (
    <div className="summary-grid">
      {cards.map((card, i) => (
        <div key={i} className={`summary-card ${card.className}`}>
          <div className="summary-card-value">{card.value}</div>
          <div className="summary-card-label">{card.label}</div>
        </div>
      ))}
    </div>
  )
}
