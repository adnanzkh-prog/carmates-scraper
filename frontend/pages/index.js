// frontend/pages/index.js
import { useState, useEffect, useRef } from 'react';
import Head from 'next/head';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

// ─── API Helper Functions ───
const startScrape = async (request) => {
    const res = await fetch(`${API_URL}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error(`Failed to queue scrape: ${res.status}`);
    return res.json();
};

const getScrapeStatus = async (taskId) => {
    const res = await fetch(`${API_URL}/scrape/status/${taskId}`);
    if (!res.ok) throw new Error(`Failed to check status: ${res.status}`);
    return res.json();
};

const getListings = async (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
        if (v !== '' && v !== null && v !== undefined) params.append(k, v);
    });
    const res = await fetch(`${API_URL}/listings?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to fetch listings: ${res.status}`);
    return res.json();
};

const checkBackendHealth = async () => {
    try {
        const res = await fetch(`${API_URL}/listings?limit=1`, { timeout: 5000 });
        return res.ok;
    } catch {
        return false;
    }
};

const parseImages = (imageUrlsRaw) => {
    if (!imageUrlsRaw) return [];
    try {
        const parsed = JSON.parse(imageUrlsRaw);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
};

// ─── localStorage Helpers for Remember Me ───
const CREDENTIALS_KEY = 'carmates_credentials';

const loadSavedCredentials = () => {
    if (typeof window === 'undefined') return null;
    try {
        const saved = localStorage.getItem(CREDENTIALS_KEY);
        return saved ? JSON.parse(saved) : null;
    } catch {
        return null;
    }
};

const saveCredentials = (email, password) => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(CREDENTIALS_KEY, JSON.stringify({ email, password }));
};

const clearCredentials = () => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(CREDENTIALS_KEY);
};

export default function Home() {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [query, setQuery] = useState('');
    const [location, setLocation] = useState('sydney');
    const [apiStatus, setApiStatus] = useState('checking');
    const [hasSearched, setHasSearched] = useState(false);
    const [taskId, setTaskId] = useState(null);
    const [error, setError] = useState('');
    const [progress, setProgress] = useState('');
    
    // ─── Login State ───
    const [showLogin, setShowLogin] = useState(false);
    const [fbEmail, setFbEmail] = useState('');
    const [fbPassword, setFbPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [hasSavedCreds, setHasSavedCreds] = useState(false);
    
    const pollRef = useRef(null);

    // ─── Load saved credentials on mount ───
    useEffect(() => {
        checkBackendHealth()
            .then(ok => setApiStatus(ok ? 'connected' : 'error'))
            .catch(() => setApiStatus('error'));
        
        // Load remembered credentials
        const saved = loadSavedCredentials();
        if (saved) {
            setFbEmail(saved.email);
            setFbPassword(saved.password);
            setHasSavedCreds(true);
            setRememberMe(true);
        }
    }, []);

    useEffect(() => {
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, []);

    // ─── Search Handler ───
    const handleSearch = async () => {
        if (!query.trim()) return;
        
        setLoading(true);
        setResults([]);
        setError('');
        setProgress('Queuing scrape job...');
        setHasSearched(true);
        setTaskId(null);
        
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }

        // Handle remember me
        if (rememberMe && fbEmail && fbPassword) {
            saveCredentials(fbEmail, fbPassword);
            setHasSavedCreds(true);
        } else if (!rememberMe && hasSavedCreds) {
            clearCredentials();
            setHasSavedCreds(false);
        }

        try {
            const scrapeRequest = {
                query: query.trim(),
                location: location,
                limit: 20,
                // Only send credentials if provided
                email: fbEmail || undefined,
                password: fbPassword || undefined,
            };

            const { task_id } = await startScrape(scrapeRequest);
            
            setTaskId(task_id);
            setProgress(`Job queued: ${task_id.slice(0, 8)}... Polling...`);

            // Poll for completion
            pollRef.current = setInterval(async () => {
                try {
                    const status = await getScrapeStatus(task_id);
                    
                    if (status.status === 'SUCCESS') {
                        clearInterval(pollRef.current);
                        pollRef.current = null;
                        setProgress('Scrape complete! Fetching results...');
                        
                        const listings = await getListings({ 
                            search: query.trim(),
                            limit: 20 
                        });
                        
                        setResults(listings.listings || []);
                        setLoading(false);
                        setProgress(`Found ${listings.total || 0} total listings in database`);
                        
                    } else if (status.status === 'FAILURE') {
                        clearInterval(pollRef.current);
                        pollRef.current = null;
                        
                        // Smart error messages based on failure reason
                        const errorMsg = status.result?.error || '';
                        if (errorMsg.includes('credentials') || errorMsg.includes('login')) {
                            setError('❌ Facebook login required. Please provide your email and password above, or try scraping without login (limited results).');
                        } else if (errorMsg.includes('blocked') || errorMsg.includes('CAPTCHA')) {
                            setError('❌ Facebook blocked the request. Try again later or use login credentials.');
                        } else {
                            setError('❌ Scraping failed. ' + errorMsg);
                        }
                        setLoading(false);
                        setProgress('');
                        
                    } else if (status.status === 'STARTED') {
                        setProgress('🔄 Scraping in progress... (this may take 30-60 seconds)');
                    } else if (status.status === 'PENDING') {
                        setProgress('⏳ Job pending in queue...');
                    }
                } catch (pollErr) {
                    console.error('Poll error:', pollErr);
                }
            }, 3000);
            
        } catch (err) {
            setError(err.message);
            setLoading(false);
            setProgress('');
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') handleSearch();
    };

    const handleExportCSV = () => window.open(`${API_URL}/export/csv`, '_blank');
    const handleExportExcel = () => window.open(`${API_URL}/export/excel`, '_blank');

    // ─── Clear saved credentials ───
    const handleClearCredentials = () => {
        clearCredentials();
        setFbEmail('');
        setFbPassword('');
        setRememberMe(false);
        setHasSavedCreds(false);
    };

    return (
        <div style={styles.container}>
            <Head>
                <title>CarMates - Australian Car Search</title>
                <meta name="description" content="Search cars from Facebook Marketplace" />
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
                            <option value="australia">All Australia</option>
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
                            {loading ? 'Scraping...' : '🔍 Search'}
                        </button>
                    </div>

                    {/* ─── Facebook Login Section (Collapsible) ─── */}
                    <div style={styles.loginSection}>
                        <button
                            type="button"
                            onClick={() => setShowLogin(!showLogin)}
                            style={styles.loginToggle}
                        >
                            <span>{showLogin ? '▼' : '▶'}</span>
                            <span>
                                {hasSavedCreds 
                                    ? '🔐 Facebook Login (credentials saved)' 
                                    : '🔐 Facebook Login (optional — better results)'}
                            </span>
                        </button>

                        {showLogin && (
                            <div style={styles.loginForm}>
                                <div style={styles.loginRow}>
                                    <input
                                        type="email"
                                        value={fbEmail}
                                        onChange={(e) => setFbEmail(e.target.value)}
                                        placeholder="Facebook Email"
                                        style={styles.loginInput}
                                    />
                                    <input
                                        type="password"
                                        value={fbPassword}
                                        onChange={(e) => setFbPassword(e.target.value)}
                                        placeholder="Facebook Password"
                                        style={styles.loginInput}
                                    />
                                </div>
                                
                                <div style={styles.loginOptions}>
                                    <label style={styles.rememberLabel}>
                                        <input
                                            type="checkbox"
                                            checked={rememberMe}
                                            onChange={(e) => setRememberMe(e.target.checked)}
                                            style={styles.checkbox}
                                        />
                                        <span>Remember me on this device</span>
                                    </label>
                                    
                                    {hasSavedCreds && (
                                        <button
                                            type="button"
                                            onClick={handleClearCredentials}
                                            style={styles.clearCredsBtn}
                                        >
                                            🗑️ Clear saved credentials
                                        </button>
                                    )}
                                </div>

                                <p style={styles.loginHint}>
                                    💡 <strong>Without login:</strong> Limited results, may be blocked by Facebook.<br/>
                                    💡 <strong>With login:</strong> Full access, better results, cookies saved for future scrapes.
                                </p>
                            </div>
                        )}
                    </div>
                    
                    {/* Progress / Error Display */}
                    {progress && (
                        <div style={styles.progressBar}>
                            <span style={styles.progressText}>{progress}</span>
                            {taskId && <span style={styles.taskId}>Task: {taskId.slice(0, 12)}...</span>}
                        </div>
                    )}
                    {error && (
                        <div style={styles.errorBox}>
                            <p style={styles.errorText}>{error}</p>
                        </div>
                    )}
                </div>

                {/* Export Buttons */}
                {results.length > 0 && (
                    <div style={styles.exportBar}>
                        <button onClick={handleExportCSV} style={styles.exportBtn}>📄 Export CSV</button>
                        <button onClick={handleExportExcel} style={styles.exportBtn}>📊 Export Excel</button>
                    </div>
                )}

                {/* Results Section */}
                <div style={styles.resultsSection}>
                    
                    {loading && (
                        <div style={styles.loadingState}>
                            <div style={styles.spinner} />
                            <p style={styles.loadingText}>Scraping Facebook Marketplace... This may take 30-60 seconds</p>
                            <p style={styles.loadingSubtext}>
                                {fbEmail 
                                    ? `Logged in as ${fbEmail.slice(0, 3)}***...` 
                                    : 'Scraping without login (limited results)'}
                            </p>
                        </div>
                    )}

                    {!loading && hasSearched && results.length === 0 && !error && (
                        <div style={styles.emptyState}>
                            <p style={styles.emptyTitle}>No cars found</p>
                            <p style={styles.emptySubtitle}>
                                {fbEmail 
                                    ? 'Try different search terms or check your Facebook credentials.' 
                                    : 'Try providing Facebook login for better results, or use different search terms.'}
                            </p>
                        </div>
                    )}

                    {!loading && results.length > 0 && (
                        <div>
                            <div style={styles.resultsMeta}>
                                Showing <strong>{results.length}</strong> results 
                                <span style={styles.sourceTag}>from Facebook Marketplace</span>
                                {fbEmail && <span style={styles.loggedInTag}>🔐 Logged in</span>}
                            </div>
                            
                            <div style={styles.grid}>
                                {results.map((car, index) => (
                                    <div key={car.facebook_id || index} style={styles.card}>
                                        <div style={styles.imageContainer}>
                                            {(() => {
                                                const images = parseImages(car.image_urls);
                                                return images.length > 0 ? (
                                                    <a href={car.listing_url} target="_blank" rel="noopener noreferrer">
                                                        <img
                                                            src={images[0]}
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
                                                );
                                            })()}
                                            
                                            {car.condition && (
                                                <span style={styles.conditionBadge}>
                                                    {car.condition}
                                                </span>
                                            )}
                                        </div>

                                        <div style={styles.cardContent}>
                                            <h3 style={styles.cardTitle}>
                                                <a 
                                                    href={car.listing_url} 
                                                    target="_blank" 
                                                    rel="noopener noreferrer"
                                                    style={styles.titleLink}
                                                >
                                                    {car.title}
                                                </a>
                                            </h3>
                                            
                                            <div style={styles.price}>
                                                {car.price ? `$${car.price.toLocaleString()} ${car.currency || 'AUD'}` : 'Contact for price'}
                                            </div>

                                            <div style={styles.details}>
                                                <span style={styles.detailItem}>📅 {car.year || 'N/A'}</span>
                                                <span style={styles.detailItem}>🚗 {car.odometer ? `${(car.odometer/1000).toFixed(0)}k ${car.odometer_unit || 'km'}` : 'N/A'}</span>
                                                <span style={styles.detailItem}>📍 {car.location || 'Australia'}</span>
                                            </div>

                                            <a 
                                                href={car.listing_url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                style={styles.viewLink}
                                            >
                                                View on Facebook →
                                            </a>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {!hasSearched && !loading && (
                        <div style={styles.initialState}>
                            <p style={styles.initialTitle}>🔍 Start Your Search</p>
                            <p style={styles.initialSubtitle}>Enter a car make or model to scrape Facebook Marketplace listings</p>
                            <p style={styles.initialNote}>
                                💡 <strong>Pro tip:</strong> Add your Facebook login for full access to all listings.<br/>
                                🔒 Credentials are only used for this session and optional to save.
                            </p>
                        </div>
                    )}
                </div>
            </main>

            <footer style={styles.footer}>
                © 2026 CarMates. Data from Facebook Marketplace. Built with Playwright + Celery + PostgreSQL.
            </footer>

            <style jsx global>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// ─── Updated Styles with Login Section ───
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
        maxWidth: '120
