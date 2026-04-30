import CarCard from './CarCard';

export default function ResultsGrid({ results, loading, error, sources }) {
  if (loading) {
    return (
      <div className="results-loading">
        <div className="spinner"></div>
        <p>Searching real marketplaces...</p>
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
        <p>No real listings found.</p>
        <div className="empty-help">
          <p>💡 To get real data:</p>
          <ol>
            <li>Add <code>EBAY_APP_ID</code> + <code>EBAY_CERT_ID</code> to Railway for eBay listings</li>
            <li>Add <code>APIFY_API_TOKEN</code> to Railway for Facebook Marketplace</li>
            <li>Or use "Add Listing Manually" to paste URLs directly</li>
          </ol>
        </div>
      </div>
    );
  }

  return (
    <div className="results-grid">
      <div className="car-grid">
        {results.map((car, index) => (
          <CarCard key={car.id || index} car={car} />
        ))}
      </div>
    </div>
  );
}
