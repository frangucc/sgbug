from http.server import HTTPServer, SimpleHTTPRequestHandler
import sqlite3
import json
from urllib.parse import urlparse, parse_qs
import webbrowser
from threading import Timer

class APIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        
        if url.path == '/api/file-analysis':
            self.handle_file_analysis(parse_qs(url.query))
        else:
            super().do_GET()
    
    def handle_file_analysis(self, query):
        commit_hash = query.get('commit', [''])[0]
        file_path = query.get('file', [''])[0]
        
        if not commit_hash or not file_path:
            self.send_error(400, "Missing commit hash or file path")
            return
        
        try:
            conn = sqlite3.connect('commits_2025.db')
            cursor = conn.cursor()
            
            # Get function changes
            cursor.execute('''
                SELECT function_name, change_type, new_signature, change_description
                FROM function_changes
                WHERE commit_hash = ? AND file_path = ?
            ''', (commit_hash, file_path))
            
            functions = [{
                'name': row[0],
                'change_type': row[1],
                'signature': row[2],
                'description': row[3]
            } for row in cursor.fetchall()]
            
            # Get dependencies
            cursor.execute('''
                SELECT target_file, dependency_type
                FROM file_dependencies
                WHERE source_file = ? AND first_seen_commit = ?
            ''', (file_path, commit_hash))
            
            dependencies = [{
                'target_file': row[0],
                'type': row[1]
            } for row in cursor.fetchall()]
            
            response = {
                'functions': functions,
                'dependencies': dependencies
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
        finally:
            conn.close()

def open_browser():
    webbrowser.open('http://localhost:8000/commits_report.html')

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, APIHandler)
    Timer(1.5, open_browser).start()
    print("Server running at http://localhost:8000/commits_report.html")
    print("Press Ctrl+C to stop the server")
    httpd.serve_forever()
