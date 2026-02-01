import sys
import uvicorn

if sys.platform == "win32":
    # see https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#windows
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)

from app.main import app

def serve():
    """Serve the web application."""
    uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False
        )

if __name__ == "__main__":
    serve()