"""
Seed script to populate Irish counties data
Run this script to add all 26 counties of Ireland to the database
"""
from sqlalchemy.orm import Session
from core.app.database import SessionLocal, engine
from travel.models import County

# All 26 counties of Ireland with their information
IRISH_COUNTIES = [
    {"name": "  ", "short_code": "CW", "telephone_code": "059"},
    {"name": "Cavan", "short_code": "CN", "telephone_code": "049"},
    {"name": "Clare", "short_code": "CE", "telephone_code": "065"},
    {"name": "Cork", "short_code": "CO", "telephone_code": "021"},
    {"name": "Donegal", "short_code": "DL", "telephone_code": "074"},
    {"name": "Dublin", "short_code": "D", "telephone_code": "01"},
    {"name": "Galway", "short_code": "G", "telephone_code": "091"},
    {"name": "Kerry", "short_code": "KY", "telephone_code": "066"},
    {"name": "Kildare", "short_code": "KE", "telephone_code": "045"},
    {"name": "Kilkenny", "short_code": "KK", "telephone_code": "056"},
    {"name": "Laois", "short_code": "LS", "telephone_code": "057"},
    {"name": "Leitrim", "short_code": "LM", "telephone_code": "071"},
    {"name": "Limerick", "short_code": "LK", "telephone_code": "061"},
    {"name": "Longford", "short_code": "LD", "telephone_code": "043"},
    {"name": "Louth", "short_code": "LH", "telephone_code": "042"},
    {"name": "Mayo", "short_code": "MO", "telephone_code": "094"},
    {"name": "Meath", "short_code": "MH", "telephone_code": "046"},
    {"name": "Monaghan", "short_code": "MN", "telephone_code": "047"},
    {"name": "Offaly", "short_code": "OY", "telephone_code": "057"},
    {"name": "Roscommon", "short_code": "RN", "telephone_code": "090"},
    {"name": "Sligo", "short_code": "SO", "telephone_code": "071"},
    {"name": "Tipperary", "short_code": "TA", "telephone_code": "052"},
    {"name": "Waterford", "short_code": "WD", "telephone_code": "051"},
    {"name": "Westmeath", "short_code": "WH", "telephone_code": "044"},
    {"name": "Wexford", "short_code": "WX", "telephone_code": "053"},
    {"name": "Wicklow", "short_code": "WW", "telephone_code": "0404"},
]


def seed_counties():
    """Seed the database with Irish counties"""
    db: Session = SessionLocal()
    
    try:
        # Check if counties already exist
        existing_count = db.query(County).count()
        
        if existing_count > 0:
            print(f"⚠️  Database already contains {existing_count} counties.")
            response = input("Do you want to clear existing data and reseed? (yes/no): ")
            
            if response.lower() in ['yes', 'y']:
                # Delete all existing counties
                db.query(County).delete()
                db.commit()
                print("✅ Cleared existing counties")
            else:
                print("❌ Seeding cancelled")
                return
        
        # Add all counties
        added_count = 0
        for county_data in IRISH_COUNTIES:
            county = County(**county_data)
            db.add(county)
            added_count += 1
        
        db.commit()
        print(f"\n✅ Successfully added {added_count} Irish counties to the database!")
        print("\nCounties added:")
        
        # Display all added counties
        counties = db.query(County).order_by(County.name).all()
        for county in counties:
            print(f"  - {county.name} ({county.short_code}) - Tel: {county.telephone_code}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding counties: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Irish Counties Seed Script")
    print("=" * 60)
    print(f"This will add all {len(IRISH_COUNTIES)} counties of Ireland to the database.\n")
    
    seed_counties()
    
    print("\n" + "=" * 60)
    print("Seeding complete!")
    print("=" * 60)
