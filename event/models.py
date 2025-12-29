from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.app.database import Base
from datetime import date, time, datetime
import enum
from sqlalchemy import String, Text, DateTime, Enum, JSON, Boolean, ForeignKey, Date, Time, Integer, Float
from typing import Optional

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


class EventStatus(enum.Enum):
    LIVE = "live"
    HIDDEN = "hidden"
    OUT_OF_STOCK = "out_of_stock"

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), index=True)

    venue_id: Mapped[int] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE"),
        index=True
    )

    desktop_image: Mapped[str] = mapped_column(String(500))
    mobile_image: Mapped[str] = mapped_column(String(500))

    description: Mapped[str | None] = mapped_column(Text)

    # optional extra data (seo, tags, etc.)
    description_metadata: Mapped[dict | None] = mapped_column(JSON)

    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus),
        default=EventStatus.HIDDEN,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    venue: Mapped["Venue"] = relationship("Venue")

    days: Mapped[list["EventDay"]] = relationship(
        "EventDay",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventDay.event_date"
    )


class EventDay(Base):
    __tablename__ = "event_days"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        index=True
    )

    event_date: Mapped[date] = mapped_column(Date, index=True)

    gate_open_time: Mapped[time] = mapped_column(Time)

    # optional per-day note
    note: Mapped[str | None] = mapped_column(Text)

    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="days"
    )

    routes: Mapped[list["EventRoute"]] = relationship(
        "EventRoute",
        back_populates="event_day",
        cascade="all, delete-orphan"
    )

class EventRoute(Base):
    __tablename__ = "event_routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_day_id: Mapped[int] = mapped_column(
        ForeignKey("event_days.id", ondelete="CASCADE"),
        index=True
    )
    route_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    start_location: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    event_day: Mapped["EventDay"] = relationship(
        "EventDay",
        back_populates="routes"
    )

    stop_nodes: Mapped[list["EventStopNode"]] = relationship(
        "EventStopNode",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="EventStopNode.id"
    )

class EventStopNode(Base):
    __tablename__ = "event_stop_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("event_routes.id", ondelete="CASCADE")
    )
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id"))
    price: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    booking_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Branching/Linking
    next_stop_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_stop_nodes.id"), nullable=True
    )

    route: Mapped["EventRoute"] = relationship(
        "EventRoute", back_populates="stop_nodes"
    )
    stop: Mapped["travel.models.Stop"] = relationship("travel.models.Stop")

    # Self-reference for branching
    next_stop_node: Mapped["EventStopNode | None"] = relationship(
        "EventStopNode",
        remote_side=[id],
        uselist=False,
        backref="previous_stop_node"
    )