from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from core.app.database import Base
from datetime import datetime

class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_geojson(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.lng, self.lat]
            },
            "properties": {
                "id": self.id,
                "name": self.name,
                "location": self.location,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }
        }
