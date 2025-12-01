from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .env import settings
from urllib.parse import quote_plus
from psycopg2 import OperationalError

# Create engine
engine = create_engine(
  settings.SQLALCHEMY_DB_URL,
  pool_size=10,
  max_overflow=20,
  pool_timeout=30,
  pool_pre_ping=True,
  pool_recycle=3600,
  echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
  """
  FastAPI dependency for database sessions
  """
  db = SessionLocal()
  try:
    # Test connection
    db.execute(text("SELECT 1"))
    yield db
  except Exception as e:
    db.close()
    raise
  finally:
    db.close()


def create_tables():
  """Create all tables"""
  Base.metadata.create_all(bind=engine)


def create_db_if_not_exists():
  """Create database if not there"""
  temp_engine = create_engine(
    f"postgresql://{settings.DB_USER}:{quote_plus(settings.DB_PASS)}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/postgres",
    isolation_level="AUTOCOMMIT"
  )
  try:
    with temp_engine.connect() as conn:
      result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname=:db_name"), {"db_name": settings.DB_NAME})
      if not result.scalar():
        # Create database if it doesn't exist
        conn.execute(text(f"CREATE DATABASE {settings.DB_NAME}"))
        print(f"Database '{settings.DB_NAME}' created successfully")
      else:
        print(f"Database '{settings.DB_NAME}' already exists")

  except OperationalError as e:
    print(f"Error checking/creating database: {e}")
  finally:
    temp_engine.dispose()


def health_check():
  """Check database health"""
  try:
    with engine.connect() as conn:
      result = conn.execute(text("SELECT 1"))
      return result.scalar() == 1
  except Exception:
    return False
