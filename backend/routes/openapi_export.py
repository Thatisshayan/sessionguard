"""
backend/routes/openapi_export.py
----------------------------------
Exports the OpenAPI schema and generates a typed TypeScript client stub.
Useful for keeping the frontend api.ts in sync with backend changes.

Maturity: Working Prototype
"""

from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse, JSONResponse

from backend.auth.access import require_admin

router = APIRouter(tags=["openapi"])


@router.get("/openapi/schema")
def get_schema(authorization: str | None = Header(None, alias="Authorization")):
    """Return the raw OpenAPI JSON schema."""
    require_admin(authorization)
    from backend.main import app
    return JSONResponse(app.openapi())


@router.get("/openapi/ts-client", response_class=PlainTextResponse)
def get_ts_client(authorization: str | None = Header(None, alias="Authorization")):
    """
    Generate a basic TypeScript API client stub from the OpenAPI schema.
    Copy-paste into your project or use as a reference.
    """
    require_admin(authorization)
    from backend.main import app
    schema = app.openapi()
    paths  = schema.get("paths", {})
    lines  = [
        "// SessionGuard API Client — auto-generated from OpenAPI schema",
        "// Do not edit manually — regenerate with GET /openapi/ts-client",
        "",
        "const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'",
        "",
        "async function _fetch(path: string, opts: RequestInit = {}) {",
        "  const token = sessionStorage.getItem('sg_access_token')",
        "  const headers: Record<string, string> = {",
        "    'Content-Type': 'application/json',",
        "    ...(token ? { Authorization: `Bearer ${token}` } : {}),",
        "    ...(opts.headers as Record<string, string> ?? {}),",
        "  }",
        "  const res = await fetch(`${BASE}${path}`, { ...opts, headers })",
        "  if (!res.ok) throw new Error(await res.text())",
        "  return res.json()",
        "}",
        "",
    ]

    method_map = {"get": "GET", "post": "POST", "patch": "PATCH",
                  "put": "PUT", "delete": "DELETE"}

    for path, methods in sorted(paths.items()):
        for method, op in methods.items():
            if method not in method_map:
                continue
            op_id   = op.get("operationId", "").replace("-", "_")
            summary = op.get("summary", "")
            has_body = method in ("post", "patch", "put")

            fn_args = "body?: Record<string, any>" if has_body else ""
            opts    = (
                "{ method: '" + method_map[method] + "', body: JSON.stringify(body) }"
                if has_body
                else f"{{ method: '{method_map[method]}' }}"
            )

            lines.append(f"/** {summary or path} */")
            lines.append(
                f"export const {op_id} = ({fn_args}) =>"
                f" _fetch(`{path.replace('{', '${').replace('}', '}')}`, {opts})"
            )
            lines.append("")

    return "\n".join(lines)
