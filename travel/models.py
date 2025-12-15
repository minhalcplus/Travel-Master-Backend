from sqlalchemy import String, Integer, ForeignKey, DateTime, Float, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.app.database import Base
from datetime import datetime
from typing import List, Optional, Any

# class Bus(Base):
#     __tablename__ = "buses"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     plate_number: Mapped[str] = mapped_column(String, unique=True, index=True)
#     capacity: Mapped[int] = mapped_column(Integer)
#     model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
#     # Link to DriverProfile
#     driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("DriverProfiles.id"), nullable=True)

#     # Relationships
#     driver: Mapped["auth.models.DriverProfile"] = relationship("auth.models.DriverProfile", back_populates="bus")
#     events: Mapped[List["Event"]] = relationship("Event", back_populates="bus")


# class Route(Base):
#     __tablename__ = "routes"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     name: Mapped[str] = mapped_column(String, index=True)
#     source: Mapped[dict] = mapped_column(JSON) # GeoJSON Point
#     destination: Mapped[dict] = mapped_column(JSON) # GeoJSON Point
    
    # Relationships
    # events: Mapped[List["Event"]] = relationship("Event", back_populates="route")


class County(Base):
    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    short_code: Mapped[str] = mapped_column(String(10), unique=True)
    telephone_code: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    county_id: Mapped[int] = mapped_column(ForeignKey("counties.id"), index=True)
    location: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to County
    county: Mapped["County"] = relationship("County", backref="stops")

    # Relationship to EventStop
    # event_stops: Mapped[List["EventStop"]] = relationship(
    #     "EventStop",
    #     back_populates="stop",
    #     cascade="all, delete-orphan"
    # )

    # GeoJSON factory method
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
                "county_id": self.county_id,
                "county_name": self.county.name if self.county else None,
                "location": self.location,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            },
        }


# class Event(Base):
#     __tablename__ = "events"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     title: Mapped[str] = mapped_column(String, index=True)
    
#     # Derived from Route
#     route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"))
    
#     from_date: Mapped[datetime] = mapped_column(DateTime)
#     to_date: Mapped[datetime] = mapped_column(DateTime)
#     total_tickets: Mapped[int] = mapped_column(Integer)
#     available_tickets: Mapped[int] = mapped_column(Integer)
    
#     driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("DriverProfiles.id"), nullable=True)
#     bus_id: Mapped[Optional[int]] = mapped_column(ForeignKey("buses.id"), nullable=True)

#     # Relationships
#     route: Mapped["Route"] = relationship("Route", back_populates="events")
#     driver: Mapped["auth.models.DriverProfile"] = relationship("auth.models.DriverProfile", back_populates="events")
#     # bus: Mapped["Bus"] = relationship("Bus", back_populates="events")
#     # event_stops: Mapped[List["EventStop"]] = relationship("EventStop", back_populates="event")
#     bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="event")


# class EventStop(Base):
#     __tablename__ = "event_stops"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
#     stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id"))
#     price: Mapped[float] = mapped_column(Float)
#     arrival_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

#     # Relationships
#     event: Mapped["Event"] = relationship("Event", back_populates="event_stops")
#     stop: Mapped["Stop"] = relationship("Stop", back_populates="event_stops")



# class Booking(Base):
#     __tablename__ = "bookings"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
#     event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
#     seats: Mapped[int] = mapped_column(Integer)
#     total_price: Mapped[float] = mapped_column(Float)
#     status: Mapped[str] = mapped_column(String, default="confirmed")
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

#     # Relationships
#     event: Mapped["Event"] = relationship("Event", back_populates="bookings")
#     user: Mapped["auth.models.User"] = relationship("auth.models.User", back_populates="bookings")

