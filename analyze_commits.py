import sqlite3
import subprocess
import json
from datetime import datetime

def get_commit_details(repo_path, commit_hash):
    """Get detailed information about a commit"""
    try:
        # Get the full commit message and diff
        result = subprocess.run(
            ['git', 'show', '--pretty=format:%B%n%n%H%n%an%n%ad%n---DIFF---%n', '--patch', commit_hash],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return None
            
        parts = result.stdout.split('---DIFF---')
        message = parts[0].strip().split('\n')
        diff = parts[1] if len(parts) > 1 else ''
        
        # Parse the basic info
        commit_info = {
            'hash': message[-4],
            'author': message[-3],
            'date': message[-2],
            'message': '\n'.join(message[:-4]).strip(),
            'diff': diff.strip(),
            'changes': []
        }
        
        # Analyze the diff to get file-specific changes
        current_file = None
        current_changes = []
        
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                if current_file:
                    commit_info['changes'].append({
                        'file': current_file,
                        'changes': current_changes
                    })
                current_file = line.split(' b/')[-1]
                current_changes = []
            elif line.startswith('+') and not line.startswith('+++'):
                current_changes.append(('add', line[1:].strip()))
            elif line.startswith('-') and not line.startswith('---'):
                current_changes.append(('remove', line[1:].strip()))
                
        if current_file:
            commit_info['changes'].append({
                'file': current_file,
                'changes': current_changes
            })
            
        return commit_info
    except Exception as e:
        print(f"Error processing commit {commit_hash}: {str(e)}")
        return None

def analyze_all_commits():
    """Analyze all commits from our database"""
    conn = sqlite3.connect('commits_2025.db')
    cursor = conn.cursor()
    
    # Get all commits
    cursor.execute('''
        SELECT DISTINCT c.hash, c.message, r.name 
        FROM commits c
        JOIN repositories r ON r.id = c.repository_id
        ORDER BY c.commit_date DESC
    ''')
    
    commits = cursor.fetchall()
    detailed_analysis = []
    
    for commit_hash, message, repo_name in commits:
        repo_path = f'/Users/franckjones/sgives/{repo_name}'
        details = get_commit_details(repo_path, commit_hash)
        if details:
            analysis = {
                'repository': repo_name,
                'commit_hash': commit_hash,
                'original_message': message,
                'detailed_description': [],
                'technical_changes': []
            }
            
            # Analyze each file's changes
            for file_change in details['changes']:
                file_analysis = {
                    'file': file_change['file'],
                    'summary': '',
                    'additions': [],
                    'removals': [],
                    'impact': 'minor'  # Can be minor, moderate, major
                }
                
                # Count significant changes
                significant_changes = 0
                for change_type, content in file_change['changes']:
                    if change_type == 'add':
                        if len(content.strip()) > 0:
                            file_analysis['additions'].append(content)
                            if not content.startswith(('import ', '//', '#', '/*')):
                                significant_changes += 1
                    else:
                        if len(content.strip()) > 0:
                            file_analysis['removals'].append(content)
                            if not content.startswith(('import ', '//', '#', '/*')):
                                significant_changes += 1
                
                # Determine impact
                if significant_changes > 20:
                    file_analysis['impact'] = 'major'
                elif significant_changes > 5:
                    file_analysis['impact'] = 'moderate'
                
                analysis['technical_changes'].append(file_analysis)
            
            detailed_analysis.append(analysis)
    
    # Write to file
    with open('detailed_commit_analysis.txt', 'w') as f:
        json.dump(detailed_analysis, f, indent=2)
    
    conn.close()
    return detailed_analysis

if __name__ == '__main__':
    analyze_all_commits()
