import { useState } from 'react';
import { Search } from 'lucide-react';

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <div className="search-input-wrapper">
        <Search className="search-icon" size={20} />
        <input
          type="text"
          name="search"
          id="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search cars (e.g., Toyota Camry, BMW X5)..."
          className="search-input"
          autoComplete="off"
        />
        <button 
          type="submit" 
          className="search-button"
          disabled={loading || !query.trim()}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </form>
  );
}
