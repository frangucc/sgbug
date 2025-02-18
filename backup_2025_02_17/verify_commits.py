import sqlite3
import subprocess
import json
from datetime import datetime
import os

class CommitVerifier:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.base_path = '/Users/franckjones/sgives'

    def get_commit_details(self, repo_path, commit_hash):
        """Get detailed git show output for a commit"""
        try:
            result = subprocess.run(
                ['git', 'show', commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            print(f"Error getting commit details: {str(e)}")
            return ""

    def analyze_diff(self, diff_content):
        """Analyze the diff content to understand the changes"""
        analysis = {
            'files_changed': [],
            'additions': [],
            'deletions': [],
            'function_changes': [],
            'property_changes': [],
            'summary': []
        }
        
        current_file = None
        in_diff = False
        
        for line in diff_content.split('\n'):
            if line.startswith('diff --git'):
                current_file = line.split(' b/')[-1]
                analysis['files_changed'].append(current_file)
                in_diff = True
            elif in_diff:
                if line.startswith('+') and not line.startswith('+++'):
                    analysis['additions'].append(line[1:].strip())
                elif line.startswith('-') and not line.startswith('---'):
                    analysis['deletions'].append(line[1:].strip())
                
                # Detect function changes
                if 'public' in line or 'private' in line or 'protected' in line:
                    if 'class' not in line and '(' in line:
                        analysis['function_changes'].append(line.strip())
                
                # Detect property changes
                if 'get;' in line or 'set;' in line:
                    analysis['property_changes'].append(line.strip())
        
        # Generate summary
        if analysis['function_changes']:
            analysis['summary'].append(f"Modified {len(analysis['function_changes'])} functions")
        if analysis['property_changes']:
            analysis['summary'].append(f"Changed {len(analysis['property_changes'])} properties")
        if len(analysis['additions']) > len(analysis['deletions']):
            analysis['summary'].append("More additions than deletions - likely new feature or enhancement")
        elif len(analysis['deletions']) > len(analysis['additions']):
            analysis['summary'].append("More deletions than additions - likely cleanup or simplification")
        
        return analysis

    def verify_commit(self, commit_hash, repository):
        """Verify a single commit against our stored analysis"""
        print(f"\n{'='*80}")
        print(f"Verifying commit {commit_hash} in {repository}")
        print(f"{'='*80}")
        
        # Get our stored analysis
        self.cursor.execute('''
            SELECT fc.file_path, fc.change_summary, fc.tags, fc.impact_areas
            FROM file_changes fc
            WHERE fc.commit_hash = ?
        ''', (commit_hash,))
        stored_changes = self.cursor.fetchall()
        
        # Get actual commit changes
        repo_path = os.path.join(self.base_path, repository)
        commit_content = self.get_commit_details(repo_path, commit_hash)
        actual_analysis = self.analyze_diff(commit_content)
        
        print("\nActual Changes:")
        print(f"Files Changed: {len(actual_analysis['files_changed'])}")
        for file in actual_analysis['files_changed']:
            print(f"  - {file}")
        print("\nSummary:")
        for item in actual_analysis['summary']:
            print(f"  - {item}")
        
        print("\nStored Analysis:")
        for file_path, summary, tags, impact_areas in stored_changes:
            print(f"\nFile: {file_path}")
            print("Summary:")
            for line in summary.split('\n'):
                print(f"  {line}")
            print("Tags:", json.loads(tags))
            print("Impact Areas:", json.loads(impact_areas))
        
        print("\nVerification Results:")
        # Check for mismatches
        stored_files = set(change[0] for change in stored_changes)
        actual_files = set(actual_analysis['files_changed'])
        
        if stored_files != actual_files:
            print("❌ File mismatch!")
            print("Missing in stored:", actual_files - stored_files)
            print("Extra in stored:", stored_files - actual_files)
        else:
            print("✅ File list matches")
        
        return {
            'commit_hash': commit_hash,
            'repository': repository,
            'stored_analysis': stored_changes,
            'actual_analysis': actual_analysis,
            'verification_passed': stored_files == actual_files
        }

    def verify_all_commits(self):
        """Verify all commits in our database"""
        self.cursor.execute('''
            SELECT DISTINCT c.hash, r.name as repository
            FROM commits c
            JOIN repositories r ON r.id = c.repository_id
            ORDER BY c.commit_date DESC
        ''')
        
        results = []
        for commit_hash, repository in self.cursor.fetchall():
            result = self.verify_commit(commit_hash, repository)
            results.append(result)
            
            # Ask for user input
            action = input("\nPress Enter to continue to next commit, 'u' to update analysis, or 'q' to quit: ")
            if action.lower() == 'q':
                break
            elif action.lower() == 'u':
                print("Please provide the updated analysis:")
                summary = input("New summary: ")
                tags = input("New tags (comma-separated): ")
                impact_areas = input("New impact areas (comma-separated): ")
                
                # Update the database
                self.cursor.execute('''
                    UPDATE file_changes
                    SET change_summary = ?,
                        tags = ?,
                        impact_areas = ?
                    WHERE commit_hash = ?
                ''', (
                    summary,
                    json.dumps(tags.split(',')),
                    json.dumps(impact_areas.split(',')),
                    commit_hash
                ))
                self.conn.commit()
        
        return results

if __name__ == '__main__':
    verifier = CommitVerifier('commits_2025.db')
    verifier.verify_all_commits()
