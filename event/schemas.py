from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
