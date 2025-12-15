from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.app.database import get_db
from . import models, schemas
from auth.models import User, DriverProfile

router = APIRouter(prefix="/travel", tags=["Travel"])

# --- County Routes ---
@router.post("/counties/", response_model=schemas.CountyOut)
def create_county(county: schemas.CountyCreate, db: Session = Depends(get_db)):
    """
    Create a new county.
    """
    # Check if county with same name or short_code already exists
    existing = db.query(models.County).filter(
        (models.County.name == county.name) | 
        (models.County.short_code == county.short_code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="County with this name or short code already exists"
        )
    
    db_county = models.County(**county.model_dump())
    db.add(db_county)
    db.commit()
    db.refresh(db_county)
    return db_county

@router.get("/counties/", response_model=List[schemas.CountyOut])
def read_counties(db: Session = Depends(get_db)):
    """
    Get all counties.
    Returns: [{"id": 1, "name": "Dublin", "short_code": "DUB", "telephone_code": "01", ...}, ...]
    """
    counties = db.query(models.County).all()
    return counties

@router.get("/counties/{county_id}", response_model=schemas.CountyOut)
def read_county(county_id: int, db: Session = Depends(get_db)):
    """
    Get a single county by ID.
    """
    county = db.query(models.County).filter(models.County.id == county_id).first()
    if county is None:
        raise HTTPException(status_code=404, detail="County not found")
    return county

@router.put("/counties/{county_id}", response_model=schemas.CountyOut)
def update_county(county_id: int, county_update: schemas.CountyUpdate, db: Session = Depends(get_db)):
    """
    Update a county by ID.
    """
    county = db.query(models.County).filter(models.County.id == county_id).first()
    if county is None:
        raise HTTPException(status_code=404, detail="County not found")
    
    # Check if another county has the same name or short_code
    existing = db.query(models.County).filter(
        models.County.id != county_id,
        (models.County.name == county_update.name) | 
        (models.County.short_code == county_update.short_code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Another county with this name or short code already exists"
        )
    
    # Update all fields
    for key, value in county_update.model_dump().items():
        setattr(county, key, value)
    
    db.commit()
    db.refresh(county)
    return county

@router.delete("/counties/{county_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_county(county_id: int, db: Session = Depends(get_db)):
    """
    Delete a county by ID.
    """
    county = db.query(models.County).filter(models.County.id == county_id).first()
    if county is None:
        raise HTTPException(status_code=404, detail="County not found")
    
    db.delete(county)
    db.commit()
    return None

# # --- Route Routes ---
# @router.post("/routes/", response_model=schemas.Route)
# def create_route(route: schemas.RouteCreate, db: Session = Depends(get_db)):
#     db_route = models.Route(**route.model_dump())
#     db.add(db_route)
#     db.commit()
#     db.refresh(db_route)
#     return db_route

# @router.get("/routes/", response_model=List[schemas.Route])
# def read_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     routes = db.query(models.Route).offset(skip).limit(limit).all()
#     return routes

# # --- Bus Routes ---
# @router.post("/buses/", response_model=schemas.Bus)
# def create_bus(bus: schemas.BusCreate, db: Session = Depends(get_db)):
#     db_bus = models.Bus(**bus.model_dump())
#     db.add(db_bus)
#     db.commit()
#     db.refresh(db_bus)
#     return db_bus

# @router.get("/buses/", response_model=List[schemas.Bus])
# def read_buses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     buses = db.query(models.Bus).offset(skip).limit(limit).all()
#     return buses

# --- Stop Routes ---
@router.post("/stops/", response_model=schemas.StopBase)
def create_stop(stop: schemas.StopCreate, db: Session = Depends(get_db)):
    """
    Create a new stop with county name OR county_id.
    """
    stop_data = stop.model_dump()
    county_id = stop_data.get('county_id')
    county_name = stop_data.get('county')
    
    # 1. Try using county_id if provided
    if county_id:
        county = db.query(models.County).filter(models.County.id == county_id).first()
        if not county:
            raise HTTPException(status_code=404, detail=f"County with id {county_id} not found")
        stop_data['county_id'] = county.id
        if 'county' in stop_data:
            stop_data.pop('county')
    
    # 2. Try using county name if provided
    elif county_name:
        county = db.query(models.County).filter(models.County.name.ilike(county_name)).first()
        if not county:
            raise HTTPException(status_code=404, detail=f"County '{county_name}' not found")
        stop_data['county_id'] = county.id
        stop_data.pop('county') # Remove string name
        
    else:
        raise HTTPException(status_code=400, detail="Either 'county' (name) or 'county_id' must be provided")
    
    db_stop = models.Stop(**stop_data)
    db.add(db_stop)
    db.commit()
    db.refresh(db_stop)
    return db_stop


@router.get("/stops/", response_model=List[schemas.StopOut])
def read_stops(db: Session = Depends(get_db)):
    """
    Get all stops as a simple array.
    Returns: [{"id": 1, "name": "...", "county": "Dublin", "location": "...", "lat": ..., "lng": ...}, ...]
    """
    stops = db.query(models.Stop).all()
    return stops


@router.get("/stops/geojson", response_model=schemas.StopGeoJSONFeatureCollection)
def read_stops_geojson(db: Session = Depends(get_db)):
    """
    Get all stops as a GeoJSON FeatureCollection.
    This format is compatible with mapping libraries like Leaflet, Mapbox, etc.
    """
    stops = db.query(models.Stop).all()
    
    features = [stop.to_geojson() for stop in stops]
    
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/stops/{stop_id}", response_model=schemas.StopBase)
def read_stop(stop_id: int, db: Session = Depends(get_db)):
    stop = db.query(models.Stop).filter(models.Stop.id == stop_id).first()
    if stop is None:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop

@router.get("/stops/{stop_id}/geojson", response_model=schemas.StopGeoJSONFeature)
def read_stop_geojson(stop_id: int, db: Session = Depends(get_db)):
    """
    Get a single stop as a GeoJSON Feature.
    """
    stop = db.query(models.Stop).filter(models.Stop.id == stop_id).first()
    if stop is None:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop.to_geojson()

@router.put("/stops/{stop_id}", response_model=schemas.StopOut)
def update_stop(stop_id: int, stop_update: schemas.StopUpdate, db: Session = Depends(get_db)):
    """
    Update a stop by ID.
    Updates all fields: name, county (name) OR county_id, location, lat, lng.
    """
    stop = db.query(models.Stop).filter(models.Stop.id == stop_id).first()
    if stop is None:
        raise HTTPException(status_code=404, detail="Stop not found")
    
    stop_data = stop_update.model_dump(exclude_unset=True)
    
    # Handle county_id update if present
    if 'county_id' in stop_data:
        county_id = stop_data['county_id']
        if county_id:
            county = db.query(models.County).filter(models.County.id == county_id).first()
            if not county:
                raise HTTPException(status_code=404, detail=f"County with id {county_id} not found")
            stop.county_id = county.id
    
    # Handle county name update if present (and county_id wasn't just set)
    elif 'county' in stop_data:
        county_name = stop_data.pop('county')
        if county_name:
            county = db.query(models.County).filter(models.County.name.ilike(county_name)).first()
            if not county:
                raise HTTPException(status_code=404, detail=f"County '{county_name}' not found")
            stop.county_id = county.id
    
    # Update other fields
    for key, value in stop_data.items():
        if key not in ['county', 'county_id']:
            setattr(stop, key, value)
    
    db.commit()
    db.refresh(stop)
    return stop

@router.delete("/stops/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(stop_id: int, db: Session = Depends(get_db)):
    """
    Delete a stop by ID.
    Returns 204 No Content on success.
    """
    stop = db.query(models.Stop).filter(models.Stop.id == stop_id).first()
    if stop is None:
        raise HTTPException(status_code=404, detail="Stop not found")
    
    db.delete(stop)
    db.commit()
    return None


# # --- Event Routes ---
# @router.post("/events/", response_model=schemas.Event)
# def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
#     # Create Event
#     event_data = event.model_dump()
#     stops_data = event_data.pop("stops")
    
#     # Auto-assign Bus from Driver
#     if event.driver_id:
#         driver = db.query(DriverProfile).filter(DriverProfile.id == event.driver_id).first()
#         if not driver:
#             raise HTTPException(status_code=404, detail="Driver not found")
        
#         # Check if driver has a bus
#         # Assuming relationship is set up in auth/models.py
#         if not driver.bus:
#              raise HTTPException(status_code=400, detail="Driver does not have an assigned bus")
        
#         event_data['bus_id'] = driver.bus.id
    
#     db_event = models.Event(**event_data)
#     db_event.available_tickets = db_event.total_tickets # Initialize available tickets
#     db.add(db_event)
#     db.commit()
#     db.refresh(db_event)

#     # Add Stops
#     for stop_item in stops_data:
#         db_event_stop = models.EventStop(event_id=db_event.id, **stop_item)
#         db.add(db_event_stop)
    
#     db.commit()
#     db.refresh(db_event)
#     return db_event

# @router.get("/events/", response_model=List[schemas.Event])
# def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     events = db.query(models.Event).offset(skip).limit(limit).all()
#     return events

# @router.get("/events/{event_id}", response_model=schemas.Event)
# def read_event(event_id: int, db: Session = Depends(get_db)):
#     event = db.query(models.Event).filter(models.Event.id == event_id).first()
#     if event is None:
#         raise HTTPException(status_code=404, detail="Event not found")
#     return event

# # --- Booking Routes ---
# @router.post("/bookings/", response_model=schemas.Booking)
# def create_booking(booking: schemas.BookingCreate, user_id: int, db: Session = Depends(get_db)):
#     # Note: user_id should ideally come from auth dependency. 
    
#     event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()
#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
    
#     if event.available_tickets < booking.seats:
#         raise HTTPException(status_code=400, detail="Not enough seats available")
    
#     total_price = 0
#     for stop in event.event_stops:
#         total_price += stop.price
    
#     total_price = total_price * booking.seats

#     db_booking = models.Booking(
#         user_id=user_id,
#         event_id=booking.event_id,
#         seats=booking.seats,
#         total_price=total_price,
#         status="confirmed"
#     )
    
#     # Update available tickets
#     event.available_tickets -= booking.seats
    
#     db.add(db_booking)
#     db.add(event) # Update event
#     db.commit()
#     db.refresh(db_booking)
#     return db_booking

# @router.get("/bookings/", response_model=List[schemas.Booking])
# def read_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     bookings = db.query(models.Booking).offset(skip).limit(limit).all()
#     return bookings
