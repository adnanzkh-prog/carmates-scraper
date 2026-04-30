// frontend/pages/index.js
import { useState, useEffect } from 'react';
import Head from 'next/head';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('sydney');
  const [apiStatus, setApiStatus] = useState('checking');
  const [hasSearched, setHasSearched] = useState(false);

  // Check API health on mount
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => {
        if (r.ok) {
          setApiStatus('connected');
        } else {
          setApiStatus('error');
        }
      })
      .catch(() => setApiStatus('error'));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setHasSearched(true);
    setResults([]);
    
    try {
      const params = new URLSearchParams({
        q: query.trim(),
        location: location,
        limit: '20'
      });
      
      console.log('Fetching:', `${API_URL}/search?${params}`);
      
      const res = await fetch(`${API_URL}/search?${params}`);
      const data = await res.json();
      
      console.log('Response:', data);
      
      if (data.results && Array.isArray(data.results)) {
        setResults(data.results);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div style={styles.container}>
      <Head>
        <title>CarMates - Australian Car Search</title>
        <meta name="description" content="Search cars from eBay, Carsales, Facebook Marketplace" />
      </Head>

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.title}>🚗 CarMates</h1>
          <p style={styles.subtitle}>Find your perfect car across Australia</p>
          <div style={styles.statusBadge}>
            <span style={{
              ...styles.statusDot,
              backgroundColor: apiStatus === 'connected' ? '#22c55e' : apiStatus === 'checking' ? '#fbbf24' : '#ef4444'
            }} />
            {apiStatus === 'connected' ? 'Backend Connected' : apiStatus === 'checking' ? 'Connecting...' : 'Backend Offline'}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        
        {/* Search Section */}
        <div style={styles.searchBox}>
          <div style={styles.searchRow}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Search Toyota, BMW, Honda..."
              style={styles.searchInput}
            />
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              style={styles.locationSelect}
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
                ...styles.searchButton,
                opacity: loading || !query.trim() ? 0.6 : 1,
                cursor: loading || !query.trim() ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        {/* Results Section */}
        <div style={styles.resultsSection}>
          
          {/* Loading State */}
          {loading && (
            <div style={styles.loadingState}>
              <div style={styles.spinner} />
              <p style={styles.loadingText}>Searching marketplaces...</p>
            </div>
          )}

          {/* Empty State (after search) */}
          {!loading && hasSearched && results.length === 0 && (
            <div style={styles.emptyState}>
              <p style={styles.emptyTitle}>No cars found</p>
              <p style={styles.emptySubtitle}>Try searching for "Toyota", "BMW", or "Honda"</p>
            </div>
          )}

          {/* Results Grid */}
          {!loading && results.length > 0 && (
            <div>
              <div style={styles.resultsMeta}>
                Found <strong>{results.length}</strong> results
              </div>
              
              <div style={styles.grid}>
                {results.map((car, index) => (
                  <div key={car.id || index} style={styles.card}>
                    
                    {/* Image */}
                    <div style={styles.imageContainer}>
                      {car.images && car.images[0] ? (
                        <a href={car.url} target="_blank" rel="noopener noreferrer">
                          <img
                            src={car.images[0]}
                            alt={car.title}
                            style={styles.image}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.parentElement.nextSibling.style.display = 'flex';
                            }}
                          />
                          <div style={{...styles.imagePlaceholder, display: 'none'}}>
                            🚗 No Image
                          </div>
                        </a>
                      ) : (
                        <div style={styles.imagePlaceholder}>
                          🚗 No Image
                        </div>
                      )}
                      
                      {/* Source Badge */}
                      <span style={{
                        ...styles.sourceBadge,
                        backgroundColor: car.source === 'Facebook Marketplace' ? '#fef3c7' : 
                                        car.source === 'eBay Australia' ? '#fce7f3' : 
                                        car.source === 'Gumtree' ? '#dcfce7' : '#dbeafe',
                        color: car.source === 'Facebook Marketplace' ? '#92400e' : 
                               car.source === 'eBay Australia' ? '#9d174d' : 
                               car.source === 'Gumtree' ? '#166534' : '#1e40af'
                      }}>
                        {car.source || 'Unknown'}
                      </span>

                      {/* Accuracy Score */}
                      {car.accuracy_score > 0 && (
                        <span style={styles.accuracyBadge}>
                          ⭐ {car.accuracy_score}%
                        </span>
                      )}
                    </div>

                    {/* Card Content */}
                    <div style={styles.cardContent}>
                      <h3 style={styles.cardTitle}>
                        <a 
                          href={car.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={styles.titleLink}
                        >
                          {car.title}
                        </a>
                      </h3>
                      
                      <div style={styles.price}>
                        {car.price ? `$${car.price.toLocaleString()}` : 'Contact for price'}
                      </div>

                      <div style={styles.details}>
                        <span style={styles.detailItem}>📅 {car.year || 'N/A'}</span>
                        <span style={styles.detailItem}>🚗 {car.odometer ? `${(car.odometer/1000).toFixed(0)}k km` : 'N/A'}</span>
                        <span style={styles.detailItem}>📍 {car.location || 'Australia'}</span>
                      </div>

                      <a 
                        href={car.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={styles.viewLink}
                      >
                        View Listing →
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Initial State (before search) */}
          {!hasSearched && !loading && (
            <div style={styles.initialState}>
              <p style={styles.initialTitle}>🔍 Start Your Search</p>
              <p style={styles.initialSubtitle}>Enter a car make or model above to find listings</p>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        © 2026 CarMates. Data from Facebook Marketplace, eBay, Gumtree, Carsales & manual submissions.
      </footer>

      {/* Global Styles */}
      <style jsx global>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// Inline Styles Object
const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    margin: 0,
    padding: 0
  },
  header: {
    backgroundColor: '#0f172a',
    color: 'white',
    padding: '1.5rem'
  },
  headerContent: {
    maxWidth: '1200px',
    margin: '0 auto'
  },
  title: {
    margin: 0,
    fontSize: '1.75rem',
    fontWeight: 'bold'
  },
  subtitle: {
    margin: '0.5rem 0 0',
    opacity: 0.7,
    fontSize: '0.875rem'
  },
  statusBadge: {
    marginTop: '0.75rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.375rem 0.75rem',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: '9999px',
    fontSize: '0.75rem',
    fontWeight: 600
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block'
  },
  main: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '1.5rem'
  },
  searchBox: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    marginBottom: '1.5rem',
    border: '1px solid #e2e8f0'
  },
  searchRow: {
    display: 'flex',
    gap: '0.75rem',
    flexWrap: 'wrap',
    alignItems: 'stretch'
  },
  searchInput: {
    flex: 1,
    minWidth: '250px',
    padding: '0.875rem 1rem',
    border: '2px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '1rem',
    outline: 'none',
    transition: 'border-color 0.2s',
    fontFamily: 'inherit'
  },
  locationSelect: {
    padding: '0.875rem 1rem',
    border: '2px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '1rem',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontFamily: 'inherit'
  },
  searchButton: {
    padding: '0.875rem 2rem',
    backgroundColor: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: 600,
    transition: 'background-color 0.2s',
    fontFamily: 'inherit',
    whiteSpace: 'nowrap'
  },
  resultsSection: {
    minHeight: '200px'
  },
  resultsMeta: {
    marginBottom: '1rem',
    color: '#64748b',
    fontSize: '0.875rem'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '1rem'
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e2e8f0',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  imageContainer: {
    height: '180px',
    backgroundColor: '#f1f5f9',
    position: 'relative',
    overflow: 'hidden'
  },
  image: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: 'block'
  },
  imagePlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#94a3b8',
    fontSize: '0.875rem'
  },
  sourceBadge: {
    position: 'absolute',
    top: '8px',
    left: '8px',
    padding: '4px 10px',
    borderRadius: '9999px',
    fontSize: '0.7rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.03em'
  },
  accuracyBadge: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    backgroundColor: 'rgba(0,0,0,0.7)',
    color: 'white',
    padding: '4px 8px',
    borderRadius: '6px',
    fontSize: '0.75rem',
    fontWeight: 600
  },
  cardContent: {
    padding: '1rem'
  },
  cardTitle: {
    margin: '0 0 0.5rem',
    fontSize: '1rem',
    lineHeight: 1.4,
    fontWeight: 600
  },
  titleLink: {
    color: '#0f172a',
    textDecoration: 'none'
  },
  price: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#2563eb',
    marginBottom: '0.75rem'
  },
  details: {
    display: 'flex',
    gap: '1rem',
    fontSize: '0.875rem',
    color: '#64748b',
    marginBottom: '1rem',
    flexWrap: 'wrap'
  },
  detailItem: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.25rem'
  },
  viewLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.25rem',
    color: '#2563eb',
    textDecoration: 'none',
    fontWeight: 600,
    fontSize: '0.875rem'
  },
  loadingState: {
    textAlign: 'center',
    padding: '3rem'
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #e2e8f0',
    borderTopColor: '#2563eb',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 1rem'
  },
  loadingText: {
    color: '#64748b'
  },
  emptyState: {
    textAlign: 'center',
    padding: '3rem',
    color: '#64748b'
  },
  emptyTitle: {
    fontSize: '1.125rem',
    fontWeight: 600,
    marginBottom: '0.5rem',
    color: '#374151'
  },
  emptySubtitle: {
    fontSize: '0.875rem'
  },
  initialState: {
    textAlign: 'center',
    padding: '3rem',
    color: '#64748b'
  },
  initialTitle: {
    fontSize: '1.25rem',
    fontWeight: 600,
    marginBottom: '0.5rem',
    color: '#374151'
  },
  initialSubtitle: {
    fontSize: '0.875rem'
  },
  footer: {
    textAlign: 'center',
    padding: '2rem',
    color: '#64748b',
    fontSize: '0.875rem',
    borderTop: '1px solid #e2e8f0',
    marginTop: '2rem'
  }
};
