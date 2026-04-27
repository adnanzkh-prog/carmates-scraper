import { useState, useEffect } from 'react';
import Head from 'next/head';
import SearchBar from '../components/SearchBar';
import FilterPanel from '../components/FilterPanel';
import ResultsGrid from '../components/ResultsGrid';
import { searchCars, healthCheck } from '../lib/api';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({});
  const [apiStatus, setApiStatus] = useState('checking');
  const [debugInfo, setDebugInfo] = useState('');

  // Check API health on mount
  useEffect(() => {
    healthCheck()
      .then((data) => {
        setApiStatus('connected');
        setDebugInfo(JSON.stringify(data, null, 2));
      })
      .catch((err) => {
        setApiStatus('disconnected');
        setDebugInfo(err.message);
      });
  }, []);

  const handleSearch = async (query) => {
    setLoading(true);
    setError(null);
    setDebugInfo('');
    
    try {
      const data = await searchCars(query, filters);
      console.log('Search data:', data);
      
      // Handle different response formats
      const resultsArray = data.results || data.data || data || [];
      setResults(resultsArray);
      setDebugInfo(`Found ${resultsArray.length} results. Raw: ${JSON.stringify(data).slice(0, 200)}...`);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to fetch results');
      setResults([]);
      setDebugInfo(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  return (
    <div className="app">
      <Head>
        <title>CarMates - Find Your Perfect Car</title>
        <meta name="description" content="Search cars across Australia" />
      </Head>

      <header className="app-header">
        <div className="header-content">
          <h1>🚗 CarMates</h1>
          <p>Find your perfect car across Australia</p>
          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', opacity: 0.8 }}>
            API Status: {apiStatus === 'connected' ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="search-section">
          <SearchBar onSearch={handleSearch} loading={loading} />
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
        </div>
        
        {/* Debug panel - remove after fixing */}
        {debugInfo && (
          <div style={{ 
            background: '#1e293b', 
            color: '#94a3b8', 
            padding: '1rem', 
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.8rem',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            maxHeight: '200px',
            overflow: 'auto'
          }}>
            <strong>Debug:</strong>{'\n'}{debugInfo}
          </div>
        )}

        <ResultsGrid 
          results={results} 
          loading={loading} 
          error={error} 
        />
      </main>

      <footer className="app-footer">
        <p>© 2026 CarMates. Data sourced from multiple platforms.</p>
      </footer>
    </div>
  );
}
