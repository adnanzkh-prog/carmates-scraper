import { MapPin, Gauge, Calendar, DollarSign, ExternalLink, Star, Shield, AlertTriangle } from 'lucide-react';

export default function CarCard({ car }) {
  const formatPrice = (price) => {
    if (!price) return 'Contact for price';
    return `$${price.toLocaleString()}`;
  };

  const formatOdometer = (km) => {
    if (!km) return 'N/A';
    return `${km.toLocaleString()} km`;
  };

  const getAccuracyColor = (score) => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#fbbf24';
    return '#ef4444';
  };

  const getSourceStyle = (source) => {
    const styles = {
      'Carsales': { bg: '#dbeafe', text: '#1e40af', icon: '🏢' },
      'eBay Australia': { bg: '#fce7f3', text: '#9d174d', icon: '🛒' },
      'Facebook Marketplace': { bg: '#fef3c7', text: '#92400e', icon: '👤' },
      'Manual': { bg: '#e0e7ff', text: '#3730a3', icon: '✅' }
    };
    return styles[source] || { bg: '#f3f4f6', text: '#374151', icon: '📌' };
  };

  const sourceStyle = getSourceStyle(car.source);

  return (
    <div className="car-card">
      <div className="car-image">
        {car.images && car.images[0] ? (
          <a href={car.url} target="_blank" rel="noopener noreferrer">
            <img src={car.images[0]} alt={car.title} loading="lazy" />
          </a>
        ) : (
          <a href={car.url} target="_blank" rel="noopener noreferrer" className="car-image-placeholder">
            <span>{sourceStyle.icon} No Image</span>
          </a>
        )}
        
        {/* Source Badge */}
        <span className="source-badge" style={{ background: sourceStyle.bg, color: sourceStyle.text }}>
          {sourceStyle.icon} {car.source}
        </span>

        {/* Accuracy Score */}
        <div className="accuracy-badge" style={{ borderColor: getAccuracyColor(car.accuracy_score) }}>
          <Star size={10} fill={getAccuracyColor(car.accuracy_score)} color={getAccuracyColor(car.accuracy_score)} />
          <span>{car.accuracy_score}% match</span>
        </div>

        {/* Warning for low accuracy */}
        {car.accuracy_score < 60 && car.source === 'Facebook Marketplace' && (
          <div className="accuracy-warning" title="Low accuracy — verify before contacting">
            <AlertTriangle size={12} />
          </div>
        )}
      </div>
      
      <div className="car-content">
        <h3 className="car-title">
          <a href={car.url} target="_blank" rel="noopener noreferrer">
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
            {new Date(car.scraped_at).toLocaleDateString('en-AU')}
          </span>
          <a href={car.url} target="_blank" rel="noopener noreferrer" className="view-link">
            View <ExternalLink size={12} />
          </a>
        </div>
      </div>

      <style jsx>{`
        .car-card {
          background: white;
          border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .car-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .car-image {
          height: 180px;
          background: #f8fafc;
          overflow: hidden;
          position: relative;
        }
        
        .car-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.3s;
        }
        
        .car-card:hover .car-image img {
          transform: scale(1.05);
        }
        
        .car-image-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #94a3b8;
          text-decoration: none;
          font-size: 0.875rem;
        }
        
        .source-badge {
          position: absolute;
          top: 8px;
          left: 8px;
          padding: 4px 10px;
          border-radius: 999px;
          font-size: 0.7rem;
          font-weight: 700;
          z-index: 2;
        }
        
        .accuracy-badge {
          position: absolute;
          top: 8px;
          right: 8px;
          background: rgba(0,0,0,0.8);
          color: white;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 4px;
          z-index: 2;
          border: 2px solid;
        }
        
        .accuracy-warning {
          position: absolute;
          bottom: 8px;
          right: 8px;
          background: #ef4444;
          color: white;
          padding: 4px;
          border-radius: 4px;
          z-index: 2;
        }
        
        .car-content {
          padding: 1rem;
        }
        
        .car-title {
          font-size: 1rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
          line-height: 1.4;
        }
        
        .car-title a {
          color: #1e293b;
          text-decoration: none;
        }
        
        .car-title a:hover {
          color: #2563eb;
        }
        
        .car-price {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: #2563eb;
          font-size: 1.25rem;
          font-weight: 700;
          margin-bottom: 0.75rem;
        }
        
        .car-details {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
          flex-wrap: wrap;
        }
        
        .detail-item {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-size: 0.875rem;
          color: #64748b;
        }
        
        .car-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 0.75rem;
          border-top: 1px solid #e2e8f0;
        }
        
        .car-date {
          font-size: 0.75rem;
          color: #94a3b8;
        }
        
        .view-link {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: #2563eb;
          text-decoration: none;
          font-size: 0.875rem;
          font-weight: 600;
        }
        
        .view-link:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}
