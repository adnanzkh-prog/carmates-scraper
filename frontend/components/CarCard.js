import { MapPin, Gauge, Calendar, DollarSign, ExternalLink, Shield, Star } from 'lucide-react';

export default function CarCard({ car }) {
  const formatPrice = (price) => {
    if (!price) return 'Price on request';
    return `$${price.toLocaleString()}`;
  };

  const formatOdometer = (km) => {
    if (!km) return 'N/A';
    return `${km.toLocaleString()} km`;
  };

  // Get source color
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

  // Get source text color
  const getSourceTextColor = (source) => {
    const colors = {
      'Carsales': '#1e40af',
      'eBay Australia': '#9d174d',
      'Gumtree': '#166534',
      'Facebook Marketplace': '#92400e',
      'Manual Submission': '#3730a3',
      'Sample Data': '#374151'
    };
    return colors[source] || '#374151';
  };

  return (
    <div className="car-card">
      {/* Image Section */}
      <div className="car-image">
        {car.images && car.images[0] ? (
          <a href={car.url} target="_blank" rel="noopener noreferrer">
            <img src={car.images[0]} alt={car.title} loading="lazy" />
          </a>
        ) : (
          <a href={car.url} target="_blank" rel="noopener noreferrer" className="car-image-placeholder">
            <span>🚗 No Image</span>
          </a>
        )}
        
        {/* Source Badge */}
        <span 
          className="source-badge"
          style={{ 
            background: getSourceColor(car.source),
            color: getSourceTextColor(car.source)
          }}
        >
          {car.source === 'Manual Submission' && '✅ '}
          {car.source === 'Facebook Marketplace' && '⚠️ '}
          {car.source}
        </span>

        {/* Accuracy Score */}
        {car.accuracy_score > 0 && (
          <span className="accuracy-badge" title="Relevance score (0-100)">
            <Star size={10} fill="#fbbf24" color="#fbbf24" />
            {car.accuracy_score}%
          </span>
        )}

        {/* Verified Badge */}
        {car.verified && (
          <span className="verified-badge" title="Manually verified">
            <Shield size={10} />
            Verified
          </span>
        )}
      </div>
      
      <div className="car-content">
        {/* Title as clickable link */}
        <h3 className="car-title">
          <a href={car.url} target="_blank" rel="noopener noreferrer" className="title-link">
            {car.title}
          </a>
        </h3>
        
        <div className="car-price">
          <DollarSign size={18} />
          <span>{formatPrice(car.price)}</span>
        </div>

        <div className="car-details">
          <div className="detail-item">
            <Calendar size={14} />
            <span>{car.year || 'N/A'}</span>
          </div>
          <div className="detail-item">
            <Gauge size={14} />
            <span>{formatOdometer(car.odometer)}</span>
          </div>
          <div className="detail-item">
            <MapPin size={14} />
            <span>{car.location || 'Australia'}</span>
          </div>
        </div>

        <div className="car-footer">
          <span className="car-date">
            Listed: {new Date(car.scraped_at).toLocaleDateString('en-AU')}
          </span>
          <a 
            href={car.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="view-link"
          >
            View Listing <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
}
