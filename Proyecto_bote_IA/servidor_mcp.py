"""
mcp_service.py — MCP server exposing waste sorter tools.

This is a COMPLEMENTARY component to service.py. It exposes the same
hardware functions as MCP tools for use with external MCP clients
(e.g., Claude Desktop, LM Studio with MCP support).

service.py does NOT require this file — it drives hardware directly.
Use this only when you want an MCP client to call the machine.

Usage:
    python mcp_service.py

Endpoints (SSE):
    http://0.0.0.0:8766/mcp

Authentication:
    Bearer token required. Set API_KEY below and pass it as:
      Authorization: Bearer <API_KEY>
"""

import requests as _requests
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import arduino
import camara
import tools as _tools

# === CONFIGURATION ===
CLIENT_URL = "http://localhost:8765"   # service.py HTTP API (if used separately)
API_PORT   = 8766
API_KEY    = "sk-lm-vsR7LD9g:LJQySs0LsvLaf3Dpo0Se"   # Change this!

# === APP ===
app = FastMCP(
    name="Waste Classifier Machine Control",
    instructions="""
    Tools for controlling a waste sorting machine with Arduino and camara.
    Sensor: VL53L0X laser (I2C). Detection range: 3–13 cm.
    Available tools:

    - ping_machine      : Test Arduino connection
    - get_distance      : Read VL53L0X sensor distance in cm
    - wait_for_object   : Block until an object is detected (threshold default 13 cm)
    - capture_photo     : Capture a photo from the camera (returns base64 JPEG)
    - sort_as_organico  : Sort object into the ORGANIC bin (servo left)
    - sort_as_inorganico: Sort object into the INORGANIC bin (servo right)
    """,
)


# === BEARER AUTH MIDDLEWARE ===

class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
        if token != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


# === MCP TOOLS ===

@app.tool()
def ping_machine() -> dict:
    """Test the connection to the Arduino."""
    return arduino.ping()


@app.tool()
def get_distance() -> dict:
    """Get the current VL53L0X laser sensor distance in cm."""
    return {"distance_cm": arduino.get_distance()}


@app.tool()
def wait_for_object(threshold_cm: float = 13.0, timeout_seconds: int = 30) -> dict:
    """
    Block until a waste object is detected within threshold_cm.

    Args:
        threshold_cm:     Detection distance threshold in cm (default: 13.0)
        timeout_seconds:  Maximum seconds to wait (default: 30)
    """
    return arduino.wait_for_object(
        threshold_cm=threshold_cm,
        timeout_seconds=timeout_seconds,
    )


@app.tool()
def capture_photo() -> dict:
    """Capture a photo from the camera and return it as base64 JPEG."""
    image_b64 = camara.get_camera_data()
    if image_b64 is None:
        return {"error": "Camera not available."}
    return {"image_b64": image_b64}


@app.tool()
def sort_as_organico(object_name: str = "Residuo") -> str:
    """
    Sort the current object into the ORGANIC waste bin (servo left).

    Args:
        object_name: Human-readable name of the identified object.
    """
    return _tools.sort_as_organico(object_name=object_name)


@app.tool()
def sort_as_inorganico(object_name: str = "Residuo") -> str:
    """
    Sort the current object into the INORGANIC waste bin (servo right).

    Args:
        object_name: Human-readable name of the identified object.
    """
    return _tools.sort_as_inorganico(object_name=object_name)


# === ENTRY POINT ===

if __name__ == "__main__":
    import uvicorn

    starlette_app = app.http_app(path="/mcp")
    starlette_app.add_middleware(BearerAuthMiddleware)

    print(f"♻️  MCP Waste Sorter corriendo en http://0.0.0.0:{API_PORT}/mcp")
    uvicorn.run(starlette_app, host="0.0.0.0", port=API_PORT)
