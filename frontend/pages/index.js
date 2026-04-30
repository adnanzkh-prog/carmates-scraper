import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { Search, Filter, Plus, ExternalLink, Shield, AlertTriangle, Star, Zap, Database, Eye } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

export default function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('sydney');
  const [apiStatus, setApiStatus] = useState(null);
  const [devMode, setDevMode] = useState(true);
  const [useRealApis, setUseRealApis] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualUrl, setManualUrl] = useState('');
  const [manualStatus, setManualStatus] = useState(null);
  const [searchMeta, setSearchMeta] = useState(null);

  // Check API health
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(r => r.json())
      .then(data => {
        setApiStatus(data);
        setDevMode(data.dev_mode);
      })
      .catch(() => setApiStatus({ status: 'error' }));
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        q: query,
        location,
        limit: '12',
        use_real_apis: useRealApis.toString()
      });
      
      const response = await fetch(`${API_URL}/search?${params}`);
      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || 'Search failed');
      
      setResults(data.results || []);
      setSearchMeta({
        total: data.total,
        time: data.search_time_ms,
        sources: data.sources,
        apiCalls: data.api_calls_made,
        devMode: data.dev_mode
      });
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, location, useRealApis]);

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
      if (!response.ok) throw new Error(data.detail || 'Failed');
      
      setManualStatus({ type: 'success', message: '✅ Added successfully!' });
      setManualUrl('');
      setTimeout(() => setManualStatus(null), 3000);
    } catch (err) {
      setManualStatus({ type: 'error', message: `❌ ${err.message}` });
      setTimeout(() => setManualStatus(null), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Head>
        <title>CarMates — Australian Car Search</title>
        <meta name="description" content="Search cars from eBay, Carsales, Facebook Marketplace" />
      </Head>

      {/* Header */}
      <header className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Zap className="w-6 h-6 text-yellow-400" />
                CarMates
              </h1>
              <p className="text-slate-400 text-sm mt-1">Search real listings across Australia</p>
            </div>
            
            {/* Mode Indicator */}
            <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
              devMode ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'
            }`}>
              {devMode ? '🔒 DEV MODE' : '⚡ LIVE APIs'}
            </div>
          </div>

          {/* API Status Bar */}
          {apiStatus && (
            <div className="flex gap-4 text-xs text-slate-400 flex-wrap">
              {Object.entries(apiStatus.sources_configured || {}).map(([name, active]) => (
                <span key={name} className={`flex items-center gap-1 ${active ? 'text-green-400' : 'text-slate-600'}`}>
                  {active ? '●' : '○'} {name.replace('_', ' ')}
                </span>
              ))}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Search Section */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
          <div className="flex gap-3 mb-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search Toyota, BMW, Honda..."
                className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="px-4 py-3 border border-slate-300 rounded-lg bg-white"
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
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? 'Searching...' : <><Search className="w-4 h-4" /> Search</>}
            </button>
          </div>

          {/* Controls Row */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              {!devMode && (
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useRealApis}
                    onChange={(e) => setUseRealApis(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className={useRealApis ? 'text-amber-600 font-medium' : 'text-slate-600'}>
                    {useRealApis ? '⚠️ Live APIs (costs credits)' : 'Use sample data'}
                  </span>
                </label>
              )}
              
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-1 text-sm text-slate-600 hover:text-blue-600"
              >
                <Filter className="w-4 h-4" />
                Filters
              </button>
            </div>

            <button
              onClick={() => setShowManualForm(!showManualForm)}
              className="flex items-center gap-1 text-sm text-slate-600 hover:text-blue-600"
            >
              <Plus className="w-4 h-4" />
              Add Listing
            </button>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-500">Min Price</label>
                <input type="number" placeholder="0" className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">Max Price</label>
                <input type="number" placeholder="Any" className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">Year From</label>
                <input type="number" placeholder="2015" className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">Year To</label>
                <input type="number" placeholder="2026" className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
              </div>
            </div>
          )}
        </div>

        {/* Manual Submit Panel */}
        {showManualForm && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Add Listing Manually</h3>
            <p className="text-xs text-blue-700 mb-3">Paste a Facebook Marketplace, Carsales, or eBay URL</p>
            <form onSubmit={handleManualSubmit} className="flex gap-2">
              <input
                type="url"
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                placeholder="https://www.facebook.com/marketplace/item/1234567890"
                className="flex-1 px-3 py-2 border border-blue-300 rounded-lg text-sm"
                required
              />
              <button
                type="submit"
                disabled={manualStatus?.type === 'loading'}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {manualStatus?.type === 'loading' ? 'Adding...' : 'Add'}
              </button>
            </form>
            {manualStatus && (
              <div className={`mt-2 text-sm ${manualStatus.type === 'success' ? 'text-green-700' : manualStatus.type === 'error' ? 'text-red-700' : 'text-amber-700'}`}>
                {manualStatus.message}
              </div>
            )}
          </div>
        )}

        {/* Search Meta */}
        {searchMeta && (
          <div className="flex items-center justify-between mb-4 text-sm text-slate-600">
            <div className="flex items-center gap-3">
              <span>{searchMeta.total} results</span>
              <span className="text-slate-400">•</span>
              <span>{searchMeta.time}ms</span>
              {searchMeta.apiCalls > 0 && (
                <>
                  <span className="text-slate-400">•</span>
                  <span className="text-amber-600">{searchMeta.apiCalls} API calls</span>
                </>
              )}
            </div>
            <div className="flex gap-2">
              {searchMeta.sources.map(source => (
                <span key={source} className="px-2 py-1 bg-slate-100 rounded-md text-xs font-medium">
                  {source}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Results Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-slate-500">Searching marketplaces...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-700">{error}</p>
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 mb-2">No listings found</p>
            <p className="text-sm text-slate-400">
              {devMode 
                ? "Try searching for 'Toyota', 'BMW', or 'Honda' (dev mode uses sample data)" 
                : "Enable 'Live APIs' to search real marketplaces"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {results.map(car => (
              <CarCard key={car.id} car={car} devMode={devMode} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

// Car Card Component
function CarCard({ car, devMode }) {
  const formatPrice = (price) => {
    if (!price) return 'Contact for price';
    return `$${price.toLocaleString()}`;
  };

  const sourceColors = {
    'eBay Australia': 'bg-pink-100 text-pink-800',
    'Carsales': 'bg-blue-100 text-blue-800',
    'Facebook Marketplace': 'bg-amber-100 text-amber-800',
    'Manual': 'bg-green-100 text-green-800',
    'Sample Data (Dev Mode)': 'bg-slate-100 text-slate-600'
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
      {/* Image */}
      <div className="relative h-48 bg-slate-100">
        {car.images && car.images[0] ? (
          <a href={car.url} target="_blank" rel="noopener noreferrer">
            <img 
              src={car.images[0]} 
              alt={car.title}
              className="w-full h-full object-cover hover:scale-105 transition-transform"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
            <div className="hidden absolute inset-0 items-center justify-center text-slate-400">
              <Eye className="w-8 h-8" />
            </div>
          </a>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400">
            <Eye className="w-8 h-8" />
          </div>
        )}
        
        {/* Badges */}
        <div className="absolute top-3 left-3 flex gap-2">
          <span className={`px-2 py-1 rounded-md text-xs font-bold ${sourceColors[car.source] || 'bg-slate-100 text-slate-600'}`}>
            {car.source === 'Facebook Marketplace' && <AlertTriangle className="w-3 h-3 inline mr-1" />}
            {car.source}
          </span>
        </div>
        
        {car.accuracy_score > 0 && (
          <div className="absolute top-3 right-3 bg-black/70 text-white px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
            {car.accuracy_score}%
          </div>
        )}
        
        {car.verified && (
          <div className="absolute bottom-3 left-3 bg-green-500 text-white px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1">
            <Shield className="w-3 h-3" />
            Verified
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-slate-900 mb-2 line-clamp-2 leading-tight">
          <a href={car.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-600">
            {car.title}
          </a>
        </h3>
        
        <div className="text-2xl font-bold text-blue-600 mb-3">
          {formatPrice(car.price)}
        </div>

        <div className="grid grid-cols-3 gap-2 text-sm text-slate-600 mb-3">
          <div className="bg-slate-50 rounded-lg p-2 text-center">
            <div className="text-xs text-slate-400">Year</div>
            <div className="font-semibold">{car.year || 'N/A'}</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-2 text-center">
            <div className="text-xs text-slate-400">Odometer</div>
            <div className="font-semibold">{car.odometer ? `${(car.odometer/1000).toFixed(0)}k km` : 'N/A'}</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-2 text-center">
            <div className="text-xs text-slate-400">Location</div>
            <div className="font-semibold truncate">{car.location || 'N/A'}</div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-100">
          <span className="text-xs text-slate-400">
            {new Date(car.scraped_at).toLocaleDateString('en-AU')}
          </span>
          <a 
            href={car.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            View <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
