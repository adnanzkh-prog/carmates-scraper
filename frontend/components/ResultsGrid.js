export default function ResultsGrid({ results, loading, error }) {
  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!results || results.length === 0) return <div className="no-results">No cars found.</div>;

  return (
    <div className="results-grid">
      {results.map((car, index) => (
        <div key={index} className="car-card">
          <h3>{car.title || 'Unknown Car'}</h3>
          <p>Price: {car.price || 'N/A'}</p>
          <p>Location: {car.location || 'N/A'}</p>
        </div>
      ))}
    </div>
  );
}
