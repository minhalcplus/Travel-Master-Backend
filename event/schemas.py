from pydantic import BaseModel
from typing import List, Optional
from datetime import date, time, datetime
from travel import schemas as travel_schemas

class VenueBase(BaseModel):
    name: str
    location: str
    lat: float
    lng: float

class VenueCreate(VenueBase):
    pass

class VenueUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class VenueOut(VenueBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# GeoJSON Schemas
class GeoJSONGeometry(BaseModel):   
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]

class VenueProperties(BaseModel):
    id: int
    name: str
    location: str
    created_at: datetime
    updated_at: datetime

class VenueGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: VenueProperties

class VenueGeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[VenueGeoJSONFeature]

# --- Event Route & StopNode Schemas ---

class EventStopNodeBase(BaseModel):
    id: Optional[int] = None # Added to support user's payload structure
    stop_id: int
    price: float
    is_active: bool = True
    booking_capacity: Optional[int] = None

class EventStopNodeCreate(EventStopNodeBase):
    pass

class EventStopNodeRef(BaseModel):
    id: int
    stop_id: int
    price: float
    
    class Config:
        from_attributes = True

class EventStopNodeOut(EventStopNodeBase):
    id: int
    next_stop_id: Optional[int] = None
    next_stop_node: Optional[EventStopNodeRef] = None
    previous_stop_node: List[EventStopNodeRef] = []
    stop: Optional[travel_schemas.StopOut] = None
    
    class Config:
        from_attributes = True

class EventRouteBase(BaseModel):
    name: Optional[str] = None
    start_location: str
    destination: str
    is_active: bool = True
    route_template_name: Optional[str] = None # Fallback for name
    group_id: Optional[int] = None

class EventRouteCreate(EventRouteBase):
    route_template_id: Optional[int] = None
    stop_nodes: List[EventStopNodeBase]

class EventRouteOut(EventRouteBase):
    id: int
    route_template_id: Optional[int] = None
    group_id: Optional[int] = None
    stop_nodes: List[EventStopNodeOut] = []

    class Config:
        from_attributes = True

# EVENT SCHEMAS
class EventDayCreate(BaseModel):
    event_date: date
    gate_open_time: time
    note: str | None = None
    routes: List[EventRouteCreate] = []

class EventCreateWithDays(BaseModel):
    name: str
    venue_id: int
    desktop_image: str
    mobile_image: str
    description: str | None = None
    description_metadata: dict | None = None
    status: Optional[str] = "hidden"
    days: list[EventDayCreate]

class EventDayOut(BaseModel):
    id: int
    event_id: int
    event_date: date
    gate_open_time: time
    note: Optional[str]
    routes: List[EventRouteOut] = []

    class Config:
        from_attributes = True

class EventOut(BaseModel):
    id: int
    name: str
    venue_id: int
    desktop_image_url: str
    mobile_image_url: str
    description: Optional[str]
    description_metadata: Optional[dict]
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    venue: Optional[VenueOut]
    days: List[EventDayOut] = []

    class Config:
        from_attributes = True

class EventDayRoutesUpdate(BaseModel):
    event_id: int
    event_day_id: int
    event_date: date
    routes: List[EventRouteCreate]

class EventRouteSummaryOut(BaseModel):
    id: int
    name: str
    event_day_id: int
    route_template_id: Optional[int] = None
    group_id: Optional[int] = None
    start_location: str
    destination: str
    is_active: bool
    stop_count: int

    class Config:
        from_attributes = True