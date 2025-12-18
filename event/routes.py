from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.app.database import get_db
from . import models, schemas

router = APIRouter(prefix="/event", tags=["Events"])

@router.post("/venues/", response_model=schemas.VenueOut)
def create_venue(venue: schemas.VenueCreate, db: Session = Depends(get_db)):
    db_venue = models.Venue(**venue.model_dump())
    db.add(db_venue)
    db.commit()
    db.refresh(db_venue)
    return db_venue

@router.get("/venues/", response_model=List[schemas.VenueOut])
def read_venues(db: Session = Depends(get_db)):
    venues = db.query(models.Venue).all()
    return venues

@router.get("/venues/geojson", response_model=schemas.VenueGeoJSONFeatureCollection)
def read_venues_geojson(db: Session = Depends(get_db)):
    venues = db.query(models.Venue).all()
    features = [venue.to_geojson() for venue in venues]
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/venues/{venue_id}", response_model=schemas.VenueOut)
def read_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

@router.get("/venues/{venue_id}/geojson", response_model=schemas.VenueGeoJSONFeature)
def read_venue_geojson(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue.to_geojson()

@router.put("/venues/{venue_id}", response_model=schemas.VenueOut)
def update_venue(venue_id: int, venue_update: schemas.VenueUpdate, db: Session = Depends(get_db)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    update_data = venue_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(venue, key, value)
    
    db.commit()
    db.refresh(venue)
    return venue

@router.delete("/venues/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    db.delete(venue)
    db.commit()
    return None
