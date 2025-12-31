from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.app.database import get_db
from auth.utils import super_admin_only
from . import models, schemas
from datetime import date, time, datetime
from .models import Event, EventDay, EventStatus, EventRoute, EventStopNode
import os
from uuid import uuid4
from fastapi import Form, File, UploadFile
import json
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends, Request
from utils.gcs import gcs_storage
from .utils import find_matching_subsequence, cleanup_node_references, attach_full_stop_nodes, create_event_route_logic

router = APIRouter(prefix="/event", tags=["Events"])

@router.post("/venues/", response_model=schemas.VenueOut, dependencies=[Depends(super_admin_only)])
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

@router.put("/venues/{venue_id}", response_model=schemas.VenueOut, dependencies=[Depends(super_admin_only)])
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

@router.delete("/venues/{venue_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(super_admin_only)])
def delete_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    db.delete(venue)
    db.commit()
    return None

#EVENT ROUTES

MEDIA_ROOT = "media/events"
os.makedirs(MEDIA_ROOT, exist_ok=True)
@router.post("/admin/events", status_code=201, dependencies=[Depends(super_admin_only)])
async def create_event(
    request: Request,                   # 1️⃣ No default → first
    db: Session = Depends(get_db),      # 2️⃣ Default → after non-defaults
    name: str = Form(...),
    venue_id: int = Form(...),
    desktop_image: UploadFile = File(...),
    mobile_image: UploadFile = File(...),
    description: str | None = Form(None),
    description_metadata: str | None = Form(None),
    status: str = Form("hidden"),
    category: str | None = Form(None),
    days: str = Form(...)
):
    try:
        days_data = json.loads(days)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid days JSON")

    if not days_data:
        raise HTTPException(400, "At least one event day is required")

    # Validate status
    try:
        event_status = EventStatus(status.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status}. Allowed values: {[s.value for s in EventStatus]}")

    # Upload images to GCS
    desktop_path = await gcs_storage.upload_file(desktop_image)
    mobile_path = await gcs_storage.upload_file(mobile_image)

    # Create Event
    event = Event(
        name=name,
        venue_id=venue_id,
        desktop_image=desktop_path,
        mobile_image=mobile_path,
        description=description,
        description_metadata=json.loads(description_metadata) if description_metadata else None,
        status=event_status,
        category=category
    )

    db.add(event)
    db.flush()

    # Add EventDays
    for d in days_data:
        try:
            parsed_date = datetime.fromisoformat(d["event_date"].replace('Z', '+00:00')).date()
        except ValueError:
            parsed_date = date.fromisoformat(d["event_date"])

        try:
            parsed_time = datetime.fromisoformat(d["gate_open_time"].replace('Z', '+00:00')).time()
        except ValueError:
            parsed_time = time.fromisoformat(d["gate_open_time"].replace('Z', '+00:00'))

        day_obj = EventDay(
            event_id=event.id,
            event_date=parsed_date,
            gate_open_time=parsed_time,
            note=d.get("note")
        )
        db.add(day_obj)
        db.flush()

        # Handle nested routes
        routes_data = d.get("routes", [])
        for r in routes_data:
            # Since d is a dict from json.loads, r is also a dict
            # create_event_route_logic expects an object with attributes or a dict helper
            # I can convert it to a dot-dict or update the logic to handle dicts
            from types import SimpleNamespace
            
            # Helper to recursively convert dict to SimpleNamespace for getattr compatibility
            def dict_to_sns(d):
                if isinstance(d, list):
                    return [dict_to_sns(i) for i in d]
                elif isinstance(d, dict):
                    return SimpleNamespace(**{k: dict_to_sns(v) for k, v in d.items()})
                return d

            r_obj = dict_to_sns(r)
            create_event_route_logic(db, day_obj.id, r_obj)

    db.commit()
    db.refresh(event)

    # Generate image URLs
    desktop_url = gcs_storage.get_public_url(desktop_path)
    mobile_url = gcs_storage.get_public_url(mobile_path)

    return {
        "id": event.id,
        "name": event.name,
        "venue_id": event.venue_id,
        "desktop_image_url": desktop_url,
        "mobile_image_url": mobile_url,
        "description": event.description,
        "description_metadata": event.description_metadata,
        "status": event.status.value,
        "category": event.category,
        "is_active": event.is_active,
        "days": [
            {
                "id": day.id,
                "event_date": day.event_date,
                "gate_open_time": day.gate_open_time.strftime("%H:%M:%S"),
                "note": day.note,
                "routes": [
                    schemas.EventRouteOut.model_validate(attach_full_stop_nodes(route))
                    for route in day.routes
                ]
            }
            for day in event.days
        ]
    }

@router.get("/admin/events", response_model=List[schemas.EventOut], dependencies=[Depends(super_admin_only)])
def list_events_admin(request: Request, db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    
    event_list = []
    for e in events:
        desktop_url = f"{request.base_url}media/events/{os.path.basename(e.desktop_image)}"
        mobile_url = f"{request.base_url}media/events/{os.path.basename(e.mobile_image)}"
        event_list.append({
            "id": e.id,
            "name": e.name,
            "venue_id": e.venue_id,
            "desktop_image_url": desktop_url,
            "mobile_image_url": mobile_url,
            "description": e.description,
            "description_metadata": e.description_metadata,
            "status": e.status,
            "category": e.category,
            "is_active": e.is_active,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
            "venue": e.venue,
            "days": e.days
        })
    return event_list


@router.get("/admin/events/{event_id}", response_model=schemas.EventOut, dependencies=[Depends(super_admin_only)])
def get_event_admin(event_id: int, request: Request, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    desktop_url = gcs_storage.get_public_url(event.desktop_image)
    mobile_url = gcs_storage.get_public_url(event.mobile_image)

    return {
        "id": event.id,
        "name": event.name,
        "venue_id": event.venue_id,
        "desktop_image_url": desktop_url,
        "mobile_image_url": mobile_url,
        "description": event.description,
        "description_metadata": event.description_metadata,
        "status": event.status,
        "category": event.category,
        "is_active": event.is_active,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "venue": event.venue,
        "days": event.days
    }

@router.put("/admin/events/{event_id}", status_code=200, dependencies=[Depends(super_admin_only)])
async def update_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str | None = Form(None),
    venue_id: int | None = Form(None),
    desktop_image: UploadFile | None = File(None),
    mobile_image: UploadFile | None = File(None),
    description: str | None = Form(None),
    description_metadata: str | None = Form(None),
    status: str | None = Form(None),
    category: str | None = Form(None),
    days: str | None = Form(None)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update basic fields
    if name is not None:
        event.name = name
    if venue_id is not None:
        event.venue_id = venue_id
    if description is not None:
        event.description = description
    if description_metadata is not None:
        try:
            event.description_metadata = json.loads(description_metadata)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid description_metadata JSON")

    # Update status
    if status is not None:
        try:
            event.status = EventStatus(status.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}. Allowed values: {[s.value for s in EventStatus]}")

    if category is not None:
        event.category = category

    # Update images
    # Update images
    if desktop_image:
        # Delete old image if it exists
        if event.desktop_image:
             gcs_storage.delete_file(event.desktop_image)
        
        event.desktop_image = await gcs_storage.upload_file(desktop_image)

    if mobile_image:
        # Delete old image if it exists
        if event.mobile_image:
            gcs_storage.delete_file(event.mobile_image)
            
        event.mobile_image = await gcs_storage.upload_file(mobile_image)

    # Update days (replace all)
    if days is not None:
        try:
            days_data = json.loads(days)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid days JSON")

        # Delete existing days
        db.query(models.EventDay).filter(models.EventDay.event_id == event.id).delete()
        
        # Add new days
        for d in days_data:
            try:
                parsed_date = datetime.fromisoformat(d["event_date"].replace('Z', '+00:00')).date()
            except ValueError:
                parsed_date = date.fromisoformat(d["event_date"])

            try:
                parsed_time = datetime.fromisoformat(d["gate_open_time"].replace('Z', '+00:00')).time()
            except ValueError:
                parsed_time = time.fromisoformat(d["gate_open_time"].replace('Z', '+00:00'))

            db.add(EventDay(
                event_id=event.id,
                event_date=parsed_date,
                gate_open_time=parsed_time,
                note=d.get("note")
            ))

    db.commit()
    db.refresh(event)

    # Generate image URLs
    desktop_url = gcs_storage.get_public_url(event.desktop_image)
    mobile_url = gcs_storage.get_public_url(event.mobile_image)

    return {
        "id": event.id,
        "name": event.name,
        "venue_id": event.venue_id,
        "desktop_image_url": desktop_url,
        "mobile_image_url": mobile_url,
        "description": event.description,
        "description_metadata": event.description_metadata,
        "status": event.status.value,
        "category": event.category,
        "is_active": event.is_active,
        "days": [
            {
                "id": day.id,
                "event_date": day.event_date,
                "gate_open_time": day.gate_open_time.strftime("%H:%M:%S"),
                "note": day.note
            }
            for day in event.days
        ]
    }

@router.delete("/admin/events/{event_id}", status_code=204, dependencies=[Depends(super_admin_only)])
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete images from disk
    # Delete images from GCS
    if event.desktop_image:
        try:
            gcs_storage.delete_file(event.desktop_image)
        except Exception as e:
            print(f"Failed to delete desktop image: {e}")

    if event.mobile_image:
        try:
            gcs_storage.delete_file(event.mobile_image)
        except Exception as e:
            print(f"Failed to delete mobile image: {e}")
    db.delete(event)
    db.commit()
    return None

# --- EVENT DAY ROUTE MANAGEMENT ---

@router.post("/admin/event-days/{day_id}/routes", response_model=schemas.EventDayOut, dependencies=[Depends(super_admin_only)])
async def create_event_day_routes(
    day_id: int,
    data: schemas.EventDayRoutesUpdate,
    db: Session = Depends(get_db)
):
    """
    Bulk create/update routes for an EventDay.
    Clears existing routes for that day and recreates them based on the payload.
    """
    day = db.query(models.EventDay).filter(models.EventDay.id == day_id).first()
    if not day:
        # Fallback: check if we can find it via data.event_day_id if URL ID is generic/placeholder
        day = db.query(models.EventDay).filter(models.EventDay.id == data.event_day_id).first()
        if not day:
            raise HTTPException(status_code=404, detail="Event day not found")

    # Update day date if provided and different
    if data.event_date:
        day.event_date = data.event_date

    # 1. Cleanup old routes and nodes for this day
    for route in day.routes:
        old_nodes = db.query(models.EventStopNode).filter_by(route_id=route.id).all()
        for node in old_nodes:
            cleanup_node_references(db, node, route.id)
            node.next_stop_id = None
            db.add(node)
        db.flush()
        db.query(models.EventStopNode).filter_by(route_id=route.id).delete()
    
    db.query(models.EventRoute).filter_by(event_day_id=day.id).delete()
    db.flush()

    # 2. Create new routes from the list
    for r_data in data.routes:
        create_event_route_logic(db, day.id, r_data)

    db.commit()
    db.refresh(day)

    # Attach full chains for response
    for route in day.routes:
        attach_full_stop_nodes(route)

    return day

@router.get("/admin/event-days/{day_id}/routes", response_model=List[schemas.EventRouteOut], dependencies=[Depends(super_admin_only)])
def get_event_day_routes(day_id: int, db: Session = Depends(get_db)):
    day = db.query(models.EventDay).filter(models.EventDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Event day not found")
    
    for route in day.routes:
        attach_full_stop_nodes(route)
        
    return day.routes

# --- GENERAL EVENT ROUTE CRUD ---

@router.post("/admin/event-routes/", response_model=schemas.EventRouteOut, dependencies=[Depends(super_admin_only)])
def create_event_route(
    data: schemas.EventRouteCreate,
    day_id: int, # We still need a day context or make it optional?
    db: Session = Depends(get_db)
):
    """
    Standalone create for EventRoute.
    Note: Requires day_id because EventRoute is tied to EventDay.
    """
    route = create_event_route_logic(db, day_id, data)
    db.commit()
    db.refresh(route)
    return attach_full_stop_nodes(route)


@router.get("/admin/event-routes/", response_model=List[schemas.EventRouteSummaryOut], dependencies=[Depends(super_admin_only)])
def list_event_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List summary of all EventRoutes.
    """
    routes = db.query(models.EventRoute).offset(skip).limit(limit).all()
    result = []
    for route in routes:
        stop_count = db.query(models.EventStopNode).filter_by(route_id=route.id).count()
        result.append({
            "id": route.id,
            "name": route.name,
            "event_day_id": route.event_day_id,
            "start_location": route.start_location,
            "destination": route.destination,
            "is_active": route.is_active,
            "group_id": route.group_id,
            "stop_count": stop_count
        })
    return result


@router.get("/admin/event-routes/all/", response_model=List[schemas.EventRouteOut], dependencies=[Depends(super_admin_only)])
def list_all_event_routes(db: Session = Depends(get_db)):
    """
    List all EventRoutes with full detail.
    """
    routes = db.query(models.EventRoute).all()
    for route in routes:
        attach_full_stop_nodes(route)
    return routes


@router.get("/admin/event-routes/{route_id}", response_model=schemas.EventRouteOut, dependencies=[Depends(super_admin_only)])
def get_event_route(route_id: int, db: Session = Depends(get_db)):
    """
    Get detail for a specific EventRoute.
    """
    route = db.query(models.EventRoute).filter_by(id=route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return attach_full_stop_nodes(route)


@router.put("/admin/event-routes/{day_id}", response_model=schemas.EventDayOut, dependencies=[Depends(super_admin_only)])
def update_event_day_routes_bulk(
    day_id: int,
    data: schemas.EventDayRoutesUpdate,
    db: Session = Depends(get_db)
):
    """
    Bulk update routes for an EventDay.
    Clears existing routes for that day and recreates them.
    """
    day = db.query(models.EventDay).filter(models.EventDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Event day not found")

    # 1. Cleanup old routes and nodes for this day
    for route in day.routes:
        old_nodes = db.query(models.EventStopNode).filter_by(route_id=route.id).all()
        for node in old_nodes:
            cleanup_node_references(db, node, route.id)
            node.next_stop_id = None
            db.add(node)
        db.flush()
        db.query(models.EventStopNode).filter_by(route_id=route.id).delete()
    
    db.query(models.EventRoute).filter_by(event_day_id=day.id).delete()
    db.flush()

    # 2. Create new routes from the list
    for r_data in data.routes:
        create_event_route_logic(db, day.id, r_data)

    db.commit()
    db.refresh(day)

    # Attach full chains for response
    for route in day.routes:
        attach_full_stop_nodes(route)

    return day


@router.delete("/admin/event-routes/{day_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(super_admin_only)])
def delete_event_day_routes_bulk(day_id: int, db: Session = Depends(get_db)):
    """
    Delete all routes for an EventDay.
    """
    day = db.query(models.EventDay).filter(models.EventDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Event day not found")
    
    for route in day.routes:
        route_nodes = db.query(models.EventStopNode).filter_by(route_id=route.id).all()
        for node in route_nodes:
            cleanup_node_references(db, node, route.id)
            node.next_stop_id = None
            db.add(node)
            db.flush()
            db.delete(node)
        db.delete(route)
    
    db.commit()
    return None

# PUBLIC ROUTES (no dependencies or different policy)
@router.get("/", response_model=List[schemas.EventOut])
def list_events_public(request: Request, db: Session = Depends(get_db)):
    events = db.query(models.Event).filter(
        models.Event.is_active == True,
        models.Event.status != models.EventStatus.HIDDEN
    ).all()
    
    event_list = []
    for e in events:
        desktop_url = f"{request.base_url}media/events/{os.path.basename(e.desktop_image)}"
        mobile_url = f"{request.base_url}media/events/{os.path.basename(e.mobile_image)}"
        event_list.append({
            "id": e.id,
            "name": e.name,
            "venue_id": e.venue_id,
            "desktop_image_url": desktop_url,
            "mobile_image_url": mobile_url,
            "description": e.description,
            "description_metadata": e.description_metadata,
            "status": e.status,
            "category": e.category,
            "is_active": e.is_active,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
            "venue": e.venue,
            "days": e.days
        })
    return event_list


@router.get("/{event_id}", response_model=schemas.EventOut)
def get_event_public(event_id: int, request: Request, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.is_active == True,
        models.Event.status != models.EventStatus.HIDDEN
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or inactive")

    desktop_url = gcs_storage.get_public_url(event.desktop_image)
    mobile_url = gcs_storage.get_public_url(event.mobile_image)

    return {
        "id": event.id,
        "name": event.name,
        "venue_id": event.venue_id,
        "desktop_image_url": desktop_url,
        "mobile_image_url": mobile_url,
        "description": event.description,
        "description_metadata": event.description_metadata,
        "status": event.status,
        "category": event.category,
        "is_active": event.is_active,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "venue": event.venue,
        "days": event.days
    }
# --- Shared Inventory Routes ---

@router.post("/admin/event-days/{day_id}/shared-inventories", response_model=schemas.SharedInventoryOut, dependencies=[Depends(super_admin_only)])
def create_shared_inventory(day_id: int, inventory: schemas.SharedInventoryCreate, db: Session = Depends(get_db)):
    day = db.query(models.EventDay).filter(models.EventDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Event day not found")
    
    db_inventory = models.SharedInventory(
        event_day_id=day_id,
        name=inventory.name,
        capacity=inventory.capacity
    )
    db.add(db_inventory)
    db.flush() # Flush to get the ID

    if inventory.stop_node_ids:
        nodes = db.query(models.EventStopNode).filter(models.EventStopNode.id.in_(inventory.stop_node_ids)).all()
        db_inventory.stop_nodes = nodes

    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@router.get("/admin/shared-inventories", response_model=List[schemas.SharedInventoryOut], dependencies=[Depends(super_admin_only)])
def list_all_shared_inventories(db: Session = Depends(get_db)):
    return db.query(models.SharedInventory).all()

@router.get("/admin/shared-inventories/{inventory_id}", response_model=schemas.SharedInventoryOut, dependencies=[Depends(super_admin_only)])
def get_shared_inventory(inventory_id: int, db: Session = Depends(get_db)):
    db_inventory = db.query(models.SharedInventory).filter(models.SharedInventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Shared inventory not found")
    return db_inventory

@router.put("/admin/shared-inventories/{inventory_id}", response_model=schemas.SharedInventoryOut, dependencies=[Depends(super_admin_only)])
def update_shared_inventory(inventory_id: int, inventory: schemas.SharedInventoryUpdate, db: Session = Depends(get_db)):
    db_inventory = db.query(models.SharedInventory).filter(models.SharedInventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Shared inventory not found")
    
    if inventory.name is not None:
        db_inventory.name = inventory.name
    if inventory.capacity is not None:
        db_inventory.capacity = inventory.capacity
    
    if inventory.stop_node_ids is not None:
        # Fetch nodes to assign
        if inventory.stop_node_ids:
            nodes = db.query(models.EventStopNode).filter(models.EventStopNode.id.in_(inventory.stop_node_ids)).all()
            db_inventory.stop_nodes = nodes
        else:
            db_inventory.stop_nodes = []
        
    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@router.delete("/admin/shared-inventories/{inventory_id}", status_code=204, dependencies=[Depends(super_admin_only)])
def delete_shared_inventory(inventory_id: int, db: Session = Depends(get_db)):
    db_inventory = db.query(models.SharedInventory).filter(models.SharedInventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Shared inventory not found")
    
    db.delete(db_inventory)
    db.commit()
    return None

@router.post("/admin/shared-inventories/{inventory_id}/attach-nodes", response_model=schemas.SharedInventoryOut, dependencies=[Depends(super_admin_only)])
def attach_nodes_to_inventory(inventory_id: int, node_ids: List[int], db: Session = Depends(get_db)):
    db_inventory = db.query(models.SharedInventory).filter(models.SharedInventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Shared inventory not found")
    
    # Fetch nodes to assign
    if node_ids:
        nodes = db.query(models.EventStopNode).filter(models.EventStopNode.id.in_(node_ids)).all()
        db_inventory.stop_nodes = nodes
    else:
        db_inventory.stop_nodes = []
    
    db.commit()
    db.refresh(db_inventory)
    return db_inventory
