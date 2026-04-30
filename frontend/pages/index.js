import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('sydney');
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => r.ok ? setApiStatus('connected') : setApiStatus('error'))
      .catch(() => setApiStatus('error'));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    
    try {
      const params = new URLSearchParams({ q: query, location, limit: '10' });
      const res = await fetch(`${API_URL}/search?${params}`);
      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      console.error(err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Head>
        <title>CarMates - Australian Car Search</title>
      </Head>

      {/* Header */}
      <header style={{ background: '#0f172a', color: 'white', padding: '1.5rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🚗 CarMates
          </h1>
          <p style={{ margin: '0.5rem 0 0', opacity: 0.7, fontSize: '0.875rem' }}>
            Find your perfect car across Australia
          </p>
          <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', opacity: 0.6 }}>
            API: {apiStatus === 'connected' ? '🟢 Connected' : apiStatus === 'checking' ? '🟡 Checking...' : '🔴 Error'}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
        {/* Search Box */}
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search Toyota, BMW, Honda..."
              style={{
                flex: 1,
                minWidth: '250px',
                padding: '0.75rem 1rem',
                border: '2px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '1rem',
                outline: 'none'
              }}
            />
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              style={{
                padding: '0.75rem 1rem',
                border: '2px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '1rem',
                background: 'white'
              }}
            >
              <option value="sydney">Sydney</option>
              <option value="melbourne">Melbourne</option>
              <option value="brisbane">Brisbane</option>
              <option value="perth">Perth</option>
              <option value="adelaide">Adelaide</option>
            </select>
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              style={{
                padding: '0.75rem 2rem',
                background: loading ? '#94a3b8' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '3px solid #e2e8f0',
              borderTopColor: '#2563eb',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 1rem'
            }} />
            <p style={{ color: '#64748b' }}>Searching...</p>
          </div>
        ) : results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            <p>No cars found. Try searching for "Toyota" or "BMW".</p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1rem'
          }}>
            {results.map(car => (
              <div key={car.id} style={{
                background: 'white',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}>
                {/* Image */}
                <div style={{ height: '180px', background: '#f1f5f9', position: 'relative' }}>
                  {car.images && car.images[0] ? (
                    <img
                      src={car.images[0]}
                      alt={car.title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  ) : (
                    <div style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#94a3b8'
                    }}>
                      No Image
                    </div>
                  )}
                  <span style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    background: car.source === 'Facebook Marketplace' ? '#fef3c7' : car.source === 'eBay Australia' ? '#fce7f3' : '#dbeafe',
                    color: car.source === 'Facebook Marketplace' ? '#92400e' : car.source === 'eBay Australia' ? '#9d174d' : '#1e40af',
                    padding: '4px 10px',
                    borderRadius: '999px',
                    fontSize: '0.7rem',
                    fontWeight: '700'
                  }}>
                    {car.source}
                  </span>
                  {car.accuracy_score > 0 && (
                    <span style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      background: 'rgba(0,0,0,0.7)',
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}>
                      ⭐ {car.accuracy_score}%
                    </span>
                  )}
                </div>

                {/* Content */}
                <div style={{ padding: '1rem' }}>
                  <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', lineHeight: 1.4 }}>
                    <a href={car.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0f172a', textDecoration: 'none' }}>
                      {car.title}
                    </a>
                  </h3>
                  <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#2563eb', marginBottom: '0.75rem' }}>
                    {car.price ? `$${car.price.toLocaleString()}` : 'Contact for price'}
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#64748b', marginBottom: '1rem' }}>
                    <span>📅 {car.year || 'N/A'}</span>
                    <span>🚗 {(car.odometer / 1000).toFixed(0)}k km</span>
                    <span>📍 {car.location}</span>
                  </div>
                  <a
                    href={car.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      color: '#2563eb',
                      textDecoration: 'none',
                      fontWeight: '600',
                      fontSize: '0.875rem'
                    }}
                  >
                    View Listing →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '2rem', color: '#64748b', fontSize: '0.875rem', borderTop: '1px solid #e2e8f0' }}>
        © 2026 CarMates. Data from Facebook Marketplace, eBay, Gumtree, Carsales & manual submissions.
      </footer>

      <style jsx global>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
