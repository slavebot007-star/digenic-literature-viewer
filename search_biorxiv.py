#!/usr/bin/env python3
"""
Search bioRxiv for papers related to digenic and oligogenic inheritance.

bioRxiv API documentation: https://api.biorxiv.org/
"""

import requests
import json
import time
import argparse
from datetime import datetime, timedelta

# Search terms for digenic/oligogenic papers
DEFAULT_SEARCH_TERMS = [
    "digenic",
    "oligogenic", 
    "digenic inheritance",
    "oligogenic inheritance",
    "two-gene",
    "multilocus",
    "multi-locus",
    "complex inheritance",
    "biallelic digenic",
    "triallelic digenic"
]


def fetch_papers_by_date_range(server, start_date, end_date, cursor=0):
    """
    Fetch papers from bioRxiv/medRxiv within a date range.
    
    Args:
        server: "biorxiv" or "medrxiv"
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        cursor: Pagination cursor
    
    Returns:
        (papers, total_count, next_cursor)
    """
    url = f"https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/{cursor}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        papers = data.get("collection", [])
        messages = data.get("messages", [{}])[0]
        
        return (
            papers,
            messages.get("count", 0),
            messages.get("cursor", None),
            messages.get("total", 0)
        )
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return [], 0, None, 0


def search_papers(terms=None, server="biorxiv", start_date=None, end_date=None, 
                  max_papers=10000, delay=0.5):
    """
    Search for papers matching any of the given terms within a date range.
    
    Args:
        terms: List of search terms
        server: "biorxiv" or "medrxiv"
        start_date: Start date (default: 2 years ago)
        end_date: End date (default: today)
        max_papers: Maximum papers to check
        delay: Delay between API calls
    
    Returns:
        List of matching papers
    """
    if terms is None:
        terms = DEFAULT_SEARCH_TERMS
    
    # Set default date range (last 5 years)
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    
    print(f"Searching {server} from {start_date} to {end_date}")
    print(f"Search terms: {', '.join(terms)}")
    print()
    
    all_matches = {}
    cursor = 0
    total_checked = 0
    
    while cursor is not None and total_checked < max_papers:
        papers, count, next_cursor, total_available = fetch_papers_by_date_range(
            server, start_date, end_date, cursor
        )
        
        if not papers:
            break
        
        for paper in papers:
            total_checked += 1
            
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            
            for term in terms:
                term_lower = term.lower()
                if term_lower in title or term_lower in abstract:
                    doi = paper.get("doi", "")
                    if doi not in all_matches:
                        all_matches[doi] = {
                            "doi": doi,
                            "title": paper.get("title", ""),
                            "authors": paper.get("authors", ""),
                            "author_corresponding": paper.get("author_corresponding", ""),
                            "author_corresponding_institution": paper.get("author_corresponding_institution", ""),
                            "date": paper.get("date", ""),
                            "year": paper.get("date", "")[:4] if paper.get("date") else "",
                            "version": paper.get("version", ""),
                            "type": paper.get("type", ""),
                            "license": paper.get("license", ""),
                            "category": paper.get("category", ""),
                            "abstract": paper.get("abstract", ""),
                            "published": paper.get("published", ""),
                            "server": server,
                            "url": f"https://doi.org/{doi}" if doi else "",
                            "matched_terms": [term]
                        }
                    else:
                        if term not in all_matches[doi]["matched_terms"]:
                            all_matches[doi]["matched_terms"].append(term)
                    break
        
        print(f"  Checked {total_checked} papers, found {len(all_matches)} matches...", end="\r")
        
        # Check if we should continue
        cursor += 100
        
        if total_available and cursor >= int(total_available):
            break
        if count == 0:
            break
        if total_checked >= max_papers:
            break
        time.sleep(delay)
    
    print()  # New line after progress
    return list(all_matches.values())


def save_papers(papers, output_file):
    """Save papers to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(papers)} papers to {output_file}")


def format_paper_for_display(paper):
    """Format a paper for console display."""
    lines = [
        f"Title: {paper['title']}",
        f"Authors: {paper['authors'][:100]}..." if len(paper['authors']) > 100 else f"Authors: {paper['authors']}",
        f"Date: {paper['date']}",
        f"DOI: {paper['doi']}",
        f"URL: {paper['url']}",
        f"Matched terms: {', '.join(paper.get('matched_terms', []))}",
        "-" * 80
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search bioRxiv/medRxiv for papers on digenic and oligogenic inheritance"
    )
    parser.add_argument(
        "--server", 
        choices=["biorxiv", "medrxiv", "both"],
        default="both",
        help="Which preprint server to search (default: both)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date (YYYY-MM-DD, default: 5 years ago)"
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--output", 
        "-o",
        default="biorxiv_digenic_papers.json",
        help="Output JSON file (default: biorxiv_digenic_papers.json)"
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=50000,
        help="Maximum papers to check (default: 50000)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between API calls in seconds (default: 0.3)"
    )
    parser.add_argument(
        "--terms",
        nargs="+",
        help="Custom search terms (space-separated)"
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Display results to console"
    )
    
    args = parser.parse_args()
    
    terms = args.terms if args.terms else DEFAULT_SEARCH_TERMS
    
    all_papers = []
    
    if args.server in ("biorxiv", "both"):
        papers = search_papers(
            terms=terms,
            server="biorxiv",
            start_date=args.start_date,
            end_date=args.end_date,
            max_papers=args.max_papers,
            delay=args.delay
        )
        all_papers.extend(papers)
    
    if args.server in ("medrxiv", "both"):
        papers = search_papers(
            terms=terms,
            server="medrxiv", 
            start_date=args.start_date,
            end_date=args.end_date,
            max_papers=args.max_papers,
            delay=args.delay
        )
        all_papers.extend(papers)
    
    # Remove duplicates (papers might appear in both servers)
    seen_dois = set()
    unique_papers = []
    for paper in all_papers:
        doi = paper['doi']
        if doi not in seen_dois:
            seen_dois.add(doi)
            unique_papers.append(paper)
    
    # Sort by date (newest first)
    unique_papers.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    print(f"\n{'='*80}")
    print(f"Found {len(unique_papers)} unique papers")
    print(f"{'='*80}\n")
    
    if args.display:
        for paper in unique_papers[:20]:  # Show first 20
            print(format_paper_for_display(paper))
            print()
    
    save_papers(unique_papers, args.output)
    
    # Print summary
    if unique_papers:
        years = [p.get('year') for p in unique_papers if p.get('year')]
        if years:
            print(f"\nYear range: {min(years)} - {max(years)}")
        
        servers = {}
        for p in unique_papers:
            srv = p.get('server', 'unknown')
            servers[srv] = servers.get(srv, 0) + 1
        print("Papers by server:")
        for srv, count in servers.items():
            print(f"  {srv}: {count}")


if __name__ == "__main__":
    main()
