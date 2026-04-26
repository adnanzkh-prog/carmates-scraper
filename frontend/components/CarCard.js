import { MapPin, Gauge, Calendar, DollarSign, ExternalLink } from 'lucide-react';

export default function CarCard({ car }) {
  const formatPrice = (price) => {
    if (!price) return 'Price on request';
    return `$${price.toLocaleString()}`;
  };

  const formatOdometer = (km) => {
    if (!km) return 'N/A';
    return `${km.toLocaleString()} km`;
  };

  return (
    <div className="car-card">
      <div className="car-image">
        {car.images && car.images[0] ? (
          <img src={car.images[0]} alt={car.title} loading="lazy" />
        ) : (
          <div className="car-image-placeholder">No Image</div>
        )}
      </div>

      <div className="car-content">
        <h3 className="car-title">{car.title}</h3>

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
          <span className="car-source">{car.source}</span>
          <a
            href={car.url}
            target="_blank"
            rel="noopener noreferrer"
            className="view-link"
          >
            View <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
}
