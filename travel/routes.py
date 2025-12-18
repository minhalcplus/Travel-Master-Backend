from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.app.database import get_db
from . import models, schemas
from .models import RouteTemplate, StopNode, Stop, RouteGroup
from travel.schemas import *
from travel.utils import find_matching_subsequence, cleanup_node_references ,build_full_route_from_node, attach_full_stop_nodes
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
    db.delete(stop)
    db.commit()
    return None


    # -----------------------------
    # Create a Route
    # -----------------------------
@router.post("/admin/routes/template/", response_model=RouteOut)
def create_route(
    data: RouteCreate,
    db: Session = Depends(get_db)
):
    route = RouteTemplate(
        name=data.name,
        start_location=data.start_location,
        destination=data.destination,
        is_active=data.is_active,
    )
    db.add(route)
    db.flush()

    match_info = find_matching_subsequence(db, data.stop_nodes)

    last_node = None

    if match_info:
        match_start_idx, existing_chain = match_info

        for i in range(match_start_idx):
            stop = data.stop_nodes[i]
            node = StopNode(
                route_id=route.id,
                stop_id=stop.stop_id,
                price=stop.price
            )
            db.add(node)
            db.flush()

            if last_node:
                last_node.next_stop_id = node.id
                db.add(last_node)

            last_node = node

        merge_node = existing_chain[0]
        last_node.next_stop_id = merge_node.id

        if last_node not in merge_node.previous_stop_node:
            merge_node.previous_stop_node.append(last_node)

        db.add(last_node)
        db.add(merge_node)

    else:

        for stop in data.stop_nodes:
            node = StopNode(
                route_id=route.id,
                stop_id=stop.stop_id,
                price=stop.price
            )
            db.add(node)
            db.flush()

            if last_node:
                last_node.next_stop_id = node.id
                db.add(last_node)

            last_node = node

    db.commit()
    db.refresh(route)
    return route


# -----------------------------
# Read Routes (Summary)
# -----------------------------
@router.get("/admin/routes/template", response_model=List[schemas.RouteSummaryOut])
def read_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    routes = db.query(models.RouteTemplate).offset(skip).limit(limit).all()
    result = []
    for route in routes:
        stop_count = db.query(models.StopNode).filter_by(route_id=route.id).count()
        result.append({
            "id": route.id,
            "name": route.name,
            "start_location": route.start_location,
            "destination": route.destination,
            "is_active": route.is_active,
            "stop_count": stop_count
        })
    return result


# -----------------------------
# Read Route Detail
# -----------------------------
@router.get("/admin/routes/all-template/", response_model=list[RouteDetailOut])
def read_all_routes(db: Session = Depends(get_db)):
    routes = db.query(RouteTemplate).all()

    for route in routes:
        attach_full_stop_nodes(route)

    return routes

    
