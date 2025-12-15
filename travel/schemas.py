from pydantic import BaseModel, Field, computed_field, field_serializer
from typing import List, Optional, Any, Dict
from datetime import datetime


# County Schemas
class CountyBase(BaseModel):
    name: str
    short_code: str
    telephone_code: str
    
class CountyCreate(CountyBase):
    pass

class CountyUpdate(CountyBase):
    pass

class CountyOut(CountyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StopBase(BaseModel):
    name: str
    location: str
    lat: float
    lng: float

class StopCreate(StopBase):
    county: Optional[str] = None
    county_id: Optional[int] = None

class StopUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    county_id: Optional[int] = None

class StopOut(StopBase):
    id: int
    county_id: int
    created_at: datetime
    updated_at: datetime
    
    # Matches the ORM relationship
    county: Optional[CountyOut] = None

    @field_serializer('county')
    def serialize_county(self, county: Optional[CountyOut], _info):
        return county.name if county else None

    class Config:
        from_attributes = True

# GeoJSON Schemas
class GeoJSONGeometry(BaseModel):   
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]

class StopProperties(BaseModel):
    id: int
    name: str
    county_id: int
    county_name: Optional[str] = None
    location: str
    created_at: datetime
    updated_at: datetime


class StopGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: StopProperties

class StopGeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[StopGeoJSONFeature]

# # Bus Schemas
# class BusBase(BaseModel):
#     plate_number: str
#     capacity: int
#     model: Optional[str] = None
#     driver_id: Optional[int] = None

# class BusCreate(BusBase):
#     pass

# class Bus(BusBase):
#     id: int

#     class Config:
#         from_attributes = True

# # Route Schemas
# class RouteBase(BaseModel):
#     name: str
#     source: Dict[str, Any] # GeoJSON
#     destination: Dict[str, Any] # GeoJSON

# class RouteCreate(RouteBase):
#     pass

# class Route(RouteBase):
#     id: int

#     class Config:
#         from_attributes = True



# # Event Stop Schemas
# class EventStopBase(BaseModel):
#     stop_id: int
#     price: float
#     arrival_time: Optional[datetime] = None

# class EventStopCreate(EventStopBase):
#     pass

# # class EventStop(EventStopBase):
# #     id: int
# #     stop: Stop

# #     class Config:
# #         from_attributes = True

# # Event Schemas
# class EventBase(BaseModel):
#     title: str
#     route_id: int
#     from_date: datetime
#     to_date: datetime
#     total_tickets: int
#     driver_id: Optional[int] = None

# class EventCreate(EventBase):
#     stops: List[EventStopCreate] = []

# class Event(EventBase):
#     id: int
#     available_tickets: int
#     bus_id: Optional[int] = None
#     route: Optional[Route] = None
#     event_stops: List[EventStop] = []
#     # driver: Optional[Driver] = None # Driver is now DriverProfile, complex to include full profile here, maybe just ID or basic info if needed.

#     class Config:
#         from_attributes = True

# # Booking Schemas
# class BookingBase(BaseModel):
#     event_id: int
#     seats: int

# class BookingCreate(BookingBase):
#     pass

# class Booking(BookingBase):
#     id: int
#     user_id: int
#     total_price: float
#     status: str
#     created_at: datetime
#     event: Event

#     class Config:
#         from_attributes = True
