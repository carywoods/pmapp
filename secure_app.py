import base64
import hmac
import os
from http.server import HTTPServer

import app

DATA_DIR = os.environ.get("DATA_DIR", "/mnt/data")
CSV_FILENAME = os.environ.get("CSV_FILENAME", "idea_census_project_registry_ic_numbers.csv")
APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
PORT = int(os.environ.get("PORT", 8765))

app.CSV_FILE = os.path.join(DATA_DIR, CSV_FILENAME)
app.BACKUP_DIR = os.path.join(DATA_DIR, "backups")
app.PORT = PORT

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(app.BACKUP_DIR, exist_ok=True)


class SecureRequestHandler(app.RequestHandler):
    def is_authenticated(self):
        if not APP_PASSWORD:
            return False

        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return False

        try:
            encoded = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            return False

        return (
            hmac.compare_digest(username, APP_USERNAME)
            and hmac.compare_digest(password, APP_PASSWORD)
        )

    def require_auth(self):
        if not APP_PASSWORD:
            self.send_response(503)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"APP_PASSWORD is not set. Configure APP_USERNAME and APP_PASSWORD in Coolify."
            )
            return False

        if not self.is_authenticated():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Idea Census Registry"')
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Authentication required.")
            return False

        return True

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/healthz":
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        if not self.require_auth():
            return

        return super().do_GET()

    def do_POST(self):
        if not self.require_auth():
            return

        return super().do_POST()


def run():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, SecureRequestHandler)
    print("========================================")
    print("Secure Idea Census Registry Web App")
    print(f"Running at: http://{server_address[0]}:{server_address[1]}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Using CSV file: {app.CSV_FILE}")
    print(f"Backups directory: {app.BACKUP_DIR}/")
    print(f"Authentication: {'enabled' if APP_PASSWORD else 'BLOCKED, APP_PASSWORD not set'}")
    print("========================================")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
