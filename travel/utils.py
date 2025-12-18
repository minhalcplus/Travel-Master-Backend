from .models import StopNode
from .schemas import StopNodeBase
from sqlalchemy.orm import Session
from typing import List
from . import models
from typing import List, Tuple, Optional
from .models import RouteTemplate


def build_previous_chain(node):
    """
    Returns all previous nodes recursively for a given node.
    """
    result = []
    current = node
    visited = set()
    while current.previous_stop_node:
        for prev in current.previous_stop_node:
            if prev.id not in visited:
                result.append(prev)
                visited.add(prev.id)
        current = current.previous_stop_node[0]  # follow one branch for linear chain
    return result[::-1]  # reverse to get order from start to this node

def merge_stop_nodes(db: Session, nodes: list[StopNode]):
    """
    Merge newly created stop nodes with existing nodes if possible,
    and update previous_stop_node to handle branches.
    """
    for i, node in enumerate(nodes):
        # Check if a node with the same stop_id exists
        existing_node = db.query(StopNode).filter(StopNode.stop_id == node.stop_id).first()

        if existing_node:
            # Check if the next stops match
            match = True
            cur_next = node.next_stop_id
            existing_next = existing_node.next_stop_id
            while cur_next and existing_next:
                cur_node = db.query(StopNode).get(cur_next)
                ex_node = db.query(StopNode).get(existing_next)
                if not cur_node or not ex_node or cur_node.stop_id != ex_node.stop_id:
                    match = False
                    break
                cur_next = cur_node.next_stop_id
                existing_next = ex_node.next_stop_id

            if match:
                # Merge: use existing node, update previous stops
                if i > 0:
                    prev_node = nodes[i-1]
                    if prev_node not in existing_node.previous_stop_node:
                        existing_node.previous_stop_node.append(prev_node)
                nodes[i] = existing_node  # Replace current node with existing node
        else:
            db.add(node)
        db.flush()

    # Link next_stop_id
    for i in range(len(nodes)-1):
        nodes[i].next_stop_id = nodes[i+1].id

    db.flush()

def get_all_previous_nodes(node: StopNode):
    """
    Recursively get all previous nodes (branches)
    """
    result = []
    queue = list(node.previous_stop_node)
    seen = set()
    while queue:
        n = queue.pop()
        if n.id not in seen:
            seen.add(n.id)
            result.append(n)
            queue.extend(n.previous_stop_node)
    return result

def find_existing_path(db: Session, stop_nodes: list[StopNodeBase]):
    """
    Returns the index where the new route diverges from existing routes.
    If overlap is found, returns (start_index, last_matched_node).
    """
    last_matched_node = None
    start_index = 0

    # Check for first stop node match
    first_stop_id = stop_nodes[0].stop_id
    existing_nodes = db.query(StopNode).filter(StopNode.stop_id == first_stop_id).all()

    for node in existing_nodes:
        match = True
        current_node = node
        for i, stop in enumerate(stop_nodes):
            if not current_node or current_node.stop_id != stop.stop_id:
                match = False
                break
            current_node = current_node.next_stop_node
        if match:
            # Fully matched path found, reuse from first node
            last_matched_node = node
            start_index = len(stop_nodes)  # no new nodes needed
            return start_index, last_matched_node

    # Partial match: check sequential nodes
    for i, stop in enumerate(stop_nodes):
        nodes_with_same_stop = db.query(StopNode).filter(StopNode.stop_id == stop.stop_id).all()
        for node in nodes_with_same_stop:
            current_node = node
            j = i
            while current_node and j < len(stop_nodes) and current_node.stop_id == stop_nodes[j].stop_id:
                last_matched_node = current_node
                current_node = current_node.next_stop_node
                j += 1
            if j > i:  # found some overlap
                return j, last_matched_node

    return 0, None
def build_full_route_from_node(node, visited=None):
    """
    Recursively traverse stop nodes to get the full path including branches.
    Prevents infinite loops using `visited`.
    """
    if visited is None:
        visited = set()

    if node.id in visited:
        return []

    visited.add(node.id)

    # Add all previous nodes chain
    node.all_previous_stop_nodes = build_previous_chain(node)

    full_path = [node]

    if node.next_stop_node:
        full_path.extend(
            build_full_route_from_node(node.next_stop_node, visited)
        )

    return full_path


def match_chain(start_node, remaining_stops: list[int]) -> bool:
    """
    Check if the chain from start_node exactly matches remaining_stops
    """
    current = start_node

    for stop_id in remaining_stops:
        if not current:
            return False

        if current.stop_id != stop_id:
            return False

        # move forward (single next node)
        current = current.next_stop_node

    return True


def find_reusable_node(db, stop_id: int, remaining_stops: list[int]):
    """
    Find a stop node where the full downstream chain matches
    """
    candidates = db.query(StopNode).filter(
        StopNode.stop_id == stop_id
    ).all()

    for node in candidates:
        if match_chain(node, remaining_stops):
            return node

    return None


def find_matching_subsequence(
    db: Session,
    stop_nodes_data: list,
    exclude_route_id: int | None = None
):
    if not stop_nodes_data:
        return None

    target_stop_ids = [s.stop_id for s in stop_nodes_data]
    print(f"🔍 Matching against: {target_stop_ids}")

    for start_idx in range(len(target_stop_ids)):
        subsequence = target_stop_ids[start_idx:]

        # ❌ block single-stop merges ONLY
        if len(subsequence) < 2:
            continue

        candidates_q = db.query(StopNode).filter(
            StopNode.stop_id == subsequence[0]
        )

        if exclude_route_id:
            candidates_q = candidates_q.filter(
                StopNode.route_id != exclude_route_id
            )

        candidates = candidates_q.all()

        for candidate in candidates:

            # ❌ existing chain must continue
            if candidate.next_stop_node is None:
                continue

            if is_matching_chain(candidate, subsequence):
                chain = build_chain_from_node(candidate, len(subsequence))
                print(
                    f"✅ MERGE at stop {candidate.stop_id}, "
                    f"nodes {[n.id for n in chain]}"
                )
                return start_idx, chain

    print("❌ No merge found")
    return None


def is_matching_chain(
    start_node: StopNode,
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
    return True


def build_chain_from_node(
    start_node: StopNode,
    length: int
) -> list[StopNode]:
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
    node_to_delete: StopNode,
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


def build_route_with_full_stops(route: RouteTemplate):
    all_nodes: list[StopNode] = []
    visited = set()

    for node in route.stop_nodes:
        if not node.previous_stop_node:
            nodes_from_here = build_full_route_from_node(node, visited)

            # 🔒 SAFETY: only accept StopNode objects
            for n in nodes_from_here:
                if isinstance(n, StopNode):
                    all_nodes.append(n)

    # Deduplicate safely
    unique_nodes = {}
    for node in all_nodes:
        unique_nodes[node.id] = node

    route.stop_nodes = list(unique_nodes.values())
    return route

def attach_full_stop_nodes(route: RouteTemplate):
    all_nodes = []
    visited = set()

    for node in route.stop_nodes:
        if not node.previous_stop_node:  # starting nodes
            nodes_from_here = build_full_route_from_node(node, visited)
            all_nodes.extend(nodes_from_here)

    # Deduplicate nodes (branches safe)
    unique_nodes = {node.id: node for node in all_nodes}.values()
    route.stop_nodes = list(unique_nodes)

    return route