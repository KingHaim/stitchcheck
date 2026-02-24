export default function SizeSelector({ sizes, selected, onSelect, castOnCounts }) {
  return (
    <div className="size-selector">
      <span className="size-label">Size:</span>
      <div className="size-pills">
        {sizes.map((size) => (
          <button
            key={size}
            className={`size-pill ${selected === size ? 'active' : ''}`}
            onClick={() => onSelect(size)}
          >
            {size}
            {castOnCounts?.[size] != null && (
              <span style={{ opacity: 0.7, fontSize: 11, marginLeft: 4 }}>
                ({castOnCounts[size]} sts)
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
