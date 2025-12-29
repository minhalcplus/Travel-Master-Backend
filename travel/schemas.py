from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime

# =====================================================
# County Schemas
# =====================================================

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


# =====================================================
# Stop Schemas
# =====================================================

class StopBase(BaseModel):
    name: str
    location: str
    lat: float
    lng: float


class StopCreate(StopBase):
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
    county: Optional[CountyOut] = None

    @field_serializer("county")
    def serialize_county(self, county: Optional[CountyOut], _info):
        return county.name if county else None

    class Config:
        from_attributes = True

# GeoJSON Schemas
class GeoJSONGeometry(BaseModel):   
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]


# =====================================================
# StopNode Schemas (IMPORTANT PART)
# =====================================================

# ---- Input schema (CREATE / UPDATE)
class StopNodeBase(BaseModel):
    stop_id: int
    price: float


class StopNodeCreate(StopNodeBase):
    pass


# ---- Lightweight reference (prevents recursion)
class StopNodeRef(BaseModel):
    id: int
    stop_id: int
    price: float

    class Config:
        from_attributes = True
class StopProperties(BaseModel):
    id: int

# ---- Output schema
class StopNodeOut(BaseModel):
    id: int
    stop_id: int
    price: float

    stop: Optional[StopOut] = None
    next_stop_node: Optional[StopNodeRef] = None
    previous_stop_node: List[StopNodeRef] = []

    all_previous_stop_nodes: List[StopNodeRef] = []

    class Config:
        from_attributes = True


# =====================================================
# Route Schemas
# =====================================================

class RouteCreate(BaseModel):
    name: str
    start_location: str
    destination: str
    is_active: bool
    stop_nodes: List[StopNodeBase]  # ORDER MATTERS


class StopGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: StopProperties


class StopGeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[StopGeoJSONFeature]
class RouteOut(BaseModel):
    id: int
    name: str
    start_location: str
    destination: str
    is_active: bool
    stop_nodes: List[StopNodeOut] = []

    class Config:
        from_attributes = True


class RouteSummaryOut(BaseModel):
    id: int
    name: str
    start_location: str
    destination: str
    is_active: bool
    stop_count: int

    class Config:
        from_attributes = True


class RouteDetailOut(BaseModel):
    id: int
    name: str
    start_location: str
    destination: str
    is_active: bool
    stop_nodes: List[StopNodeOut] = []

    class Config:
        from_attributes = True

#group routes


class RouteGroupCreate(BaseModel):
    name: str
    route_ids: List[int]


class RouteGroupUpdate(BaseModel):
    name: str | None = None
    route_ids: List[int] | None = None


class RouteGroupOut(BaseModel):
    id: int
    name: str
    route_ids: List[int]

    class Config:
        from_attributes = True


class RouteGroupDetailedOut(BaseModel):
    id: int
    name: str
    routes: List[RouteDetailOut]

    class Config:
        from_attributes = True
