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
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualUrl, setManualUrl] = useState('');
  const [manualStatus, setManualStatus] = useState(null);

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
      const searchFilters = { ...filters, q: query };
      const data = await searchCars(API_URL, searchFilters);
      
      setResults(data.results || []);
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
    setFilters(prev => ({ ...prev, ...newFilters }));
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualUrl.trim()) return;

    setManualStatus({ type: 'loading', message: 'Adding...' });

    try {
      const formData = new FormData();
      formData.append('url', manualUrl.trim());

      const response = await fetch(`${API_URL}/submit`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to add');
      }

      setManualStatus({ 
        type: 'success', 
        message: `✅ Added! It will appear in search results.` 
      });
      setManualUrl('');
      setTimeout(() => setManualStatus(null), 4000);
    } catch (err) {
      setManualStatus({ type: 'error', message: `❌ ${err.message}` });
      setTimeout(() => setManualStatus(null), 4000);
    }
  };

  return (
    <div className="app">
      <Head>
        <title>CarMates - Real Australian Car Listings</title>
        <meta name="description" content="Search real cars from eBay, Carsales, Facebook Marketplace" />
      </Head>

      <header className="app-header">
        <div className="header-content">
          <h1>🚗 CarMates</h1>
          <p>Real listings from eBay, Carsales & Facebook Marketplace</p>
          
          {/* API Status Bar */}
          <div className="status-bar">
            <span className={`status-dot ${apiStatus}`}></span>
            <span className="status-text">
              {apiStatus === 'connected' ? 'Live Data' : apiStatus === 'checking' ? 'Connecting...' : 'Offline'}
            </span>
            {apiDetails?.sources_configured && (
              <span className="sources-configured">
                {Object.entries(apiDetails.sources_configured)
                  .filter(([_, v]) => v)
                  .map(([k]) => k.replace('_', ' '))
                  .join(' • ')}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Search Section */}
        <div className="search-section">
          <SearchBar onSearch={handleSearch} loading={loading} />
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
        </div>

        {/* Results Meta */}
        {sources.length > 0 && !loading && (
          <div className="results-meta-bar">
            <div className="source-tags">
              {sources.map(source => (
                <span key={source} className={`source-tag tag-${source.toLowerCase().replace(/\s+/g, '-')}`}>
                  {source === 'Manual' && '✅ '}
                  {source === 'Facebook Marketplace' && '⚠️ '}
                  {source}
                </span>
              ))}
            </div>
            <div className="results-count">
              {totalResults} results • {searchTime}ms
            </div>
          </div>
        )}

        {/* Toggle Manual Form */}
        <button 
          className="toggle-manual-btn"
          onClick={() => setShowManualForm(!showManualForm)}
        >
          {showManualForm ? '− Hide' : '+ Add Listing Manually'}
        </button>

        {/* Manual Form (Collapsible) */}
        {showManualForm && (
          <div className="manual-form-panel">
            <p className="manual-hint">Paste a Facebook Marketplace, Carsales, or eBay listing URL</p>
            <form onSubmit={handleManualSubmit}>
              <div className="manual-input-row">
                <input
                  type="url"
                  value={manualUrl}
                  onChange={(e) => setManualUrl(e.target.value)}
                  placeholder="https://www.facebook.com/marketplace/item/1234567890"
                  className="manual-input"
                  required
                />
                <button type="submit" className="manual-submit-btn" disabled={manualStatus?.type === 'loading'}>
                  {manualStatus?.type === 'loading' ? 'Adding...' : 'Add'}
                </button>
              </div>
            </form>
            {manualStatus && (
              <div className={`manual-status ${manualStatus.type}`}>
                {manualStatus.message}
              </div>
            )}
          </div>
        )}

        {/* Results */}
        <ResultsGrid 
          results={results} 
          loading={loading} 
          error={error}
          sources={sources}
        />
      </main>

      <footer className="app-footer">
        <p>© 2026 CarMates. Real data only — no mockups.</p>
      </footer>

      <style jsx global>{`
        .status-bar {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-top: 0.75rem;
          padding: 0.5rem 1rem;
          background: rgba(255,255,255,0.15);
          border-radius: 999px;
          display: inline-flex;
        }
        
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ef4444;
        }
        
        .status-dot.connected {
          background: #22c55e;
          animation: pulse 2s infinite;
        }
        
        .status-dot.checking {
          background: #fbbf24;
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .status-text {
          font-size: 0.875rem;
          font-weight: 600;
        }
        
        .sources-configured {
          font-size: 0.75rem;
          opacity: 0.8;
          margin-left: 0.5rem;
          padding-left: 0.5rem;
          border-left: 1px solid rgba(255,255,255,0.3);
        }
        
        .results-meta-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem 1rem;
          background: white;
          border-radius: 8px;
          margin-bottom: 1rem;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          flex-wrap: wrap;
          gap: 0.5rem;
        }
        
        .source-tags {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }
        
        .source-tag {
          font-size: 0.75rem;
          padding: 0.25rem 0.75rem;
          border-radius: 999px;
          font-weight: 600;
        }
        
        .tag-ebay-australia { background: #fce7f3; color: #9d174d; }
        .tag-carsales { background: #dbeafe; color: #1e40af; }
        .tag-facebook-marketplace { background: #fef3c7; color: #92400e; }
        .tag-manual { background: #e0e7ff; color: #3730a3; }
        
        .results-count {
          font-size: 0.875rem;
          color: #64748b;
          margin-left: auto;
        }
        
        .toggle-manual-btn {
          background: transparent;
          border: 2px dashed #cbd5e1;
          color: #64748b;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 600;
          margin-bottom: 1rem;
          width: 100%;
          transition: all 0.2s;
        }
        
        .toggle-manual-btn:hover {
          border-color: #2563eb;
          color: #2563eb;
        }
        
        .manual-form-panel {
          background: #f8fafc;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 1.5rem;
        }
        
        .manual-hint {
          font-size: 0.875rem;
          color: #64748b;
          margin-bottom: 0.75rem;
        }
        
        .manual-input-row {
          display: flex;
          gap: 0.5rem;
        }
        
        .manual-input {
          flex: 1;
          padding: 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          font-size: 0.875rem;
        }
        
        .manual-submit-btn {
          background: #2563eb;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
        }
        
        .manual-submit-btn:disabled {
          opacity: 0.6;
        }
        
        .manual-status {
          margin-top: 0.75rem;
          padding: 0.75rem;
          border-radius: 8px;
          font-size: 0.875rem;
        }
        
        .manual-status.success {
          background: #dcfce7;
          color: #166534;
        }
        
        .manual-status.error {
          background: #fef2f2;
          color: #dc2626;
        }
        
        .manual-status.loading {
          background: #fef3c7;
          color: #92400e;
        }
      `}</style>
    </div>
  );
}
