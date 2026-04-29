import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import SearchBar from '../components/SearchBar';
import FilterPanel from '../components/FilterPanel';
import ResultsGrid from '../components/ResultsGrid';
import { searchCars, healthCheck } from '../lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({});
  const [apiStatus, setApiStatus] = useState('checking');
  const [apiDetails, setApiDetails] = useState(null);
  const [sources, setSources] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [searchTime, setSearchTime] = useState(0);
  const [manualUrl, setManualUrl] = useState('');
  const [manualSubmitStatus, setManualSubmitStatus] = useState(null);

  // Check API health on mount
  useEffect(() => {
    healthCheck()
      .then((data) => {
        setApiStatus('connected');
        setApiDetails(data);
      })
      .catch(() => setApiStatus('disconnected'));
  }, []);

  const handleSearch = useCallback(async (query) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await searchCars(query, filters);
      console.log('Search response:', data);
      
      const resultsArray = data.results || [];
      setResults(resultsArray);
      setTotalResults(data.total || 0);
      setSearchTime(data.search_time_ms || 0);
      setSources(data.sources || []);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to fetch results');
      setResults([]);
      setSources([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  // Manual submission handler
  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualUrl.trim()) return;

    setManualSubmitStatus({ type: 'loading', message: 'Adding listing...' });

    try {
      const response = await fetch(`${API_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: manualUrl.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to add listing');
      }

      setManualSubmitStatus({ 
        type: 'success', 
        message: `✅ Added: ${data.title || 'Listing'} (Accuracy: ${data.accuracy_score}%)` 
      });
      setManualUrl('');
      
      // Refresh search to show new listing
      if (filters.q) {
        handleSearch(filters.q);
      }
      
      setTimeout(() => setManualSubmitStatus(null), 5000);
    } catch (err) {
      setManualSubmitStatus({ type: 'error', message: `❌ ${err.message}` });
      setTimeout(() => setManualSubmitStatus(null), 5000);
    }
  };

  // Get source badge color
  const getSourceColor = (source) => {
    const colors = {
      'Carsales': '#dbeafe',
      'eBay Australia': '#fce7f3',
      'Gumtree': '#dcfce7',
      'Facebook Marketplace': '#fef3c7',
      'Manual Submission': '#e0e7ff',
      'Sample Data': '#f3f4f6'
    };
    return colors[source] || '#f3f4f6';
  };

  // Get API status icon
  const getStatusIcon = () => {
    if (apiStatus === 'connected') return '🟢';
    if (apiStatus === 'checking') return '🟡';
    return '🔴';
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
          
          {/* API Status Dashboard */}
          <div className="api-dashboard">
            <div className="api-status-badge">
              {getStatusIcon()} Backend: {apiStatus === 'connected' ? 'Connected' : apiStatus === 'checking' ? 'Checking...' : 'Offline'}
            </div>
            
            {apiDetails && apiDetails.sources && (
              <div className="sources-status">
                {Object.entries(apiDetails.sources).map(([name, active]) => (
                  <span 
                    key={name} 
                    className={`source-pill ${active ? 'active' : 'inactive'}`}
                    title={active ? 'Working' : 'Not configured'}
                  >
                    {active ? '✓' : '✗'} {name.replace('_', ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Manual Submission Form */}
        <div className="manual-submit-section">
          <h3>📎 Add Listing Manually</h3>
          <p>Paste a Facebook Marketplace, Gumtree, or Carsales URL to add it to search results</p>
          
          <form onSubmit={handleManualSubmit} className="manual-form">
            <div className="manual-input-wrapper">
              <input
                type="url"
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                placeholder="https://www.facebook.com/marketplace/item/1234567890"
                className="manual-input"
                required
              />
              <button 
                type="submit" 
                className="manual-submit-btn"
                disabled={!manualUrl.trim() || (manualSubmitStatus?.type === 'loading')}
              >
                {manualSubmitStatus?.type === 'loading' ? 'Adding...' : '➕ Add Listing'}
              </button>
            </div>
          </form>

          {manualSubmitStatus && (
            <div className={`submit-status ${manualSubmitStatus.type}`}>
              {manualSubmitStatus.message}
            </div>
          )}
        </div>

        <div className="search-section">
          <SearchBar onSearch={handleSearch} loading={loading} />
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
        </div>

        {/* Active Sources Bar */}
        {sources.length > 0 && (
          <div className="active-sources-bar">
            <span className="sources-label">Data from:</span>
            {sources.map(source => (
              <span 
                key={source} 
                className="active-source-tag"
                style={{ background: getSourceColor(source) }}
              >
                {source === 'Facebook Marketplace' && '⚠️ '}
                {source === 'Manual Submission' && '✅ '}
                {source}
              </span>
            ))}
            <span className="results-meta">
              {totalResults} results • {searchTime}ms
            </span>
          </div>
        )}

        <ResultsGrid 
          results={results} 
          loading={loading} 
          error={error} 
        />
      </main>

      <footer className="app-footer">
        <p>© 2026 CarMates. Data from Facebook Marketplace, eBay, Gumtree, Carsales & manual submissions.</p>
      </footer>

      {/* Add these styles */}
      <style jsx>{`
        .api-dashboard {
          margin-top: 1rem;
          padding: 0.75rem;
          background: rgba(255,255,255,0.15);
          border-radius: 12px;
          backdrop-filter: blur(10px);
        }
        
        .api-status-badge {
          font-size: 0.875rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }
        
        .sources-status {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
          justify-content: center;
        }
        
        .source-pill {
          font-size: 0.75rem;
          padding: 0.25rem 0.5rem;
          border-radius: 999px;
          background: rgba(255,255,255,0.2);
          color: white;
        }
        
        .source-pill.active {
          background: rgba(34, 197, 94, 0.3);
        }
        
        .source-pill.inactive {
          background: rgba(239, 68, 68, 0.2);
          opacity: 0.7;
        }
        
        .manual-submit-section {
          background: linear-gradient(135deg, #1e293b, #334155);
          color: white;
          padding: 1.5rem;
          border-radius: 12px;
          margin-bottom: 2rem;
        }
        
        .manual-submit-section h3 {
          margin-bottom: 0.25rem;
          font-size: 1.1rem;
        }
        
        .manual-submit-section p {
          opacity: 0.8;
          font-size: 0.875rem;
          margin-bottom: 1rem;
        }
        
        .manual-form {
          display: flex;
          gap: 0.5rem;
        }
        
        .manual-input-wrapper {
          display: flex;
          flex: 1;
          gap: 0.5rem;
        }
        
        .manual-input {
          flex: 1;
          padding: 0.75rem;
          border: 2px solid rgba(255,255,255,0.2);
          border-radius: 8px;
          background: rgba(255,255,255,0.1);
          color: white;
          font-size: 0.875rem;
        }
        
        .manual-input::placeholder {
          color: rgba(255,255,255,0.5);
        }
        
        .manual-submit-btn {
          background: #22c55e;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }
        
        .manual-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .submit-status {
          margin-top: 0.75rem;
          padding: 0.75rem;
          border-radius: 8px;
          font-size: 0.875rem;
        }
        
        .submit-status.success {
          background: #dcfce7;
          color: #166534;
        }
        
        .submit-status.error {
          background: #fef2f2;
          color: #dc2626;
        }
        
        .submit-status.loading {
          background: #fef3c7;
          color: #92400e;
        }
        
        .active-sources-bar {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 1rem;
          padding: 0.75rem;
          background: white;
          border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          flex-wrap: wrap;
        }
        
        .sources-label {
          font-size: 0.875rem;
          color: #64748b;
          font-weight: 500;
        }
        
        .active-source-tag {
          font-size: 0.75rem;
          padding: 0.25rem 0.75rem;
          border-radius: 999px;
          font-weight: 600;
          color: #1e293b;
        }
        
        .results-meta {
          margin-left: auto;
          font-size: 0.75rem;
          color: #64748b;
        }
      `}</style>
    </div>
  );
}
