#!/usr/bin/env python3
"""
Quick search bioRxiv for digenic papers using a simpler approach.
Searches recent papers and filters by keywords.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

SEARCH_TERMS = ["digenic", "oligogenic", "digenic inheritance", "two-gene"]

def quick_search(server="biorxiv", days_back=365):
    """
    Quick search of recent bioRxiv/medRxiv papers for digenic terms.
    
    Args:
        server: 'biorxiv' or 'medrxiv'
        days_back: Number of days to look back
    """
    print(f"Searching recent {server} papers...")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    matches = []
    cursor = 0
    total_checked = 0
    
    while cursor is not None:
        url = f"https://api.biorxiv.org/details/{server}/{start_str}/{end_str}/{cursor}"
        
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            if "collection" not in data:
                break
            
            for paper in data["collection"]:
                total_checked += 1
                title = paper.get("title", "").lower()
                abstract = paper.get("abstract", "").lower()
                
                for term in SEARCH_TERMS:
                    if term in title or term in abstract:
                        matches.append({
                            "title": paper.get("title"),
                            "authors": paper.get("authors"),
                            "date": paper.get("date"),
                            "doi": paper.get("doi"),
                            "url": f"https://doi.org/{paper.get('doi')}" if paper.get("doi") else "",
                            "abstract": paper.get("abstract", "")[:500] + "..." if paper.get("abstract") else "",
                            "matched_term": term,
                            "server": server,
                            "category": paper.get("category", "")
                        })
                        break  # Don't add same paper twice
            
            # Check if there are more papers
            messages = data.get("messages", [{}])[0]
            total = messages.get("total", 0)
            
            # Increment cursor by 100 for next page
            cursor += 100
            
            # Stop if we've checked all papers
            if cursor >= int(total):
                break
            
            if cursor and cursor % 2000 == 0:
                print(f"  Checked {total_checked} papers, found {len(matches)} matches...")
                
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"  Checked {total_checked} papers, found {len(matches)} matches")
    return matches


def main():
    print("="*60)
    print("Quick bioRxiv/medRxiv Digenic Paper Search")
    print("="*60)
    
    all_matches = []
    
    # Search both servers
    for server in ["biorxiv", "medrxiv"]:
        matches = quick_search(server)
        all_matches.extend(matches)
    
    # Sort by date
    all_matches.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    print(f"\n{'='*60}")
    print(f"Total matches: {len(all_matches)}")
    print(f"{'='*60}\n")
    
    # Display results
    for i, paper in enumerate(all_matches[:10], 1):
        print(f"{i}. {paper['title']}")
        print(f"   Authors: {paper['authors'][:80]}..." if len(paper['authors']) > 80 else f"   Authors: {paper['authors']}")
        print(f"   Date: {paper['date']} | Server: {paper['server']}")
        print(f"   Category: {paper.get('category', 'N/A')}")
        print(f"   Matched: {paper['matched_term']}")
        print(f"   URL: {paper['url']}")
        print()
    
    # Save results
    output_file = "quick_biorxiv_results.json"
    with open(output_file, "w") as f:
        json.dump(all_matches, f, indent=2)
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
