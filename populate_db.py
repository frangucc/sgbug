import sqlite3
import re
from datetime import datetime

def parse_date(date_str):
    # Try different date formats
    formats = [
        "%a %b %d %H:%M:%S %Y %z",
        "%a %b %d %H:%M:%S %Y %Z"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def parse_files(content):
    commits = []
    current_commit = None
    current_files = []
    
    lines = content.split('\n')
    for line in lines:
        if line.startswith('=== '):
            if current_commit and current_files:
                commits.append((current_commit, current_files))
            current_repo = line.strip('= ').strip()
            continue
            
        if re.match(r'^[a-f0-9]{7,40}\s+-\s+', line):
            if current_commit and current_files:
                commits.append((current_commit, current_files))
            parts = line.split(' : ', 1)
            if len(parts) == 2:
                commit_info, message = parts
                commit_parts = commit_info.split(', ', 1)
                if len(commit_parts) == 2:
                    hash_author, date = commit_parts
                    hash_author_parts = hash_author.split(' - ')
                    if len(hash_author_parts) == 2:
                        commit_hash = hash_author_parts[0].strip()
                        author = hash_author_parts[1].strip()
                        current_commit = {
                            'hash': commit_hash,
                            'author': author,
                            'date': date.strip(),
                            'message': message.strip(),
                            'repository': current_repo
                        }
                        current_files = []
        elif line.strip() and not line.startswith('commit ') and not line.startswith('Author:') and not line.startswith('Date:'):
            if line.strip() and current_commit:
                current_files.append(line.strip())
    
    if current_commit and current_files:
        commits.append((current_commit, current_files))
    
    return commits

def main():
    conn = sqlite3.connect('commits_2025.db')
    cursor = conn.cursor()
    
    # Read the files
    with open('files_summary_2025.txt', 'r') as f:
        content = f.read()
    
    commits_data = parse_files(content)
    
    # Get repository IDs
    cursor.execute('SELECT id, name FROM repositories')
    repo_ids = {name: id for id, name in cursor.fetchall()}
    
    # Insert commits and files
    for commit_info, files in commits_data:
        # Insert commit
        cursor.execute('''
            INSERT INTO commits (hash, author, commit_date, message, repository_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            commit_info['hash'],
            commit_info['author'],
            parse_date(commit_info['date']).isoformat(),
            commit_info['message'],
            repo_ids[commit_info['repository']]
        ))
        commit_id = cursor.lastrowid
        
        # Insert files and create relationships
        for file_path in files:
            cursor.execute('INSERT OR IGNORE INTO files (path, repository_id) VALUES (?, ?)',
                         (file_path, repo_ids[commit_info['repository']]))
            cursor.execute('SELECT id FROM files WHERE path = ? AND repository_id = ?',
                         (file_path, repo_ids[commit_info['repository']]))
            file_id = cursor.fetchone()[0]
            
            cursor.execute('INSERT INTO commit_files (commit_id, file_id) VALUES (?, ?)',
                         (commit_id, file_id))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
