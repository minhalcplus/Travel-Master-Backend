from sqlalchemy.orm import Session
from typing import List, Tuple, Optional
from .models import EventRoute, EventStopNode
from . import models

def build_previous_chain(node: EventStopNode):
    """
    Returns all previous nodes recursively for a given node.
    """
    result = []
    current = node
    visited = set()
    while current.previous_stop_node:
        found_prev = False
        for prev in current.previous_stop_node:
            if prev.id not in visited:
                result.append(prev)
                visited.add(prev.id)
                current = prev
                found_prev = True
                break
        if not found_prev:
            break
    return result[::-1]  # reverse to get order from start to this node

def build_full_route_from_node(node: EventStopNode, visited=None):
    """
    Recursively traverse stop nodes to get the full path including branches.
    Prevents infinite loops using `visited`.
    """
    if visited is None:
        visited = set()

    if node.id in visited:
        return []

    visited.add(node.id)

    # Add all previous nodes chain (for serialization/UI)
    # Note: In the original logic, this was assigned to a non-existent field on the model,
    # but it's useful for the API to attach it.
    print(f"  Traversing Node {node.id} (Stop {node.stop_id}), next_id={node.next_stop_id}, next_node={'exists' if node.next_stop_node else 'NONE'}")
    
    full_path = [node]

    if node.next_stop_node:
        full_path.extend(
            build_full_route_from_node(node.next_stop_node, visited)
        )

    return full_path

def find_matching_subsequence(
    db: Session,
    stop_nodes_data: list,
    exclude_route_id: int | None = None
):
    """
    Finds if the provided stop nodes sequence already exists in another route to allow merging/branching.
    """
    if not stop_nodes_data:
        return None

    target_stop_ids = [s.stop_id for s in stop_nodes_data]

    for start_idx in range(len(target_stop_ids)):
        subsequence = target_stop_ids[start_idx:]

        # Block single-stop merges to avoid excessive branching
        if len(subsequence) < 2:
            continue

        candidates_q = db.query(EventStopNode).filter(
            EventStopNode.stop_id == subsequence[0]
        )

        if exclude_route_id:
            candidates_q = candidates_q.filter(
                EventStopNode.route_id != exclude_route_id
            )

        candidates = candidates_q.all()

        for candidate in candidates:
            # Existing chain must continue
            if candidate.next_stop_node is None:
                continue

            if is_matching_chain(candidate, subsequence):
                chain = build_chain_from_node(candidate, len(subsequence))
                return start_idx, chain

    return None

def is_matching_chain(
    start_node: EventStopNode,
    target_stop_ids: list[int]
) -> bool:
    """
    Confirms stop_id sequence match.
    """
    current = start_node
    for stop_id in target_stop_ids:
        if not current or current.stop_id != stop_id:
            return False
        current = current.next_stop_node
    
    # Check if existing chain continues beyond our new route's end
    if current is not None:
        return False
        
    return True

def build_chain_from_node(
    start_node: EventStopNode,
    length: int
) -> list[EventStopNode]:
    """
    Collect nodes in order.
    """
    chain = []
    current = start_node
    for _ in range(length):
        if not current:
            break
        chain.append(current)
        current = current.next_stop_node
    return chain

def cleanup_node_references(
    db: Session,
    node_to_delete: EventStopNode,
    route_id: int
):
    """
    Removes cross-route references safely.
    """
    for prev in node_to_delete.previous_stop_node:
        if prev.route_id != route_id and prev.next_stop_id == node_to_delete.id:
            prev.next_stop_id = None
            db.add(prev)

    if node_to_delete.next_stop_node:
        next_node = node_to_delete.next_stop_node
        next_node.previous_stop_node = [
            p for p in next_node.previous_stop_node
            if p.id != node_to_delete.id
        ]
        db.add(next_node)

def attach_full_stop_nodes(route: EventRoute):
    """
    Attaches the full sequence of stop nodes (including ancestors) to a route.
    """
    all_nodes = []
    visited = set()

    for node in route.stop_nodes:
        if not node.previous_stop_node:  # starting nodes for this route
            nodes_from_here = build_full_route_from_node(node, visited)
            all_nodes.extend(nodes_from_here)

    # Deduplicate nodes (branches safe)
    unique_nodes = {node.id: node for node in all_nodes}.values()
    route.stop_nodes = list(unique_nodes)

    return route

def create_event_route_logic(
    db: Session,
    day_id: int,
    route_data: any, # schemas.EventRouteCreate
    exclude_route_id: Optional[int] = None,
    existing_route: Optional[EventRoute] = None
) -> EventRoute:
    """
    Core logic for creating or updating an EventRoute with graph-based stop node matching.
    """
    # Determine name: use 'name' if provided, else 'route_template_name'
    route_name = getattr(route_data, 'name', None) or getattr(route_data, 'route_template_name', None) or "Unnamed Route"
    
    if existing_route:
        route = existing_route
        route.name = route_name
        route.route_template_id = getattr(route_data, 'route_template_id', route.route_template_id)
        route.group_id = getattr(route_data, 'group_id', route.group_id)
        route.start_location = route_data.start_location
        route.destination = route_data.destination
        route.is_active = route_data.is_active
        route.event_day_id = day_id
    else:
        route = models.EventRoute(
            event_day_id=day_id,
            route_template_id=getattr(route_data, 'route_template_id', None),
            group_id=getattr(route_data, 'group_id', None),
            name=route_name,
            start_location=route_data.start_location,
            destination=route_data.destination,
            is_active=route_data.is_active
        )
        db.add(route)
    
    db.flush()

    # Chain matching disabled to ensure "whole new" nodes for every route
    last_node = None
    for stop_node_data in route_data.stop_nodes:
        node = models.EventStopNode(
            route_id=route.id,
            stop_id=stop_node_data.stop_id,
            price=stop_node_data.price,
            is_active=getattr(stop_node_data, "is_active", True),
            booking_capacity=getattr(stop_node_data, "booking_capacity", None),
            pickup_time=getattr(stop_node_data, "pickup_time", None)
        )
        db.add(node)
        db.flush()

        if last_node:
            last_node.next_stop_id = node.id
            db.add(last_node)
        last_node = node

    db.flush()
    return route
