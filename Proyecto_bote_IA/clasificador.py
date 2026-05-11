"""
clasificador.py — Agentic vision + tool-calling via direct HTTP requests.

Uses the OpenAI-compatible endpoint from LM Studio to:
  1. Receive a base64 image of the waste object.
  2. Decide via tool-calling whether it is orgánico or inorgánico.
  3. Return a status string: SUCCESS:...:ORGANICO / SUCCESS:...:INORGANICO /
     DISCARD:... / ERROR:...

Design notes:
  - Uses `requests` directly (no openai SDK) to match the project pattern.
  - Image is replaced in-context on retakes (saves tokens).
  - Up to MAX_TURNS agentic turns before giving up.
"""

import json
import requests
import tools
import camara

# === CONFIGURATION ===
API_URL        = "http://192.168.56.1:1234/v1/chat/completions"
LMSTUDIO_MODEL = "qwen/qwen3-vl-4b"
LMSTUDIO_API_KEY = "lm-studio"   # LM Studio does not validate the key
MAX_TURNS      = 5

SYSTEM_PROMPT = (
    "Eres un clasificador autónomo de residuos. "
    "Analiza la imagen y llama a la herramienta correcta con el nombre del objeto.\n\n"
    "REGLAS:\n"
    "- Orgánico (frutas, verduras, comida, cáscaras, restos biológicos) "
    "→ sort_as_organico(object_name='Nombre específico')\n"
    "- Inorgánico (plástico, botellas, latas, vidrio, papel, cartón, envases) "
    "→ sort_as_inorganico(object_name='Nombre específico')\n"
    "- Recipiente vacío o sin objeto visible → discard_object()\n"
    "- Imagen poco clara → get_camera_image() y luego clasifica.\n\n"
    "INSTRUCCIONES:\n"
    "1. Identifica el objeto con el mayor detalle posible "
    "(e.g. 'Botella PET transparente', 'Manzana roja').\n"
    "2. Llama a la herramienta correspondiente con object_name.\n"
    "3. Sin razonamiento extra, solo la llamada a la herramienta."
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LMSTUDIO_API_KEY}",
    }


def test_connection() -> bool:
    """Return True if LM Studio is reachable and responds to a minimal request."""
    try:
        payload = {
            "model": LMSTUDIO_MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }
        r = requests.post(API_URL, headers=_headers(), json=payload, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ─── Agentic loop ────────────────────────────────────────────────────────────

def act_on_waste(image_b64: str, on_message=None) -> str:
    """
    Run the agentic classification loop for one waste object.

    Args:
        image_b64:   Base64-encoded JPEG of the object.
        on_message:  Optional callback(role, content) for logging.

    Returns:
        One of:
          "SUCCESS:<object_name>:ORGANICO"
          "SUCCESS:<object_name>:INORGANICO"
          "DISCARD:<reason>"
          "ERROR:<reason>"
    """
    # Build the initial user message with the image
    user_content = [
        {"type": "text", "text": "Clasifica este residuo."},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        },
    ]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]

    for _ in range(MAX_TURNS):
        try:
            payload = {
                "model":       LMSTUDIO_MODEL,
                "messages":    messages,
                "tools":       tools.TOOLS_SCHEMA,
                "tool_choice": "auto",
            }

            response = requests.post(
                API_URL, headers=_headers(), json=payload, timeout=60
            )
            response.raise_for_status()

            res_json = response.json()
            msg = res_json["choices"][0]["message"]
            messages.append(msg)

            # Log assistant text if provided
            if on_message and msg.get("content"):
                on_message("assistant", msg["content"])

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                # No tool call — model returned plain text; treat as error
                return f"ERROR:No tool called — {msg.get('content', '')[:80]}"

            # Process every tool call in this turn
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                args      = json.loads(tool_call["function"].get("arguments", "{}"))

                if on_message:
                    on_message("tool", f"{func_name}({args})")

                # ── get_camera_image: replace image in context, don't return ──
                if func_name == "get_camera_image":
                    new_img = camara.get_camera_data()
                    if new_img:
                        messages[1]["content"][1]["image_url"]["url"] = (
                            f"data:image/jpeg;base64,{new_img}"
                        )
                        result = "NEW_IMAGE_READY"
                    else:
                        result = "ERROR:Capture failed"

                # ── known tools ───────────────────────────────────────────────
                elif func_name in tools.AVAILABLE_FUNCTIONS:
                    result = tools.AVAILABLE_FUNCTIONS[func_name](**args)

                else:
                    result = f"ERROR:Unknown tool '{func_name}'"

                # Append tool result to conversation
                messages.append({
                    "role":        "tool",
                    "content":     result,
                    "tool_call_id": tool_call["id"],
                })

                # Terminal outcomes — return immediately
                if result.startswith(("SUCCESS", "DISCARD")):
                    return result

        except requests.RequestException as e:
            return f"ERROR:HTTP error — {e}"
        except Exception as e:
            return f"ERROR:Agent failure — {e}"

    return "ERROR:Max turns reached without a decision"
