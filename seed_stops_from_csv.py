"""
Seed script to populate stops from CSV file
"""
import csv
import os
from sqlalchemy.orm import Session
from core.app.database import SessionLocal
from travel.models import Stop, County

CSV_FILE = "Copy of Maps Master _ PUP Codes - Sheet1.csv"

# Mapping from RouteName in CSV to County Name in DB
ROUTE_TO_COUNTY_MAP = {
    "CK": "Cork",
    "DG": "Donegal",
    "GY": "Galway",
    "KY": "Kerry",
    "MO": "Mayo",
    "SO": "Sligo",
    "WD": "Waterford",
    "WX": "Wexford"
}

def seed_stops_from_csv():
    """Seed stops from CSV file"""
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV file not found: {CSV_FILE}")
        return

    db: Session = SessionLocal()
    
    try:
        # Pre-fetch counties to minimize DB queries
        counties = db.query(County).all()
        county_map = {c.name.lower(): c.id for c in counties}
        
        # Also map by short code just in case
        county_code_map = {c.short_code: c.id for c in counties}

        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            added_count = 0
            skipped_count = 0
            
            print(f"Reading from {CSV_FILE}...")
            
            for row in reader:
                route_name = row.get('RouteName', '').strip()
                stop_order = row.get('StopOrder', '').strip()
                city = row.get('City', '').strip()
                location = row.get('Location', '').strip()
                lat_str = row.get('Lat', '').strip()
                lon_str = row.get('Lon', '').strip()
                
                if not route_name or not city:
                    print(f"⚠️  Skipping row with missing RouteName or City: {row}")
                    skipped_count += 1
                    continue
                
                # Construct the name as requested: routename-stoporder-city
                # Example: CK-1-bantry
                stop_name = f"{route_name}-{stop_order}-{city}"
                
                # Find county_id
                county_id = None
                
                # 1. Try mapping from RouteName
                mapped_county_name = ROUTE_TO_COUNTY_MAP.get(route_name)
                if mapped_county_name:
                    county_id = county_map.get(mapped_county_name.lower())
                
                # 2. If not found, try using RouteName as short code
                if not county_id:
                    county_id = county_code_map.get(route_name)
                
                # 3. If still not found, try using City as County name (unlikely but possible)
                if not county_id:
                    county_id = county_map.get(city.lower())

                if not county_id:
                    print(f"⚠️  Could not find county for RouteName: {route_name} (City: {city}). Skipping.")
                    skipped_count += 1
                    continue
                
                # Parse lat/lon
                try:
                    lat = float(lat_str) if lat_str else 0.0
                    lng = float(lon_str) if lon_str else 0.0
                except ValueError:
                    print(f"⚠️  Invalid coordinates for {stop_name}: {lat_str}, {lon_str}")
                    lat = 0.0
                    lng = 0.0

                # Check if stop already exists (optional, but good practice)
                existing_stop = db.query(Stop).filter(Stop.name == stop_name).first()
                if existing_stop:
                    print(f"ℹ️  Stop already exists: {stop_name}. Updating...")
                    existing_stop.county_id = county_id
                    existing_stop.location = location
                    existing_stop.lat = lat
                    existing_stop.lng = lng
                else:
                    new_stop = Stop(
                        name=stop_name,
                        county_id=county_id,
                        location=location,
                        lat=lat,
                        lng=lng
                    )
                    db.add(new_stop)
                    added_count += 1
            
            db.commit()
            print(f"\n✅ Seeding complete!")
            print(f"   Added/Updated: {added_count}")
            print(f"   Skipped: {skipped_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding stops: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_stops_from_csv()
