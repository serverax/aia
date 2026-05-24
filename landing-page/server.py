#!/usr/bin/env python3
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super().end_headers()

    def do_GET(self):
        # Serve index.html for root
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()


os.chdir(DIRECTORY)

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"🚀 Server running at http://localhost:{PORT}")
    print(f"📂 Serving from: {DIRECTORY}")
    print(f"📄 Main file: {DIRECTORY}/index.html")
    print("")
    print("Open your browser to: http://localhost:8000")
    print("")
    print("Press Ctrl+C to stop")
    print("")
    httpd.serve_forever()
