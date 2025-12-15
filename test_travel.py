import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api/travel"
AUTH_URL = "http://127.0.0.1:8000/api/auth" # Assuming auth routes exist

def test_travel_flow():
    print("Starting Travel Flow Verification...")

    # 1. Create Route
    route_data = {
        "name": "City Center to Airport",
        "source": {"type": "Point", "coordinates": [77.2090, 28.6139]}, # Delhi
        "destination": {"type": "Point", "coordinates": [72.8777, 19.0760]} # Mumbai
    }
    response = requests.post(f"{BASE_URL}/routes/", json=route_data)
    if response.status_code != 200:
        print(f"Failed to create route: {response.text}")
        return
    route_id = response.json()["id"]
    print(f"Route created: {route_id}")

    # 2. Create Stop
    stop_data = {
        "name": "Midway Halt",
        "location": {"type": "Point", "coordinates": [75.8577, 26.9124]} # Jaipur
    }
    response = requests.post(f"{BASE_URL}/stops/", json=stop_data)
    if response.status_code != 200:
        print(f"Failed to create stop: {response.text}")
        return
    stop_id = response.json()["id"]
    print(f"Stop created: {stop_id}")

    # 3. Create Bus (We need a driver first, but driver creation is complex due to auth)
    # For this test, we might need to manually insert a driver or assume one exists.
    # Or we can create a bus without driver first, then assign?
    # The requirement says "assign buses to driver".
    # Let's try to create a bus first.
    bus_data = {
        "plate_number": "DL-01-1234",
        "capacity": 40,
        "model": "Volvo 9400"
    }
    response = requests.post(f"{BASE_URL}/buses/", json=bus_data)
    if response.status_code != 200:
        print(f"Failed to create bus: {response.text}")
        # If plate number unique constraint fails, it might be due to previous runs.
        # Let's try to get existing bus.
        response = requests.get(f"{BASE_URL}/buses/")
        bus_id = response.json()[0]["id"]
        print(f"Using existing bus: {bus_id}")
    else:
        bus_id = response.json()["id"]
        print(f"Bus created: {bus_id}")

    # 4. Create Event
    # We need a driver_id. This is tricky without full auth flow.
    # Let's assume we can skip driver_id for now if nullable, or we need to mock it.
    # In our model, driver_id is nullable.
    # But our logic in routes.py checks for driver if driver_id is provided.
    # Let's try to create event without driver first to test basic flow.
    
    event_data = {
        "title": "Weekend Trip",
        "route_id": route_id,
        "from_date": (datetime.now() + timedelta(days=1)).isoformat(),
        "to_date": (datetime.now() + timedelta(days=2)).isoformat(),
        "total_tickets": 40,
        # "driver_id": 1, # Skipping for now as we don't have a valid driver profile ID easily
        "stops": [
            {
                "stop_id": stop_id,
                "price": 500.0,
                "arrival_time": (datetime.now() + timedelta(days=1, hours=4)).isoformat()
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/events/", json=event_data)
    if response.status_code != 200:
        print(f"Failed to create event: {response.text}")
        return
    event_id = response.json()["id"]
    print(f"Event created: {event_id}")

    # 5. Create Booking
    booking_data = {
        "event_id": event_id,
        "seats": 2
    }
    # We need a user_id. Again, tricky without auth.
    # Our route takes user_id as query param.
    # Let's assume user_id=1 exists (admin usually).
    response = requests.post(f"{BASE_URL}/bookings/?user_id=1", json=booking_data)
    if response.status_code != 200:
        print(f"Failed to create booking: {response.text}")
        return
    booking_id = response.json()["id"]
    print(f"Booking created: {booking_id}")

    print("Verification Completed Successfully!")

if __name__ == "__main__":
    test_travel_flow()
