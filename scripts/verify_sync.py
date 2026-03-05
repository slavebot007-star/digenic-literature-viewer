#!/usr/bin/env python3
"""
Verify workspace and GitHub repo are in sync for digenic literature viewer.
Run this before pushing to GitHub to prevent sync bugs.
"""

import json
import sys
from pathlib import Path

def load_json(path):
    """Load JSON file, return None if missing/invalid."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, str(e)
    return json.load(open(path)), None

def main():
    workspace = Path("/root/.openclaw/workspace")
    repo = Path("/tmp/digenic-literature-viewer")
    
    errors = []
    warnings = []
    
    # Check workspace files exist
    ws_json = workspace / "comprehensive_papers.json"
    ws_html = workspace / "literature-viewer.html"
    
    if not ws_json.exists():
        errors.append(f"❌ Workspace JSON missing: {ws_json}")
    if not ws_html.exists():
        errors.append(f"❌ Workspace HTML missing: {ws_html}")
    
    # Check repo files exist (in docs/ subdirectory for GitHub Pages)
    repo_json = repo / "docs" / "comprehensive_papers.json"
    repo_html = repo / "docs" / "index.html"
    
    if not repo_json.exists():
        errors.append(f"❌ Repo JSON missing: {repo_json}")
    if not repo_html.exists():
        errors.append(f"❌ Repo HTML missing: {repo_html}")
    
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    
    # Load and compare JSON
    try:
        with open(ws_json) as f:
            ws_data = json.load(f)
        with open(repo_json) as f:
            repo_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        sys.exit(1)
    
    # Validate structure
    if isinstance(ws_data, list):
        errors.append("❌ Workspace JSON is a list (should be dict with 'metadata' and 'papers')")
    elif not isinstance(ws_data, dict) or "papers" not in ws_data:
        errors.append("❌ Workspace JSON missing 'papers' key")
    
    if isinstance(repo_data, list):
        errors.append("❌ Repo JSON is a list (should be dict with 'metadata' and 'papers')")
    elif not isinstance(repo_data, dict) or "papers" not in repo_data:
        errors.append("❌ Repo JSON missing 'papers' key")
    
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    
    # Compare counts
    ws_papers = len(ws_data["papers"])
    repo_papers = len(repo_data["papers"])
    
    ws_cats = ws_data.get("metadata", {}).get("categories", {})
    repo_cats = repo_data.get("metadata", {}).get("categories", {})
    
    print(f"📊 Workspace: {ws_papers} papers")
    print(f"📁 Repo:      {repo_papers} papers")
    print()
    
    if ws_papers != repo_papers:
        errors.append(f"❌ Paper count mismatch: workspace={ws_papers}, repo={repo_papers}")
    
    if ws_cats != repo_cats:
        errors.append(f"❌ Category mismatch:")
        errors.append(f"   Workspace: {ws_cats}")
        errors.append(f"   Repo:      {repo_cats}")
    
    # Check last_updated
    ws_updated = ws_data.get("metadata", {}).get("last_updated", "unknown")
    repo_updated = repo_data.get("metadata", {}).get("last_updated", "unknown")
    
    if ws_updated != repo_updated:
        warnings.append(f"⚠️  last_updated differs (may be OK if only metadata changed)")
        warnings.append(f"   Workspace: {ws_updated}")
        warnings.append(f"   Repo:      {repo_updated}")
    
    # Check HTML has embedded data
    with open(ws_html) as f:
        ws_html_content = f.read()
    with open(repo_html) as f:
        repo_html_content = f.read()
    
    if "const PAPERS_DATA" not in ws_html_content:
        errors.append("❌ Workspace HTML missing PAPERS_DATA")
    if "const PAPERS_DATA" not in repo_html_content:
        errors.append("❌ Repo HTML missing PAPERS_DATA")
    
    # Compare HTML data counts (rough check)
    ws_pmid_count = ws_html_content.count('"PMID"')
    repo_pmid_count = repo_html_content.count('"PMID"')
    
    if ws_pmid_count != repo_pmid_count:
        errors.append(f"❌ HTML PMID count mismatch: workspace={ws_pmid_count}, repo={repo_pmid_count}")
    
    # Report results
    if warnings:
        print("\n".join(warnings))
        print()
    
    if errors:
        print("\n".join(errors))
        print("\n🔧 To fix: cp comprehensive_papers.json /tmp/digenic-literature-viewer/docs/")
        print("           cp literature-viewer.html /tmp/digenic-literature-viewer/docs/index.html")
        sys.exit(1)
    
    print("✅ Workspace and repo are in sync!")
    print(f"   Total papers: {ws_papers}")
    print(f"   Categories: {ws_cats}")
    print(f"   Last updated: {ws_updated}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
