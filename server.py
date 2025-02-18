from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open('http://localhost:8000/commits_report.html')

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    Timer(1.5, open_browser).start()  # Open browser after server starts
    print("Server running at http://localhost:8000/commits_report.html")
    print("Press Ctrl+C to stop the server")
    httpd.serve_forever()
