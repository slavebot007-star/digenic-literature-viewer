# bioRxiv Digenic Paper Search Scripts

This directory contains Python scripts to search bioRxiv and medRxiv for preprints related to digenic and oligogenic inheritance.

## Scripts

### 1. `search_biorxiv.py` - Comprehensive Search

The main search script that iterates through bioRxiv/medRxiv papers and filters by digenic/oligogenic keywords.

**Usage:**

```bash
# Search both bioRxiv and medRxiv (default) - last 5 years
python search_biorxiv.py

# Search only bioRxiv
python search_biorxiv.py --server biorxiv

# Search with custom date range (faster)
python search_biorxiv.py --start-date 2024-01-01 --end-date 2024-12-31

# Search with custom terms
python search_biorxiv.py --terms "digenic" "triallelic" "dual-gene"

# Display results to console
python search_biorxiv.py --display

# Limit papers checked (for testing)
python search_biorxiv.py --max-papers 10000
```

**Options:**
- `--server`: Choose "biorxiv", "medrxiv", or "both" (default: both)
- `--start-date`: Start date in YYYY-MM-DD format (default: 5 years ago)
- `--end-date`: End date in YYYY-MM-DD format (default: today)
- `--output`, `-o`: Output JSON file (default: `biorxiv_digenic_papers.json`)
- `--max-papers`: Maximum papers to check (default: 50000)
- `--delay`: Delay between API calls in seconds (default: 0.3)
- `--terms`: Custom search terms (space-separated)
- `--display`: Display results to console

**Default Search Terms:**
- digenic
- oligogenic
- digenic inheritance
- oligogenic inheritance
- two-gene
- multilocus
- multi-locus
- complex inheritance
- biallelic digenic
- triallelic digenic

**Note on Search Time:** The bioRxiv API returns 100 papers per request. Searching the full database (~70,000 papers per year) can take 5-10 minutes. Use `--start-date` to limit the search range for faster results.

### 2. `quick_biorxiv_search.py` - Quick Search

A simpler, faster script for quick searches of recent papers (last 365 days by default).

**Usage:**

```bash
# Quick search of last year
python quick_biorxiv_search.py
```

This will search both servers and display the top 10 results.

### 3. `convert_biorxiv_to_viewer.py` - Format Converter

Converts bioRxiv search results to match the `comprehensive_papers.json` format used by the literature viewer.

**Usage:**

```bash
# Convert to viewer format
python convert_biorxiv_to_viewer.py biorxiv_digenic_papers.json

# Convert and merge with existing comprehensive_papers.json
python convert_biorxiv_to_viewer.py biorxiv_digenic_papers.json --merge comprehensive_papers.json

# Save to custom output file
python convert_biorxiv_to_viewer.py results.json --output converted.json
```

## Typical Workflow

### Quick Test (Recommended First)
```bash
# Search just the last year on bioRxiv only (fastest)
python search_biorxiv.py --server biorxiv --start-date 2024-01-01 --max-papers 20000
```

### Full Search
```bash
# Search everything (may take 10-15 minutes)
python search_biorxiv.py
```

### Convert and Merge
```bash
# Convert to your viewer format and merge
python convert_biorxiv_to_viewer.py biorxiv_digenic_papers.json --merge comprehensive_papers.json
```

## API Notes

- The bioRxiv API is accessed at `https://api.biorxiv.org/details/[server]/[start_date]/[end_date]/[cursor]`
- Returns 100 papers per request
- No authentication required
- Please use reasonable delays between requests (default 0.3s)

## Output Format

The search scripts produce JSON with these fields:

```json
{
  "doi": "10.1101/xxxxxx",
  "title": "Paper Title",
  "authors": "Author1; Author2; Author3",
  "date": "2024-01-15",
  "year": "2024",
  "abstract": "Abstract text...",
  "category": "genetics",
  "server": "biorxiv",
  "url": "https://doi.org/10.1101/xxxxxx",
  "matched_terms": ["digenic", "oligogenic"]
}
```

The converter transforms this to match the `comprehensive_papers.json` format.

## Requirements

- Python 3.7+
- requests library (`pip install requests`)

## Tips for Faster Searches

1. **Limit date range**: Use `--start-date 2023-01-01` to search only recent papers
2. **Limit max papers**: Use `--max-papers 10000` for testing
3. **Search one server**: Use `--server biorxiv` instead of both
4. **Use the quick script**: `quick_biorxiv_search.py` is pre-configured for recent papers only

## Example: Complete Workflow

```bash
# 1. Quick search to test (last year, bioRxiv only)
python search_biorxiv.py --server biorxiv --start-date 2024-01-01 --max-papers 30000 --display

# 2. If results look good, run full search
python search_biorxiv.py

# 3. Convert and merge with your existing database
python convert_biorxiv_to_viewer.py biorxiv_digenic_papers.json --merge comprehensive_papers.json
```
