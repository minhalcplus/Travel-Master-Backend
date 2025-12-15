"""
Migration script to update stops table:
- Change county (string) to county_id (foreign key)
- This will drop the old county column and add the new county_id column
- WARNING: This will lose existing stop data if any exists
"""
from sqlalchemy import create_engine, text
from core.app.env import settings

def migrate_stops_county_field():
    """Migrate stops table from county string to county_id foreign key"""
    engine = create_engine(settings.SQLALCHEMY_DB_URL)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if stops table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'stops'
                    );
                """))
                table_exists = result.scalar()
                
                if not table_exists:
                    print("✅ Stops table doesn't exist yet. No migration needed.")
                    print("   The table will be created with the correct schema on server restart.")
                    return
                
                # Check if county column exists (old schema)
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'stops' AND column_name = 'county'
                    );
                """))
                has_old_column = result.scalar()
                
                # Check if county_id column exists (new schema)
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'stops' AND column_name = 'county_id'
                    );
                """))
                has_new_column = result.scalar()
                
                if has_new_column and not has_old_column:
                    print("✅ Migration already completed. Stops table has county_id column.")
                    return
                
                if has_old_column:
                    # Check if there are any existing stops
                    result = conn.execute(text("SELECT COUNT(*) FROM stops;"))
                    stop_count = result.scalar()
                    
                    if stop_count > 0:
                        print(f"⚠️  WARNING: Found {stop_count} existing stops.")
                        print("   This migration will DELETE all existing stops.")
                        response = input("   Continue? (yes/no): ")
                        
                        if response.lower() not in ['yes', 'y']:
                            print("❌ Migration cancelled.")
                            trans.rollback()
                            return
                        
                        # Delete all stops
                        conn.execute(text("DELETE FROM stops;"))
                        print(f"   Deleted {stop_count} stops.")
                    
                    # Drop the old county column
                    conn.execute(text("ALTER TABLE stops DROP COLUMN county;"))
                    print("✅ Dropped old 'county' column")
                
                # Add the new county_id column if it doesn't exist
                if not has_new_column:
                    conn.execute(text("""
                        ALTER TABLE stops 
                        ADD COLUMN county_id INTEGER NOT NULL 
                        REFERENCES counties(id);
                    """))
                    print("✅ Added new 'county_id' column with foreign key")
                    
                    # Add index on county_id
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_stops_county_id 
                        ON stops(county_id);
                    """))
                    print("✅ Created index on 'county_id'")
                
                # Commit transaction
                trans.commit()
                print("\n✅ Migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Stops Table Migration: county -> county_id")
    print("=" * 60)
    print()
    
    migrate_stops_county_field()
    
    print()
    print("=" * 60)
    print("Please restart your server for changes to take effect.")
    print("=" * 60)
