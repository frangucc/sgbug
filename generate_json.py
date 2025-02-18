import sqlite3
import json

def get_repo_summary(cursor):
    cursor.execute('''
        SELECT 
            r.name,
            COUNT(DISTINCT c.id) as commits,
            COUNT(DISTINCT cf.file_id) as files
        FROM repositories r
        LEFT JOIN commits c ON c.repository_id = r.id
        LEFT JOIN commit_files cf ON cf.commit_id = c.id
        GROUP BY r.id
        ORDER BY commits DESC
    ''')
    return [{"name": row[0], "commits": row[1], "files": row[2]} for row in cursor.fetchall()]

def get_commit_details(cursor):
    # First get the basic commit info
    cursor.execute('''
        SELECT 
            r.name as repository,
            c.hash,
            c.author,
            c.commit_date,
            c.message,
            GROUP_CONCAT(f.path, '||') as files,
            cd.title,
            cd.detailed_description,
            cd.technical_impact
        FROM commits c
        JOIN repositories r ON r.id = c.repository_id
        LEFT JOIN commit_files cf ON cf.commit_id = c.id
        LEFT JOIN files f ON f.id = cf.file_id
        LEFT JOIN commit_details cd ON cd.commit_hash = c.hash
        GROUP BY c.id
        ORDER BY c.commit_date DESC
    ''')
    
    commits = []
    for row in cursor.fetchall():
        commit = {
            "repository": row[0],
            "hash": row[1],
            "author": row[2],
            "date": row[3] if row[3] else None,
            "message": row[4],
            "files": row[5].split('||') if row[5] else [],
            "title": row[6] or row[4],  # Use message as title if title is null
            "detailed_description": row[7] or row[4],  # Use message if no description
            "technical_impact": row[8] or 'MINOR'
        }
        commits.append(commit)
    
    # Now get file changes for each commit
    cursor.execute('''
        SELECT 
            fc.commit_hash,
            fc.file_path,
            fc.change_summary,
            fc.tags,
            fc.impact_areas,
            NULL as function_changes
        FROM file_changes fc
    ''')
    
    changes_by_commit = {}
    for row in cursor.fetchall():
        commit_hash = row[0]
        if commit_hash not in changes_by_commit:
            changes_by_commit[commit_hash] = []
            
        change = {
            'file_path': row[1],
            'change_summary': row[2],
            'tags': json.loads(row[3] or '[]'),
            'impact_areas': json.loads(row[4] or '[]'),
            'function_changes': []
        }
        
        if row[5]:  # Process function changes
            for fc in row[5].split(','):
                if not fc: continue
                try:
                    parts = fc.split('::')
                    if len(parts) >= 2:
                        fname, ftype = parts[0], parts[1]
                        fdesc = parts[2] if len(parts) > 2 else ''
                        if fname and ftype:
                            change['function_changes'].append({
                                'name': fname,
                                'type': ftype,
                                'description': fdesc
                            })
                except Exception as e:
                    print(f'Error processing function change: {fc} - {e}')
        
        changes_by_commit[commit_hash].append(change)
    
    # Add file changes to commits
    for commit in commits:
        commit['file_changes'] = changes_by_commit.get(commit['hash'], [])
    
    return commits
    
    commits = []
    for row in cursor.fetchall():
        commit = dict(row)
        
        # Parse files list
        if commit['files']:
            commit['files'] = [f for f in commit['files'].split(',') if f]
        else:
            commit['files'] = []
            
        # Parse file changes
        try:
            changes = json.loads(commit['file_changes'])
            commit['file_changes'] = []
            
            for change in changes:
                if not change['file_path']:
                    continue
                    
                processed_change = {
                    'file_path': change['file_path'],
                    'change_summary': change['change_summary'] or '',
                    'tags': json.loads(change['tags'] or '[]'),
                    'impact_areas': json.loads(change['impact_areas'] or '[]'),
                    'function_changes': []
                }
                
                if change['function_changes']:
                    for fc in change['function_changes'].split(','):
                        if not fc:
                            continue
                        fname, ftype, fdesc = fc.split('::', 2)
                        if fname and ftype:
                            processed_change['function_changes'].append({
                                'name': fname,
                                'type': ftype,
                                'description': fdesc
                            })
                
                commit['file_changes'].append(processed_change)
        except Exception as e:
            print(f'Error processing file changes for commit {commit["hash"]}: {e}')
            commit['file_changes'] = []
        
        # Set defaults for missing values
        commit['title'] = commit.get('title') or commit['message']
        commit['technical_impact'] = commit.get('technical_impact', 'MINOR')
        commit['detailed_description'] = commit.get('detailed_description') or commit['message']
        
        commits.append(commit)
    
    return commits

def main():
    conn = sqlite3.connect('commits_2025.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get data
    repo_summary = get_repo_summary(cursor)
    commits = get_commit_details(cursor)

    # Create the final data structure
    data = {
        'repoSummary': repo_summary,
        'commits': commits
    }

    # Write to file
    with open('commits_data.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    main()
