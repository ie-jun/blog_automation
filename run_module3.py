"""Module 3 entry point — starts the FastAPI style guide server with uvicorn."""

import uvicorn

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "modules.style.web_app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
    )
