from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from datetime import datetime
from database import Base

class CarListing(Base):
    __tablename__ = "car_listings"

    id = Column(Integer, primary_key=True, index=True)
    facebook_id = Column(String, unique=True, index=True)
    title = Column(String)
    price = Column(Float, nullable=True)
    currency = Column(String, default="AUD")
    year = Column(Integer, nullable=True)
    odometer = Column(Integer, nullable=True)
    odometer_unit = Column(String, default="km")
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    listing_url = Column(String)
    image_urls = Column(Text, nullable=True)
    scrape_timestamp = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    make = Column(String, nullable=True)
    model = Column(String, nullable=True)
    condition = Column(String, nullable=True)

    __table_args__ = (
        Index("idx_price", "price"),
        Index("idx_year", "year"),
        Index("idx_location", "location"),
        Index("idx_ft_search", "title", "description", postgresql_using="gin"),
    )
