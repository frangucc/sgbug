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
    # First get all commits
    cursor.execute('''
        SELECT 
            r.name as repository,
            c.hash,
            c.author,
            c.commit_date,
            c.message,
            GROUP_CONCAT(DISTINCT f.path) as files,
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
        files = list(set(row[5].split(',') if row[5] else []))
        commit_hash = row[1]
        
        # Get file changes for this commit
        cursor.execute('''
            SELECT file_path, change_summary, tags, impact_areas
            FROM file_changes
            WHERE commit_hash = ?
        ''', (commit_hash,))
        
        file_changes = []
        for fc in cursor.fetchall():
            try:
                tags = json.loads(fc[2] or '[]')
                impact_areas = json.loads(fc[3] or '[]')
            except:
                tags = []
                impact_areas = []
                
            file_changes.append({
                'file_path': fc[0],
                'change_summary': fc[1] or '',
                'tags': tags,
                'impact_areas': impact_areas
            })
            
        commits.append({
            "repository": row[0],
            "hash": row[1],
            "author": row[2],
            "date": row[3],
            "message": row[4],
            "files": files,
            "title": row[6] or row[4],  # Use message as fallback
            "detailed_description": row[7] or row[4],  # Use message as fallback
            "technical_impact": row[8] or 'MINOR',
            "file_changes": file_changes
        })
    return commits

def get_file_timeline(cursor):
    cursor.execute('''
        WITH CommitFiles AS (
            SELECT 
                c.id as commit_id,
                COUNT(DISTINCT f.id) as file_count,
                GROUP_CONCAT(f.path) as paths
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
            cf.paths,
            cf.file_count,
            fc.tags,
            fc.impact_areas,
            fc.change_summary
        FROM commits c
        JOIN repositories r ON r.id = c.repository_id
        LEFT JOIN commit_details cd ON cd.commit_hash = c.hash
        LEFT JOIN file_changes fc ON fc.commit_hash = c.hash
        JOIN CommitFiles cf ON cf.commit_id = c.id
        ORDER BY c.commit_date DESC
    ''')
    
    timeline = []
    for row in cursor.fetchall():
        try:
            tags = json.loads(row[11] or '[]')
            impact_areas = json.loads(row[12] or '[]')
        except:
            tags = []
            impact_areas = []
            
        paths = row[8].split('||') if row[8] else []
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
            "file_count": row[9],
            "tags": tags,
            "impact_areas": impact_areas,
            "change_summary": row[12] or ''
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
