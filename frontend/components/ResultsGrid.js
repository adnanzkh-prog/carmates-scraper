import CarCard from './CarCard';

export default function ResultsGrid({ results, loading, error }) {
  if (loading) {
    return (
      <div className="results-loading">
        <div className="spinner"></div>
        <p>Searching across marketplaces...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-error">
        <p>⚠️ {error}</p>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="results-empty">
        <p>No cars found. Try adjusting your search or filters.</p>
        <p style={{fontSize: '0.875rem', color: 'var(--text-light)', marginTop: '0.5rem'}}>
          💡 Tip: Add listings manually using the form above
        </p>
      </div>
    );
  }

  // Count by source
  const sourceCounts = results.reduce((acc, car) => {
    acc[car.source] = (acc[car.source] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="results-grid">
      <div className="results-count">
        Found <strong>{results.length}</strong> cars
        
        {/* Source breakdown */}
        <span className="source-breakdown">
          {Object.entries(sourceCounts).map(([source, count]) => (
            <span key={source} className="source-count-tag">
              {count}× {source}
            </span>
          ))}
        </span>
      </div>
      
      <div className="car-grid">
        {results.map((car, index) => (
          <CarCard key={car.id || index} car={car} />
        ))}
      </div>
    </div>
  );
}
