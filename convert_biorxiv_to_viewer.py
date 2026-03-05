#!/usr/bin/env python3
"""
Convert bioRxiv search results to match the comprehensive_papers.json format.
This allows easy integration with the existing literature viewer.
"""

import json
import argparse
from datetime import datetime


def convert_paper(biorxiv_paper):
    """
    Convert a bioRxiv paper to the comprehensive_papers.json format.
    """
    # Parse authors - bioRxiv uses ";" separator
    authors_str = biorxiv_paper.get("authors", "")
    
    # Get year from date (format: YYYY-MM-DD)
    date = biorxiv_paper.get("date", "")
    year = date[:4] if date and len(date) >= 4 else ""
    
    # Determine category based on content
    title_abs = (biorxiv_paper.get("title", "") + " " + 
                 biorxiv_paper.get("abstract", "")).lower()
    
    if any(x in title_abs for x in ["patient", "clinical", "disease", "syndrome", "disorder"]):
        category = "clinical"
    elif any(x in title_abs for x in ["mouse", "zebrafish", "model", "animal"]):
        category = "model"
    else:
        category = "mechanism"
    
    # Determine inheritance pattern
    inheritance = "digenic"
    if "oligogenic" in title_abs:
        inheritance = "oligogenic"
    elif "triallelic" in title_abs:
        inheritance = "triallelic"
    
    # Create the converted paper matching comprehensive_papers.json format
    converted = {
        "PMID": None,  # bioRxiv preprints don't have PMIDs
        "title": biorxiv_paper.get("title", ""),
        "authors": authors_str,
        "journal": f"bioRxiv [{biorxiv_paper.get('category', 'preprint')}]",
        "year": year,
        "doi": biorxiv_paper.get("doi", ""),
        "abstract": biorxiv_paper.get("abstract", ""),
        "mesh_terms": [inheritance, biorxiv_paper.get("server", "biorxiv")] + biorxiv_paper.get("matched_terms", []),
        "source": f"{biorxiv_paper.get('server', 'biorxiv')}_api",
        "category": category,
        "is_preprint": True,
        "preprint_server": biorxiv_paper.get("server", "bioRxiv"),
        "date": date,
        "version": biorxiv_paper.get("version", ""),
        "category_biorxiv": biorxiv_paper.get("category", "")
    }
    
    return converted


def main():
    parser = argparse.ArgumentParser(
        description="Convert bioRxiv search results to comprehensive_papers.json format"
    )
    parser.add_argument(
        "input", 
        help="Input JSON file from bioRxiv search"
    )
    parser.add_argument(
        "--output", 
        "-o",
        default="biorxiv_papers_converted.json",
        help="Output file (default: biorxiv_papers_converted.json)"
    )
    parser.add_argument(
        "--merge",
        "-m",
        help="Merge with existing comprehensive_papers.json file"
    )
    
    args = parser.parse_args()
    
    # Load bioRxiv results
    with open(args.input, 'r') as f:
        biorxiv_papers = json.load(f)
    
    print(f"Converting {len(biorxiv_papers)} bioRxiv papers...")
    
    # Convert papers
    converted = [convert_paper(p) for p in biorxiv_papers]
    
    # Remove duplicates by DOI
    seen = set()
    unique = []
    for p in converted:
        doi = p.get("doi", "")
        if doi and doi not in seen:
            seen.add(doi)
            unique.append(p)
    
    print(f"Converted {len(unique)} unique papers")
    
    # Print sample
    if unique:
        print("\nSample entry:")
        print(json.dumps(unique[0], indent=2))
    
    # Merge with existing if requested
    if args.merge:
        with open(args.merge, 'r') as f:
            existing = json.load(f)
        
        # Add only new papers (not already in existing by DOI)
        existing_dois = {p.get("doi", "") for p in existing}
        new_papers = [p for p in unique if p.get("doi", "") not in existing_dois]
        
        merged = existing + new_papers
        
        print(f"\nAdded {len(new_papers)} new papers to existing {len(existing)} papers")
        print(f"Total: {len(merged)} papers")
        
        with open(args.merge, 'w') as f:
            json.dump(merged, f, indent=2)
        print(f"Saved merged results to {args.merge}")
    else:
        with open(args.output, 'w') as f:
            json.dump(unique, f, indent=2)
        print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
