from subprocess import run
from core.app.env import BASE_DIR
from .file_storage import initial_dirs
import shutil
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from os import makedirs


def clearPyCache():
    try:
        print(f"Cleaning __pycache__ in: {BASE_DIR}")

        # Use Python to clean pycache instead of bash
        pycache_dirs = list(Path(BASE_DIR).rglob("__pycache__"))
        for pycache_dir in pycache_dirs:
            if pycache_dir.is_dir():
                shutil.rmtree(pycache_dir)
                print(f"Removed: {pycache_dir}")

        print(f"✅ Cleaned up {len(pycache_dirs)} __pycache__ directories")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


def create_initial_dirs():
    try:
        for dir in initial_dirs:
            makedirs(dir["path"], exist_ok=True)
            print(f"Created directory: {dir['path']}")

    except Exception as e:
        print(f"❌ failed to create: {e}")


def create_and_mount_initial_dirs(app: FastAPI):
    try:
        for dir_config in initial_dirs:
            path = dir_config["path"]
            mount_point = dir_config["mount_point"]
            name = dir_config["name"]
            if path.exists() and path.is_dir():
                print(f"📁 Directory exists: {path}")
            else:
                try:
                    makedirs(path, exist_ok=True)
                    print(f"✅ Created directory: {path}")
                except OSError as e:
                    print(f"❌ Failed to create directory {path}: {e}")
                    continue
            try:
                app.mount(mount_point, StaticFiles(directory=path), name=name)
                print(f"🔗 Mounted '{name}' at {mount_point}")
            except Exception as e:
                print(f"❌ Failed to mount {mount_point}: {e}")

    except Exception as e:
        print(f"❌ Unexpected error in directory setup: {e}")
