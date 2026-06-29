ENFORCED_ROUTES = {
    "/api/users",
    "/api/data",
    "/api/export",
    "/admin/audit",
    "/admin/dashboard",
    "/internal/status",
}


class JWTMiddleware:
    """Selectively enforces JWT validation based on a hardcoded route set.

    This set intentionally diverges from the decorator declarations on several
    routes, creating the inconsistencies recorded in route_metadata.json.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path in ENFORCED_ROUTES:
            auth = environ.get("HTTP_AUTHORIZATION", "")
            if not auth.startswith("Bearer "):
                status = "401 Unauthorized"
                headers = [("Content-Type", "application/json")]
                start_response(status, headers)
                return [b'{"error": "middleware: missing token"}']
        return self.app(environ, start_response)
