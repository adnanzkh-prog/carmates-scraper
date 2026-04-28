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

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('disconnected'));
  }, []);

  const handleSearch = async (query) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchCars(query, filters);
      console.log('Search response:', data);
      const resultsArray = data.results || [];
      setResults(resultsArray);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to fetch results');
      setResults([]);
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
            API: {apiStatus === 'connected' ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="search-section">
          <SearchBar onSearch={handleSearch} loading={loading} />
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
        </div>

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
