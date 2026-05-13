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

const getDebugScreenshots = async () => {
    const res = await fetch(`${API_URL}/debug/screenshots`);
    if (!res.ok) return { screenshots: [] };
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

    // ─── Source Toggles ───
    const [includeFacebook, setIncludeFacebook] = useState(true);
    const [includeGumtree, setIncludeGumtree] = useState(true);

    // ─── Login State ───
    const [showLogin, setShowLogin] = useState(false);
    const [fbEmail, setFbEmail] = useState('');
    const [fbPassword, setFbPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [hasSavedCreds, setHasSavedCreds] = useState(false);

    // ─── Debug Screenshots ───
    const [showDebug, setShowDebug] = useState(false);
    const [screenshots, setScreenshots] = useState([]);
    const [selectedScreenshot, setSelectedScreenshot] = useState(null);

    const pollRef = useRef(null);

    // ─── Load saved credentials on mount ───
    useEffect(() => {
        checkBackendHealth()
            .then(ok => setApiStatus(ok ? 'connected' : 'error'))
            .catch(() => setApiStatus('error'));

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

    // ─── Fetch debug screenshots ───
    const loadScreenshots = async () => {
        try {
            const data = await getDebugScreenshots();
            setScreenshots(data.screenshots || []);
            if (data.screenshots && data.screenshots.length > 0) {
                setSelectedScreenshot(data.screenshots[0]);
            }
        } catch (e) {
            console.error('Failed to load screenshots:', e);
        }
    };

    // ─── Search Handler ───
    const handleSearch = async () => {
        if (!query.trim()) return;

        setLoading(true);
        setResults([]);
        setError('');
        setProgress('Queuing scrape job...');
        setHasSearched(true);
        setTaskId(null);
        setShowDebug(false);
        setScreenshots([]);

        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }

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
                include_facebook: includeFacebook,
                include_gumtree: includeGumtree,
                email: fbEmail || undefined,
                password: fbPassword || undefined,
            };

            const { task_id } = await startScrape(scrapeRequest);

            setTaskId(task_id);
            setProgress(`Job queued: ${task_id.slice(0, 8)}... Polling...`);

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

                        const fbCount = status.result?.facebook_count || 0;
                        const gtCount = status.result?.gumtree_count || 0;
                        setProgress(`Found ${listings.total || 0} total listings (FB: ${fbCount}, Gumtree: ${gtCount})`);

                        // If Facebook was requested but returned 0, show debug option
                        if (includeFacebook && fbCount === 0) {
                            await loadScreenshots();
                        }

                    } else if (status.status === 'FAILURE') {
                        clearInterval(pollRef.current);
                        pollRef.current = null;

                        const errorMsg = status.result?.error || '';
                        if (errorMsg.includes('credentials') || errorMsg.includes('login')) {
                            setError('❌ Facebook login required or failed. Provide credentials above, or disable Facebook and use Gumtree only.');
                        } else if (errorMsg.includes('blocked') || errorMsg.includes('CAPTCHA')) {
                            setError('❌ Facebook blocked the request. Try Gumtree instead, or use login credentials.');
                        } else {
                            setError('❌ Scraping failed. ' + errorMsg);
                        }

                        // Load screenshots on failure too
                        if (includeFacebook) {
                            await loadScreenshots();
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
                <meta name="description" content="Search cars from Facebook Marketplace & Gumtree" />
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

                    {/* ─── Source Toggle Checkboxes ─── */}
                    <div style={styles.sourceToggleRow}>
                        <label style={styles.sourceLabel}>
                            <input
                                type="checkbox"
                                checked={includeFacebook}
                                onChange={(e) => setIncludeFacebook(e.target.checked)}
                                style={styles.sourceCheckbox}
                            />
                            <span style={styles.sourceText}>
                                <span style={styles.fbIcon}>📘</span> Facebook Marketplace
                                <span style={styles.sourceHint}>(requires login)</span>
                            </span>
                        </label>
                        <label style={styles.sourceLabel}>
                            <input
                                type="checkbox"
                                checked={includeGumtree}
                                onChange={(e) => setIncludeGumtree(e.target.checked)}
                                style={styles.sourceCheckbox}
                            />
                            <span style={styles.sourceText}>
                                <span style={styles.gtIcon}>🌿</span> Gumtree
                                <span style={styles.sourceHint}>(no login needed)</span>
                            </span>
                        </label>
                    </div>

                    {/* ─── Facebook Login Section (Collapsible) ─── */}
                    {includeFacebook && (
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
                                        💡 <strong>Without login:</strong> Facebook may block or return limited results.<br/>
                                        💡 <strong>With login:</strong> Full access, but account may face checkpoint from datacenter IPs.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

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
                            {screenshots.length > 0 && (
                                <button
                                    onClick={() => setShowDebug(!showDebug)}
                                    style={styles.debugToggleBtn}
                                >
                                    {showDebug ? '🔼 Hide' : '🔽 Show'} Facebook Debug Screenshots ({screenshots.length})
                                </button>
                            )}
                        </div>
                    )}

                    {/* ─── Debug Screenshot Viewer ─── */}
                    {showDebug && screenshots.length > 0 && (
                        <div style={styles.debugPanel}>
                            <div style={styles.debugHeader}>
                                <h4 style={styles.debugTitle}>📸 Facebook Login Debug Screenshots</h4>
                                <p style={styles.debugSubtitle}>
                                    These show what Facebook displayed during the failed login attempt.
                                    If you see a CAPTCHA or checkpoint, Facebook blocked the datacenter IP.
                                </p>
                            </div>

                            <div style={styles.screenshotSelector}>
                                {screenshots.map((ss, idx) => (
                                    <button
                                        key={ss.filename}
                                        onClick={() => setSelectedScreenshot(ss)}
                                        style={{
                                            ...styles.ssThumb,
                                            backgroundColor: selectedScreenshot?.filename === ss.filename ? '#dbeafe' : '#f1f5f9'
                                        }}
                                    >
                                        Screenshot {idx + 1}
                                        <span style={styles.ssTime}>{ss.timestamp}</span>
                                    </button>
                                ))}
                            </div>

                            {selectedScreenshot && (
                                <div style={styles.ssViewer}>
                                    <img
                                        src={`${API_URL}/debug/screenshots/${selectedScreenshot.filename}`}
                                        alt="Facebook login page debug"
                                        style={styles.ssImage}
                                    />
                                    <p style={styles.ssCaption}>
                                        Timestamp: {selectedScreenshot.timestamp} | 
                                        <a href={`${API_URL}/debug/screenshots/${selectedScreenshot.filename}`} target="_blank" rel="noopener noreferrer" style={styles.ssLink}>
                                            Open in new tab
                                        </a>
                                    </p>
                                </div>
                            )}
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
                            <p style={styles.loadingText}>Scraping... This may take 30-60 seconds</p>
                            <p style={styles.loadingSubtext}>
                                {includeFacebook && fbEmail 
                                    ? `Facebook: ${fbEmail.slice(0, 3)}***... | ` 
                                    : includeFacebook ? 'Facebook: no login | ' : ''}
                                {includeGumtree ? 'Gumtree: active' : ''}
                            </p>
                        </div>
                    )}

                    {!loading && hasSearched && results.length === 0 && !error && (
                        <div style={styles.emptyState}>
                            <p style={styles.emptyTitle}>No cars found</p>
                            <p style={styles.emptySubtitle}>
                                {includeGumtree && !includeFacebook
                                    ? 'Try different search terms or enable Facebook with login.'
                                    : 'Try providing Facebook login for better results, or use different search terms.'}
                            </p>
                        </div>
                    )}

                    {!loading && results.length > 0 && (
                        <div>
                            <div style={styles.resultsMeta}>
                                Showing <strong>{results.length}</strong> results
                                {results.some(r => r.source === 'facebook') && (
                                    <span style={styles.fbSourceTag}>📘 Facebook</span>
                                )}
                                {results.some(r => r.source === 'gumtree') && (
                                    <span style={styles.gtSourceTag}>🌿 Gumtree</span>
                                )}
                                {fbEmail && <span style={styles.loggedInTag}>🔐 Logged in</span>}
                            </div>

                            <div style={styles.grid}>
                                {results.map((car, index) => (
                                    <div key={car.facebook_id || car.listing_id || index} style={styles.card}>
                                        <div style={styles.imageContainer}>
                                            {(() => {
                                                const images = parseImages(car.image_urls);
                                                const firstImage = images.length > 0 ? images[0] : car.image_url;
                                                return firstImage ? (
                                                    <a href={car.listing_url} target="_blank" rel="noopener noreferrer">
                                                        <img
                                                            src={firstImage}
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

                                            {/* Source Badge */}
                                            <span style={{
                                                ...styles.sourceBadge,
                                                backgroundColor: car.source === 'gumtree' ? '#dcfce7' : '#dbeafe',
                                                color: car.source === 'gumtree' ? '#166534' : '#1e40af'
                                            }}>
                                                {car.source === 'gumtree' ? '🌿 Gumtree' : '📘 Facebook'}
                                            </span>
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
                                                View on {car.source === 'gumtree' ? 'Gumtree' : 'Facebook'} →
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
                            <p style={styles.initialSubtitle}>Enter a car make or model to search across Australia</p>
                            <p style={styles.initialNote}>
                                💡 <strong>Pro tip:</strong> Enable Gumtree for instant results without login.<br/>
                                📘 Facebook requires credentials but may be blocked from cloud servers.<br/>
                                🔒 Credentials are only used for this session and optional to save.
                            </p>
                        </div>
                    )}
                </div>
            </main>

            <footer style={styles.footer}>
                © 2026 CarMates. Data from Facebook Marketplace & Gumtree. Built with Playwright + Celery + PostgreSQL.
            </footer>

            <style jsx global>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// ─── Updated Styles with Source Toggles & Debug Viewer ───
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
        alignItems: 'stretch',
        marginBottom: '1rem'
    },
    searchInput: {
        flex: 1,
        minWidth: '250px',
        padding: '0.875rem 1rem',
        border: '2px solid #e2e8f0',
        borderRadius: '8px',
        fontSize: '1rem',
        outline: 'none',
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
        fontFamily: 'inherit',
        whiteSpace: 'nowrap'
    },

    // ─── Source Toggle Styles ───
    sourceToggleRow: {
        display: 'flex',
        gap: '1.5rem',
        marginBottom: '1rem',
        flexWrap: 'wrap',
        padding: '0.75rem',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        border: '1px solid #e2e8f0'
    },
    sourceLabel: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        cursor: 'pointer',
        fontSize: '0.875rem',
        fontWeight: 500
    },
    sourceCheckbox: {
        width: '18px',
        height: '18px',
        cursor: 'pointer'
    },
    sourceText: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.375rem'
    },
    fbIcon: {
        fontSize: '1rem'
    },
    gtIcon: {
        fontSize: '1rem'
    },
    sourceHint: {
        fontSize: '0.75rem',
        color: '#94a3b8',
        fontWeight: 400
    },

    // ─── Login Section Styles ───
    loginSection: {
        marginTop: '0.5rem',
        borderTop: '1px solid #e2e8f0',
        paddingTop: '1rem'
    },
    loginToggle: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: 'none',
        border: 'none',
        color: '#64748b',
        fontSize: '0.875rem',
        cursor: 'pointer',
        padding: '0.5rem 0',
        fontFamily: 'inherit',
        width: '100%',
        textAlign: 'left'
    },
    loginForm: {
        marginTop: '0.75rem',
        padding: '1rem',
        backgroundColor: '#fefce8',
        borderRadius: '8px',
        border: '1px solid #fde047'
    },
    loginRow: {
        display: 'flex',
        gap: '0.75rem',
        marginBottom: '0.75rem',
        flexWrap: 'wrap'
    },
    loginInput: {
        flex: 1,
        minWidth: '200px',
        padding: '0.625rem 0.875rem',
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        fontSize: '0.875rem',
        fontFamily: 'inherit'
    },
    loginOptions: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.5rem'
    },
    rememberLabel: {
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.875rem',
        color: '#374151',
        cursor: 'pointer'
    },
    checkbox: {
        width: '16px',
        height: '16px',
        cursor: 'pointer'
    },
    clearCredsBtn: {
        background: 'none',
        border: 'none',
        color: '#dc2626',
        fontSize: '0.75rem',
        cursor: 'pointer',
        fontFamily: 'inherit',
        textDecoration: 'underline'
    },
    loginHint: {
        marginTop: '0.75rem',
        fontSize: '0.75rem',
        color: '#92400e',
        lineHeight: 1.5
    },

    // ─── Debug Panel Styles ───
    debugToggleBtn: {
        marginTop: '0.75rem',
        padding: '0.5rem 1rem',
        backgroundColor: '#fef3c7',
        border: '1px solid #fde047',
        borderRadius: '6px',
        fontSize: '0.875rem',
        cursor: 'pointer',
        color: '#92400e',
        fontFamily: 'inherit',
        fontWeight: 500
    },
    debugPanel: {
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: '#fefce8',
        borderRadius: '8px',
        border: '1px solid #fde047'
    },
    debugHeader: {
        marginBottom: '1rem'
    },
    debugTitle: {
        margin: '0 0 0.5rem',
        fontSize: '1rem',
        color: '#92400e'
    },
    debugSubtitle: {
        margin: 0,
        fontSize: '0.75rem',
        color: '#a16207',
        lineHeight: 1.5
    },
    screenshotSelector: {
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1rem',
        flexWrap: 'wrap'
    },
    ssThumb: {
        padding: '0.5rem 0.75rem',
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        fontSize: '0.75rem',
        cursor: 'pointer',
        fontFamily: 'inherit',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.25rem'
    },
    ssTime: {
        fontSize: '0.625rem',
        color: '#64748b'
    },
    ssViewer: {
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        overflow: 'hidden',
        backgroundColor: 'white'
    },
    ssImage: {
        width: '100%',
        maxHeight: '400px',
        objectFit: 'contain',
        display: 'block'
    },
    ssCaption: {
        padding: '0.75rem',
        margin: 0,
        fontSize: '0.75rem',
        color: '#64748b',
        backgroundColor: '#f8fafc',
        borderTop: '1px solid #e2e8f0'
    },
    ssLink: {
        color: '#2563eb',
        textDecoration: 'none'
    },

    progressBar: {
        marginTop: '1rem',
        padding: '0.75rem 1rem',
        backgroundColor: '#eff6ff',
        borderRadius: '8px',
        border: '1px solid #bfdbfe',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    progressText: {
        color: '#1e40af',
        fontSize: '0.875rem',
        fontWeight: 500
    },
    taskId: {
        color: '#64748b',
        fontSize: '0.75rem',
        fontFamily: 'monospace'
    },
    errorBox: {
        marginTop: '1rem',
        padding: '0.75rem 1rem',
        backgroundColor: '#fef2f2',
        borderRadius: '8px',
        border: '1px solid #fecaca'
    },
    errorText: {
        color: '#dc2626',
        fontSize: '0.875rem',
        lineHeight: 1.5,
        margin: 0
    },
    exportBar: {
        display: 'flex',
        gap: '0.75rem',
        marginBottom: '1rem'
    },
    exportBtn: {
        padding: '0.5rem 1rem',
        backgroundColor: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        fontSize: '0.875rem',
        cursor: 'pointer',
        color: '#374151'
    },
    resultsSection: {
        minHeight: '200px'
    },
    resultsMeta: {
        marginBottom: '1rem',
        color: '#64748b',
        fontSize: '0.875rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        flexWrap: 'wrap'
    },
    fbSourceTag: {
        padding: '2px 8px',
        backgroundColor: '#dbeafe',
        color: '#1e40af',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600
    },
    gtSourceTag: {
        padding: '2px 8px',
        backgroundColor: '#dcfce7',
        color: '#166534',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600
    },
    loggedInTag: {
        padding: '2px 8px',
        backgroundColor: '#dcfce7',
        color: '#166534',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600
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
        border: '1px solid #e2e8f0'
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
    conditionBadge: {
        position: 'absolute',
        top: '8px',
        left: '8px',
        padding: '4px 10px',
        borderRadius: '9999px',
        fontSize: '0.7rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        backgroundColor: '#fef3c7',
        color: '#92400e'
    },
    sourceBadge: {
        position: 'absolute',
        top: '8px',
        right: '8px',
        padding: '4px 10px',
        borderRadius: '9999px',
        fontSize: '0.7rem',
        fontWeight: 700,
        textTransform: 'uppercase'
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
        color: '#374151',
        fontWeight: 500
    },
    loadingSubtext: {
        color: '#94a3b8',
        fontSize: '0.875rem',
        marginTop: '0.5rem'
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
        fontSize: '0.875rem',
        lineHeight: 1.5
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
    initialNote: {
        fontSize: '0.75rem',
        color: '#94a3b8',
        marginTop: '1rem',
        lineHeight: 1.5
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
