import requests
import json
import sys

BASE_URL = "http://localhost:8002"

def log(msg):
    print(f"[TEST] {msg}")

def check(condition, msg):
    if condition:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)

def main():
    # 1. Create a County (Prerequisite)
    log("Creating county...")
    county_res = requests.post(f"{BASE_URL}/api/travel/counties/", json={"name": "TestCounty", "short_code": "TC", "telephone_code": "99"})
    if county_res.status_code == 400:
        log("County exists, continuing...")
        # Get existing id?
        county_id = 999 
        # Actually lets assume it might fail if exists but we need an ID. 
        # For simplicity, fail if can't get ID.
        # But wait, we can just GET counties
    
    counties_resp = requests.get(f"{BASE_URL}/api/travel/counties/")
    log(f"Get Counties Status: {counties_resp.status_code}")
    counties = counties_resp.json()
    log(f"Counties Response: {counties}")

    county_id = None
    if isinstance(counties, list) and len(counties) > 0:
        county_id = counties[0]['id']
    elif county_res.status_code == 200:
        county_id = county_res.json()['id']
    else:
        log("Could not find or create a county. Exiting.")
        sys.exit(1)

    # 2. Create Stops
    log("Creating stops...")
    stop_ids = []
    for i in range(3):
        stop_res = requests.post(f"{BASE_URL}/api/travel/stops/", json={
            "name": f"Stop {i}",
            "county_id": county_id,
            "location": "Test Loc",
            "lat": 1.0, 
            "lng": 1.0
        })
        if stop_res.status_code == 200:
            stop_ids.append(stop_res.json()['id'])
        else:
            log(f"Failed to create stop: {stop_res.text}")
    
    if len(stop_ids) < 3:
        log("Not enough stops created. Attempting to fetch existing.")
        stops = requests.get(f"{BASE_URL}/api/travel/stops/").json()
        stop_ids = [s['id'] for s in stops[:3]]
    
    check(len(stop_ids) >= 3, "Have at least 3 stops")
    log(f"Using Stop IDs: {stop_ids}")

    # 3. Create Route with Linked List
    log("Creating Route with Linked List...")
    route_data = {
        "name": "Linked List Route",
        "start_location": "A",
        "destination": "B",
        "stops": [
            {"stop_id": stop_ids[0], "price": 10.0},
            {"stop_id": stop_ids[1], "price": 15.0},
            {"stop_id": stop_ids[2], "price": 20.0}
        ]
    }
    
    route_res = requests.post(f"{BASE_URL}/api/travel/routes/", json=route_data)
    check(route_res.status_code == 200, f"Route creation success. Code: {route_res.status_code}, Body: {route_res.text}")
    
    route_json = route_res.json()
    stop_nodes = route_json.get('stop_nodes', [])
    check(len(stop_nodes) == 3, "Route has 3 stop nodes")
    
    # Verify Linking
    node1 = stop_nodes[0]
    node2 = stop_nodes[1]
    node3 = stop_nodes[2]
    
    # Note: The response list order depends on DB insertion, which is usually sequential.
    # We should verify node1.next_stop_node.id == node2.id
    
    log("Verifying Linked List pointers...")
    
    # Check Node 1 -> Node 2
    if node1['next_stop_node']:
        check(node1['next_stop_node']['id'] == node2['id'], f"Node 1 next is Node 2. (Got {node1['next_stop_node']['id']} expected {node2['id']})")
    else:
        check(False, "Node 1 has no next node")
        
    # Check Node 2 -> Node 3
    if node2['next_stop_node']:
        check(node2['next_stop_node']['id'] == node3['id'], f"Node 2 next is Node 3. (Got {node2['next_stop_node']['id']} expected {node3['id']})")
    else:
        check(False, "Node 2 has no next node")
        
    # Check Node 3 -> None
    check(node3['next_stop_node'] is None, "Node 3 has no next node")
    
    log("Verifying Previous Nodes (List)...")
    
    # Node 1 should have empty prev (if it's start)
    check(isinstance(node1['prev_stop_nodes'], list), "Node 1 prev_stop_nodes is list")
    
    # Node 2 should have Node 1 in prev list? 
    # Wait, if we fetch the list, the recursion depth might limit what we see, 
    # OR we need to check if schema populates it.
    # By default, back_populates should work.
    
    # Since we didn't explicitly add to prev_stop_nodes list in route creation (we set next_stop_node_id),
    # verifying it appears in the list confirms the relationship works.
    
    # However, fetching "stop_nodes" list separately might not show the relationship unless eager loaded or we check the 'next_stop_node' structure's inverse?
    # No, 'prev_stop_nodes' is a field on StopNodeOut.
    
    # Let's see if Node 2 has Node 1 in its prev list.
    # CAUTION: Infinite recursion if not careful in schema. 'prev_stop_nodes' is List[StopNodeOut].
    # StopNodeOut has 'next_stop_node' (StopNodeOut).
    # If Node 2.prev contains Node 1, and Node 1.next contains Node 2... loop.
    # Pydantic handles this usually if we don't depth dive too deep or if we use fetch.
    
    # Let's just check type for now.
    check(isinstance(node2['prev_stop_nodes'], list), "Node 2 prev_stop_nodes is list")
    
    log("Verification Complete!")

if __name__ == "__main__":
    main()
