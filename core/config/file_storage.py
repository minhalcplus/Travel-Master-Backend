from core.app.env import BASE_DIR

initial_dirs = [
    {'name': 'public', 'path': BASE_DIR / "public", 'mount_point': '/public'}
]

try:
    # Try to import user configuration
    from user_config.file_storage import initial_dirs as user_initial_dirs
    
    # Validate that it's a list before extending
    if isinstance(user_initial_dirs, list):
        initial_dirs.extend(user_initial_dirs)
        print(f"✅ Loaded {len(user_initial_dirs)} user directories")
    else:
        print("⚠️  User initial_dirs is not a list, using defaults only")
        
except ModuleNotFoundError:
    # Module doesn't exist at all - this is normal
    print("ℹ️  No user configuration found, using defaults only")
except ImportError as e:
    # Module exists but initial_dirs not found
    if "initial_dirs" in str(e):
        print("ℹ️  user_config.file_storage exists but initial_dirs not found")
    else:
        print(f"ℹ️  Import error: {e}")
except Exception as e:
    # Any other unexpected error
    print(f"⚠️  Unexpected error loading user config: {e}")