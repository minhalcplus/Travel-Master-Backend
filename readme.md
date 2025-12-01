# FastAPI Starter

## Custom User Defined Directories and Mount in FastAPI

To add custom directories that will be created and mounted as static file servers in your FastAPI application, follow these steps:

### 1. Create Configuration File

Create a file at the root of your project: `user_config/file_storage.py`

### 2. Add Directory Configuration

In the `user_config/file_storage.py` file, define your custom directories:

```python
from core.app.env import BASE_DIR

initial_dirs = [
    {'name': 'storage', 'path': BASE_DIR / "storage", 'mount_point': '/storage'}
]