@router.get("/admin/routes/template/{route_id}", response_model=RouteDetailOut)
def read_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(RouteTemplate).filter(RouteTemplate.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    all_nodes = []
    visited = set()
    # Traverse each starting stop node of this route
    for node in route.stop_nodes:
        if not node.previous_stop_node:  # starting nodes
            nodes_from_here = build_full_route_from_node(node, visited)
            all_nodes.extend(nodes_from_here)

    # Deduplicate nodes (in case of branches)
    unique_nodes = {node.id: node for node in all_nodes}.values()
    route.stop_nodes = list(unique_nodes)

    return route

# -----------------------------
# Update Route (Full Replace with Branching Logic)
# -----------------------------
@router.put("/admin/routes/template/{route_id}", response_model=schemas.RouteOut)
def update_route(
    route_id: int,
    data: schemas.RouteCreate,
    db: Session = Depends(get_db)
):
    route = db.query(models.RouteTemplate).filter_by(id=route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.name = data.name
    route.start_location = data.start_location
    route.destination = data.destination
    route.is_active = data.is_active

    # Cleanup references
    old_nodes = db.query(models.StopNode).filter_by(route_id=route_id).all()
    for node in old_nodes:
        cleanup_node_references(db, node, route_id)

    # Delete only this route's nodes
    db.query(models.StopNode).filter_by(route_id=route_id).delete()
    db.flush()

    # Rebuild chain (exclude self)
    match_info = find_matching_subsequence(
        db,
        data.stop_nodes,
        exclude_route_id=route_id
    )

    last_node = None

    if match_info:
        match_start_idx, existing_chain = match_info

        for i in range(match_start_idx):
            stop = data.stop_nodes[i]
            node = models.StopNode(
                route_id=route.id,
                stop_id=stop.stop_id,
                price=stop.price
            )
            db.add(node)
            db.flush()

            if last_node:
                last_node.next_stop_id = node.id
                db.add(last_node)

            last_node = node

        merge_node = existing_chain[0]
        last_node.next_stop_id = merge_node.id

        if last_node not in merge_node.previous_stop_node:
            merge_node.previous_stop_node.append(last_node)

        db.add(last_node)
        db.add(merge_node)

    else:

        for stop in data.stop_nodes:
            node = models.StopNode(
                route_id=route.id,
                stop_id=stop.stop_id,
                price=stop.price
            )
            db.add(node)
            db.flush()

            if last_node:
                last_node.next_stop_id = node.id
                db.add(last_node)

            last_node = node

    db.commit()
    db.refresh(route)
    return route

# -----------------------------
# Delete Route
# -----------------------------
@router.delete("/admin/routes/template/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route_id: int, db: Session = Depends(get_db)):
    """
    Deletes a route and cleans up its nodes intelligently:
    - If a node is used ONLY by this route: delete it
    - If a node is shared with other routes: keep it, remove links
    """
    route = db.query(models.RouteTemplate).filter_by(id=route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Get all nodes belonging to this route
    route_nodes = db.query(models.StopNode).filter_by(route_id=route_id).all()
    
    
    # Process each node
    for node in route_nodes:
        # Check if this node is shared (has previous nodes from other routes)
        other_route_previous_nodes = [
            prev for prev in node.previous_stop_node 
            if prev.route_id != route_id
        ]
        
        if other_route_previous_nodes:
            # Node is shared - keep it but remove links from this route's nodes
            
            # Remove previous nodes that belong to this route
            node.previous_stop_node = [
                prev for prev in node.previous_stop_node 
                if prev.route_id != route_id
            ]
            db.add(node)
            
        else:
            # Node is only used by this route - safe to delete
            
            # Clean up references in other nodes before deleting
            cleanup_node_references(db, node, route_id)
            
            # Delete the node
            db.delete(node)
    
    # Delete the route itself
    db.delete(route)
    db.commit()
    return None


# -----------------------------
# Create Route Group
# -----------------------------
@router.post("/admin/route-groups", response_model=RouteGroupOut)
def create_route_group(data: RouteGroupCreate, db: Session = Depends(get_db)):
    routes = db.query(RouteTemplate).filter(
        RouteTemplate.id.in_(data.route_ids)
    ).all()

    group = RouteGroup(name=data.name, routes=routes)
    db.add(group)
    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "name": group.name,
        "route_ids": [r.id for r in group.routes]
    }

# -----------------------------
# GET Route Group
# -----------------------------
@router.get("/admin/route-groups", response_model=list[RouteGroupOut])
def list_route_groups(db: Session = Depends(get_db)):
    groups = db.query(RouteGroup).all()

    return [
        {
            "id": g.id,
            "name": g.name,
            "route_ids": [r.id for r in g.routes]
        }
        for g in groups
    ]

# -----------------------------
# GET per id Route Group
# ----------------------------- 
@router.get("/admin/route-groups/{group_id}", response_model=RouteGroupOut)
def get_route_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")

    return {
        "id": group.id,
        "name": group.name,
        "route_ids": [r.id for r in group.routes]
    }

# -----------------------------
# Update Route Group
# ----------------------------- 
@router.put("/admin/route-groups/{group_id}", response_model=RouteGroupOut)
def update_route_group(
    group_id: int,
    data: RouteGroupUpdate,
    db: Session = Depends(get_db)
):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")

    if data.name is not None:
        group.name = data.name

    if data.route_ids is not None:
        routes = db.query(RouteTemplate).filter(
            RouteTemplate.id.in_(data.route_ids)
        ).all()
        group.routes = routes

    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "name": group.name,
        "route_ids": [r.id for r in group.routes]
    }

# -----------------------------
# Delete Route Group
# ----------------------------- 
@router.delete("/admin/route-groups/{group_id}", status_code=204)
def delete_route_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(RouteGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")

    db.delete(group)
    db.commit()