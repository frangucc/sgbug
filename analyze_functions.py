import sqlite3
import subprocess
import re
from typing import List, Dict, Tuple
import ast
import os

class FunctionAnalyzer:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def get_file_content_at_commit(self, repo_path: str, commit_hash: str, file_path: str) -> str:
        """Get file content at a specific commit"""
        try:
            result = subprocess.run(
                ['git', 'show', f'{commit_hash}:{file_path}'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            print(f"Error getting file content: {str(e)}")
            return ""

    def analyze_typescript_functions(self, content: str) -> List[Dict]:
        """Analyze TypeScript/JavaScript functions using regex"""
        functions = []
        
        # Pattern for function declarations, including arrow functions and class methods
        patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.*?)\)',  # Regular functions
            r'(?:public|private|protected)?\s*(?:async\s+)?(\w+)\s*\((.*?)\)\s*{',  # Class methods
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>',  # Arrow functions
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                func_name = match.group(1)
                params = match.group(2)
                
                # Find the function body
                start_pos = match.end()
                body = self._extract_function_body(content[start_pos:])
                
                functions.append({
                    'name': func_name,
                    'parameters': params.strip(),
                    'body': body,
                    'signature': f'{func_name}({params.strip()})'
                })

        return functions

    def analyze_csharp_functions(self, content: str) -> List[Dict]:
        """Analyze C# functions using regex"""
        functions = []
        
        # Pattern for C# methods
        pattern = r'(?:public|private|protected|internal)?\s*(?:async\s+)?(?:[\w<>[\]]+\s+)?(\w+)\s*\((.*?)\)'
        
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            func_name = match.group(1)
            params = match.group(2)
            
            # Find the function body
            start_pos = match.end()
            body = self._extract_function_body(content[start_pos:])
            
            functions.append({
                'name': func_name,
                'parameters': params.strip(),
                'body': body,
                'signature': f'{func_name}({params.strip()})'
            })

        return functions

    def _extract_function_body(self, content: str) -> str:
        """Extract function body by matching braces"""
        body = ""
        brace_count = 0
        found_first_brace = False
        
        for char in content:
            if char == '{':
                found_first_brace = True
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            
            if found_first_brace:
                body += char
                if brace_count == 0:
                    break
        
        return body.strip()

    def find_dependencies(self, content: str, file_path: str) -> List[Dict]:
        """Find file dependencies"""
        dependencies = []
        
        # TypeScript/JavaScript imports
        import_patterns = [
            r'import\s+.*?from\s+[\'"](.+?)[\'"]',  # ES6 imports
            r'require\s*\([\'"](.+?)[\'"]\)',  # CommonJS requires
        ]
        
        # C# using statements and base classes
        if file_path.endswith('.cs'):
            patterns = [
                r'using\s+([\w.]+);',  # Using statements
                r':\s*([\w.]+)',  # Base classes/interfaces
            ]
            import_patterns.extend(patterns)
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dep_path = match.group(1)
                dependencies.append({
                    'path': dep_path,
                    'type': 'imports' if 'import' in pattern or 'using' in pattern else 'extends'
                })
        
        return dependencies

    def analyze_commit(self, repo_path: str, commit_hash: str):
        """Analyze a specific commit"""
        # Get files changed in this commit
        self.cursor.execute('''
            SELECT f.path 
            FROM files f
            JOIN commit_files cf ON cf.file_id = f.id
            JOIN commits c ON c.id = cf.commit_id
            WHERE c.hash = ?
        ''', (commit_hash,))
        
        files = self.cursor.fetchall()
        
        for file_path, in files:
            content = self.get_file_content_at_commit(repo_path, commit_hash, file_path)
            if not content:
                continue
            
            # Analyze functions based on file type
            functions = []
            if file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                functions = self.analyze_typescript_functions(content)
            elif file_path.endswith('.cs'):
                functions = self.analyze_csharp_functions(content)
            
            # Store function changes
            for func in functions:
                self.cursor.execute('''
                    INSERT INTO function_changes 
                    (commit_hash, file_path, function_name, change_type, new_signature, change_description)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    commit_hash,
                    file_path,
                    func['name'],
                    'modified',  # We'll need to compare with previous version to determine if added/modified/removed
                    func['signature'],
                    f"Parameters: {func['parameters']}"
                ))
            
            # Analyze dependencies
            dependencies = self.find_dependencies(content, file_path)
            for dep in dependencies:
                self.cursor.execute('''
                    INSERT INTO file_dependencies
                    (source_file, target_file, dependency_type, first_seen_commit, last_seen_commit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    file_path,
                    dep['path'],
                    dep['type'],
                    commit_hash,
                    commit_hash
                ))
        
        self.conn.commit()

    def analyze_all_commits(self):
        """Analyze all commits in the database"""
        self.cursor.execute('''
            SELECT c.hash, r.name as repository 
            FROM commits c
            JOIN repositories r ON r.id = c.repository_id
            ORDER BY c.commit_date
        ''')
        commits = self.cursor.fetchall()
        
        for commit_hash, repository in commits:
            repo_path = f'/Users/franckjones/sgives/{repository}'
            print(f"Analyzing commit {commit_hash} in {repository}...")
            self.analyze_commit(repo_path, commit_hash)

if __name__ == '__main__':
    analyzer = FunctionAnalyzer('commits_2025.db')
    analyzer.analyze_all_commits()
