import httpx
import json

BASE_URL = "http://localhost:8002"

def test_create_route():
    # 1. Create some stops first (or assume they exist)
    # Let's try to create a couple of stops to be sure
    headers = {"Content-Type": "application/json"}
    
    stop1_data = {
        "name": "Test Stop A",
        "location": "Location A",
        "lat": 53.3498,
        "lng": -6.2603,
        "county": "Dublin" # Assuming seeded with Dublin
    }
    stop2_data = {
        "name": "Test Stop B",
        "location": "Location B",
        "lat": 53.3500,
        "lng": -6.2600,
        "county": "Dublin" 
    }
    
    # Use httpx.Client for requests
    with httpx.Client() as client:
        # Check if county Dublin exists, if not we might fail.
        # We can use the existing seed script or just try to create stops.
        
        s1 = client.post(f"{BASE_URL}/api/travel/stops/", json=stop1_data)
        s2 = client.post(f"{BASE_URL}/api/travel/stops/", json=stop2_data)
        
        if s1.status_code != 200 or s2.status_code != 200:
            print(f"Failed to create stops: {s1.text}, {s2.text}")
            return

        stop1_id = s1.json()['id']
        stop2_id = s2.json()['id']
        print(f"Created stops: {stop1_id}, {stop2_id}")

        # 2. Create Route
        route_data = {
            "name": "Test Route 1",
            "start_location": "Start",
            "destination": "End",
            "is_active": True,
            "stops": [
                {"stop_id": stop1_id, "price": 10.5},
                {"stop_id": stop2_id, "price": 15.0}
            ]
        }
        
        response = client.post(f"{BASE_URL}/api/travel/routes/", json=route_data)
        if response.status_code == 200:
            print("Route created successfully!")
            route = response.json()
            print(json.dumps(route, indent=2))
            
            # Verify Linked List / Graph
            stops = route['stops']
            if len(stops) == 2:
                # stops[0] should have stops[1] in its next_stops
                # stops[1] should have stops[0] in its prev_stops
                
                s1_next_ids = [s['id'] for s in stops[0]['next_stops']]
                s2_prev_ids = [s['id'] for s in stops[1]['prev_stops']]

                print(f"Stop 1 Next IDs: {s1_next_ids}")
                print(f"Stop 2 Prev IDs: {s2_prev_ids}")
                
                if stops[1]['id'] in s1_next_ids and stops[0]['id'] in s2_prev_ids:
                     print("Graph structure verified (M2M)!")
                else:
                     print("Graph structure seems WRONG.")
        else:
            print(f"Failed to create route: {response.text}")

if __name__ == "__main__":
    test_create_route()
