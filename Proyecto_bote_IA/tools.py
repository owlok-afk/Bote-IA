"""
tools.py — Sorting tools exposed to the LLM agent.

Maps AI decisions to physical Arduino commands:
  - sort_as_organico   → ORGANICO command  (servo left)
  - sort_as_inorganico → INORGANICO command (servo right)
  - discard_object     → no movement, just log
  - get_camera_image   → captures a fresh frame

All tool functions return a string starting with:
  SUCCESS:...  → terminal, object sorted
  DISCARD:...  → terminal, object ignored
  ERROR:...    → failure
  NEW_IMAGE_READY:...  → non-terminal, continue loop
"""

import arduino
import camara

# === TOOL IMPLEMENTATIONS ===

def sort_as_organico(object_name: str = "Residuo") -> str:
    """Sort the detected object into the ORGANIC waste bin (servo left)."""
    result = arduino.classify_as_organico()
    if result["success"]:
        return f"SUCCESS:{object_name}:ORGANICO"
    return f"ERROR:Sorting failed for {object_name}: {result.get('error', result.get('response'))}"


def sort_as_inorganico(object_name: str = "Residuo") -> str:
    """Sort the detected object into the INORGANIC waste bin (servo right)."""
    result = arduino.classify_as_inorganico()
    if result["success"]:
        return f"SUCCESS:{object_name}:INORGANICO"
    return f"ERROR:Sorting failed for {object_name}: {result.get('error', result.get('response'))}"


def discard_object() -> str:
    """Discard the object — nothing visible or unrecognized."""
    return "DISCARD:No waste object detected"


def get_camera_image() -> str:
    """Capture a fresh photo from the camara."""
    image_b64 = camara.get_camera_data()
    if image_b64 is None:
        return "ERROR:Camera unavailable"
    return f"NEW_IMAGE_READY:{image_b64}"


# === API SCHEMAS (OpenAI tool-calling format) ===

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "sort_as_organico",
            "description": (
                "Sort the detected object into the ORGANIC bin. "
                "Use for: fruits, vegetables, food scraps, peels, "
                "any biological/compostable material."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": (
                            "Specific name of the object "
                            "(e.g. 'Manzana', 'Cáscara de naranja', 'Lechuga')."
                        )
                    }
                },
                "required": ["object_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_as_inorganico",
            "description": (
                "Sort the detected object into the INORGANIC bin. "
                "Use for: plastic bottles, cans, glass, cardboard, "
                "paper, wrappers, any non-biodegradable material."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": (
                            "Specific name of the object "
                            "(e.g. 'Botella de plástico', 'Lata de aluminio', 'Caja de cartón')."
                        )
                    }
                },
                "required": ["object_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discard_object",
            "description": (
                "Discard when the container is empty or no object "
                "is clearly visible in the image."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_camera_image",
            "description": "Take another photo if the first one was unclear or blurry.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

# Dispatcher: maps function name → callable
AVAILABLE_FUNCTIONS = {
    "sort_as_organico":   sort_as_organico,
    "sort_as_inorganico": sort_as_inorganico,
    "discard_object":     discard_object,
    "get_camera_image":   get_camera_image,
}
