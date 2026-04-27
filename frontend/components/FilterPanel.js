import { useState } from 'react';
import { SlidersHorizontal, ChevronDown } from 'lucide-react';

export default function FilterPanel({ filters, onFilterChange }) {
  const [isOpen, setIsOpen] = useState(false);

  const makes = ['All', 'Toyota', 'Honda', 'Ford', 'BMW', 'Mercedes', 'Audi', 'Mazda', 'Hyundai', 'Kia', 'Volkswagen', 'Nissan'];
  const locations = ['All', 'Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide'];

  const handleChange = (field, value) => {
    onFilterChange({ ...filters, [field]: value });
  };

  return (
    <div className="filter-panel">
      <button 
        className="filter-toggle"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <SlidersHorizontal size={18} />
        <span>Filters</span>
        <ChevronDown 
          size={16} 
          className={`chevron ${isOpen ? 'open' : ''}`}
        />
      </button>
      
      {isOpen && (
        <div className="filter-content">
          <div className="filter-group">
            <label htmlFor="make-filter">Make</label>
            <select 
              id="make-filter"
              value={filters.make || 'All'} 
              onChange={(e) => handleChange('make', e.target.value === 'All' ? '' : e.target.value)}
            >
              {makes.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="min-price">Min Price ($)</label>
              <input
                id="min-price"
                type="number"
                value={filters.min_price || ''}
                onChange={(e) => handleChange('min_price', e.target.value)}
                placeholder="0"
              />
            </div>
            <div className="filter-group">
              <label htmlFor="max-price">Max Price ($)</label>
              <input
                id="max-price"
                type="number"
                value={filters.max_price || ''}
                onChange={(e) => handleChange('max_price', e.target.value)}
                placeholder="999999"
              />
            </div>
          </div>

          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="year-from">Year From</label>
              <input
                id="year-from"
                type="number"
                value={filters.year_from || ''}
                onChange={(e) => handleChange('year_from', e.target.value)}
                placeholder="1900"
              />
            </div>
            <div className="filter-group">
              <label htmlFor="year-to">Year To</label>
              <input
                id="year-to"
                type="number"
                value={filters.year_to || ''}
                onChange={(e) => handleChange('year_to', e.target.value)}
                placeholder="2026"
              />
            </div>
          </div>

          <div className="filter-group">
            <label htmlFor="location-filter">Location</label>
            <select 
              id="location-filter"
              value={filters.location || 'All'} 
              onChange={(e) => handleChange('location', e.target.value === 'All' ? '' : e.target.value)}
            >
              {locations.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
