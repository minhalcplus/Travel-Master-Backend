import uvicorn
import contextlib
import signal
import sys
from core.app.env import settings


class GracefulExit:
    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        self.shutdown = True
        sys.exit(0)


@contextlib.contextmanager
def graceful_shutdown():
    exit_handler = GracefulExit()
    try:
        yield exit_handler
    except KeyboardInterrupt:
        print("Server interrupted by user")
    finally:
        print("Cleanup completed")


if __name__ == "__main__":
    with graceful_shutdown():
        uvicorn.run(
            "core.app:app",
            host=settings.SERVER_HOST if settings.IS_PROD else '127.0.0.1',
            port=settings.PORT,
            reload=settings.IS_DEV,
            workers=settings.WORKERS if settings.IS_PROD else None
        )
