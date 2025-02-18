import sqlite3
import json

def get_repo_summary(cursor):
    cursor.execute('''
        SELECT r.name, COUNT(DISTINCT c.id) as commits, COUNT(DISTINCT f.id) as files
        FROM repositories r
        LEFT JOIN commits c ON c.repository_id = r.id
        LEFT JOIN commit_files cf ON cf.commit_id = c.id
        LEFT JOIN files f ON f.id = cf.file_id
        GROUP BY r.name
    ''')
    return [{"name": row[0], "commits": row[1], "files": row[2]} for row in cursor.fetchall()]

def get_commit_details(cursor):
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
        files = row[5].split('||') if row[5] else []
        commits.append({
            "repository": row[0],
            "hash": row[1],
            "author": row[2],
            "date": row[3],
            "message": row[4],
            "files": files,
            "title": row[6],
            "detailed_description": row[7],
            "technical_impact": row[8]
        })
    return commits

def get_file_timeline(cursor):
    cursor.execute('''
        WITH CommitFiles AS (
            SELECT 
                c.id as commit_id,
                COUNT(DISTINCT f.id) as file_count
            FROM commits c
            JOIN commit_files cf ON cf.commit_id = c.id
            JOIN files f ON f.id = cf.file_id
            GROUP BY c.id
        )
        SELECT 
            c.hash,
            c.commit_date,
            c.message,
            c.author,
            cd.title,
            cd.detailed_description,
            cd.technical_impact,
            r.name as repository,
            GROUP_CONCAT(f.path) as paths,
            cf.file_count
        FROM commits c
        JOIN repositories r ON r.id = c.repository_id
        JOIN commit_files cfs ON cfs.commit_id = c.id
        JOIN files f ON f.id = cfs.file_id
        LEFT JOIN commit_details cd ON cd.commit_hash = c.hash
        JOIN CommitFiles cf ON cf.commit_id = c.id
        GROUP BY c.id, r.name
        ORDER BY c.commit_date DESC
    ''')
    
    timeline = []
    for row in cursor.fetchall():
        paths = row[8].split(',') if row[8] else []
        timeline.append({
            "hash": row[0],
            "date": row[1],
            "message": row[2],
            "author": row[3],
            "title": row[4] or row[2],  # Use message as title if title is null
            "description": row[5] or "No detailed description available.",
            "impact": row[6] or "MINOR",
            "repository": row[7],
            "files": paths,
            "file_count": row[9]
        })
    return timeline
    
    timeline = []
    for row in cursor.fetchall():
        commits = json.loads(row[2])
        timeline.append({
            "path": row[0],
            "repository": row[1],
            "commits": sorted(commits, key=lambda x: x['date'])
        })
    return timeline

def get_file_changes(cursor):
    cursor.execute('''
        SELECT commit_hash, file_path, change_summary, tags, impact_areas
        FROM file_changes
    ''')
    return [{
        'commit_hash': row[0],
        'file_path': row[1],
        'change_summary': row[2],
        'tags': row[3],
        'impact_areas': row[4]
    } for row in cursor.fetchall()]

def main():
    conn = sqlite3.connect('commits_2025.db')
    cursor = conn.cursor()
    
    data = {
        "repoSummary": get_repo_summary(cursor),
        "commits": get_commit_details(cursor),
        "fileTimeline": get_file_timeline(cursor),
        "fileChanges": get_file_changes(cursor)
    }
    
    with open('commits_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    conn.close()

if __name__ == '__main__':
    main()
