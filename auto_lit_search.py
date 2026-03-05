#!/usr/bin/env python3
"""
Automated Digenic Literature Search + SVM Classification Pipeline
=================================================================

This script:
1. Searches multiple databases for digenic/oligogenic papers
2. Classifies new papers using the trained SVM model
3. Updates comprehensive_papers.json
4. Regenerates literature-viewer.html
5. Pushes to GitHub

Usage:
    python3 auto_lit_search.py [--dry-run]
"""

import json
import sys
import pickle
import math
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Union, Optional, Set
from datetime import datetime
import subprocess
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

# Paths
WORKSPACE_DIR = Path("/root/.openclaw/workspace")
CLASSIFIER_DIR = Path("/root/.openclaw/media/inbound/paper_classifier")
PAPERS_JSON = WORKSPACE_DIR / "comprehensive_papers.json"
HTML_FILE = WORKSPACE_DIR / "literature-viewer.html"
VERIFY_SCRIPT = WORKSPACE_DIR / "scripts" / "verify_sync.py"

# Model files
MODEL_PATH = CLASSIFIER_DIR / "svm_model.pkl"
VECTORIZER_PATH = CLASSIFIER_DIR / "tfidf_vectorizer.pkl"

# GitHub repo
GITHUB_REPO = "/tmp/digenic-literature-viewer"


class SVMClassifier:
    """SVM-based paper classifier."""
    
    CATEGORY_MAP = {
        "Tool/Method": "tools",
        "Clinical/Biological": "clinical",
        "Review": "review"
    }
    
    def __init__(self):
        self.model = None
        self.categories = None
        self._load_model()
    
    def _load_model(self):
        with open(MODEL_PATH, 'rb') as f:
            self.model = pickle.load(f)
        with open(VECTORIZER_PATH, 'rb') as f:
            _ = pickle.load(f)  # Vectorizer is part of pipeline
        
        if hasattr(self.model, 'classes_'):
            self.categories = list(self.model.classes_)
        else:
            self.categories = ["Tool/Method", "Clinical/Biological", "Review"]
    
    def predict(self, text: str) -> Dict[str, Union[str, float]]:
        if not text or len(text.strip()) < 10:
            return {'ml_category': 'clinical', 'ml_confidence': 0.5}
        
        prediction = self.model.predict([text])[0]
        confidence = self._get_confidence([text], prediction)
        
        ml_category = self.CATEGORY_MAP.get(prediction, prediction.lower())
        return {'ml_category': ml_category, 'ml_confidence': confidence}
    
    def _get_confidence(self, text, prediction) -> float:
        if hasattr(self.model, 'predict_proba'):
            try:
                proba = self.model.predict_proba(text)[0]
                pred_idx = list(self.model.classes_).index(prediction)
                return float(proba[pred_idx])
            except:
                pass
        
        if hasattr(self.model, 'decision_function'):
            try:
                decision = self.model.decision_function(text)[0]
                if hasattr(decision, '__iter__'):
                    max_decision = max(decision)
                    confidence = 1 / (1 + math.exp(-max_decision))
                    return float(confidence)
                else:
                    confidence = 1 / (1 + math.exp(-abs(decision)))
                    return float(confidence)
            except:
                pass
        
        return 0.5


class LiteratureSearch:
    """Multi-database literature search."""
    
    def __init__(self):
        self.results = []
        self.seen_dois: Set[str] = set()
        self.seen_pmids: Set[str] = set()
    
    def search_pubmed(self, query: str, limit: int = 200) -> List[Dict]:
        """Search PubMed with detailed parsing."""
        papers = []
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
                "sort": "date"
            }
            
            search_data = urllib.parse.urlencode(search_params).encode()
            with urllib.request.urlopen(search_url, data=search_data, timeout=30) as response:
                data = json.loads(response.read().decode())
                pmids = data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return papers
            
            print(f"  PubMed: Found {len(pmids)} papers")
            
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
            fetch_data = urllib.parse.urlencode(fetch_params).encode()
            
            with urllib.request.urlopen(fetch_url, data=fetch_data, timeout=60) as response:
                xml_content = response.read()
            
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                if pmid in self.seen_pmids:
                    continue
                
                title_elem = article.find(".//ArticleTitle")
                title = "".join(title_elem.itertext()) if title_elem is not None else ""
                
                abstract_elem = article.find(".//Abstract")
                abstract = ""
                if abstract_elem is not None:
                    abstract_texts = []
                    for abs_text in abstract_elem.findall(".//AbstractText"):
                        text = "".join(abs_text.itertext())
                        abstract_texts.append(text)
                    abstract = " ".join(abstract_texts)
                
                authors = []
                for author in article.findall(".//Author"):
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None:
                        name = lastname.text
                        if forename is not None:
                            name = f"{forename.text} {name}"
                        authors.append(name)
                authors_str = "; ".join(authors[:5])
                if len(authors) > 5:
                    authors_str += f" et al. ({len(authors)} authors)"
                
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""
                
                year = None
                pub_date = article.find(".//PubDate")
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    if year_elem is not None:
                        year = year_elem.text
                
                doi = ""
                for article_id in article.findall(".//ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break
                
                mesh_terms = []
                for mesh in article.findall(".//MeshHeading"):
                    descriptor = mesh.find("DescriptorName")
                    if descriptor is not None:
                        mesh_terms.append(descriptor.text)
                
                paper = {
                    "PMID": pmid,
                    "title": title,
                    "authors": authors_str,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "abstract": abstract,
                    "mesh_terms": mesh_terms,
                    "source": "pubmed"
                }
                
                papers.append(paper)
                self.seen_pmids.add(pmid)
                
        except Exception as e:
            print(f"  PubMed error: {e}")
        
        return papers
    
    def search_europe_pmc(self, query: str, limit: int = 100) -> List[Dict]:
        """Search Europe PMC for preprints."""
        papers = []
        try:
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            params = {
                "query": f"({query}) AND (SRC:PPR)",
                "format": "json",
                "pageSize": limit,
                "resultType": "lite"
            }
            
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
            
            with urllib.request.urlopen(full_url, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("resultList", {}).get("result", [])
                
                print(f"  Europe PMC: Found {len(results)} papers")
                
                for item in results:
                    doi = item.get("doi", "")
                    pmid = item.get("pmid", "")
                    
                    if (doi and doi in self.seen_dois) or (pmid and pmid in self.seen_pmids):
                        continue
                    
                    authors_str = item.get("authorString", "")
                    if len(authors_str) > 100:
                        authors_str = authors_str[:100] + "..."
                    
                    year = None
                    pub_date = item.get("firstPublicationDate", "")
                    if pub_date:
                        year = pub_date.split("-")[0]
                    
                    paper = {
                        'PMID': pmid,
                        'doi': doi,
                        'title': item.get("title", ""),
                        'authors': authors_str,
                        'journal': item.get("journalTitle", "Preprint"),
                        'year': year,
                        'abstract': item.get("abstractText", "")[:500] if item.get("abstractText") else "",
                        'mesh_terms': [],
                        'source': 'europepmc'
                    }
                    
                    papers.append(paper)
                    
                    if doi:
                        self.seen_dois.add(doi)
                    if pmid:
                        self.seen_pmids.add(pmid)
                        
        except Exception as e:
            print(f"  Europe PMC error: {e}")
        
        return papers
    
    def search_openalex(self, query: str, limit: int = 100) -> List[Dict]:
        """Search OpenAlex."""
        papers = []
        try:
            url = "https://api.openalex.org/works"
            params = {
                "search": query,
                "per_page": min(limit, 200),
                "filter": "type:article",
                "sort": "relevance_score:desc"
            }
            
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
            
            with urllib.request.urlopen(full_url, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                
                print(f"  OpenAlex: Found {len(results)} papers")
                
                for item in results:
                    doi = item.get("doi", "").replace("https://doi.org/", "") if item.get("doi") else ""
                    
                    if doi and doi in self.seen_dois:
                        continue
                    
                    authors = []
                    for auth in item.get("authorships", [])[:5]:
                        author_name = auth.get("author", {}).get("display_name", "")
                        if author_name:
                            authors.append(author_name)
                    authors_str = "; ".join(authors)
                    if len(item.get("authorships", [])) > 5:
                        authors_str += f" et al. ({len(item.get('authorships', []))} authors)"
                    
                    year = None
                    pub_date = item.get("publication_date", "")
                    if pub_date:
                        year = pub_date.split("-")[0]
                    
                    abstract = item.get("abstract", "") or ""
                    concepts = [c.get("display_name", "") for c in item.get("concepts", [])[:5]]
                    
                    paper = {
                        'PMID': None,
                        'doi': doi,
                        'title': item.get("display_name", ""),
                        'authors': authors_str,
                        'journal': item.get("primary_location", {}).get("source", {}).get("display_name", "Unknown"),
                        'year': year,
                        'abstract': abstract[:500] if abstract else "",
                        'mesh_terms': concepts,
                        'source': 'openalex'
                    }
                    
                    papers.append(paper)
                    
                    if doi:
                        self.seen_dois.add(doi)
                        
        except Exception as e:
            print(f"  OpenAlex error: {e}")
        
        return papers
    
    def search_crossref(self, query: str, limit: int = 100) -> List[Dict]:
        """Search Crossref."""
        papers = []
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": query,
                "rows": min(limit, 100),
                "sort": "relevance",
                "order": "desc",
                "filter": "type:journal-article"
            }
            
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
            
            headers = {'User-Agent': 'LiteratureSearchBot/1.0'}
            req = urllib.request.Request(full_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                results = data.get("message", {}).get("items", [])
                
                print(f"  Crossref: Found {len(results)} papers")
                
                for item in results:
                    doi = item.get("DOI", "")
                    
                    if doi and doi in self.seen_dois:
                        continue
                    
                    authors = []
                    for auth in item.get("author", [])[:5]:
                        given = auth.get("given", "")
                        family = auth.get("family", "")
                        if family:
                            name = f"{given} {family}".strip()
                            authors.append(name)
                    authors_str = "; ".join(authors)
                    if len(item.get("author", [])) > 5:
                        authors_str += f" et al. ({len(item.get('author', []))} authors)"
                    
                    year = None
                    published = item.get("published-print", {}) or item.get("published-online", {})
                    if published and published.get("date-parts"):
                        date_parts = published["date-parts"][0]
                        if date_parts and len(date_parts) > 0:
                            year = str(date_parts[0])
                    
                    title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
                    journal = item.get("container-title", ["Unknown"])[0] if isinstance(item.get("container-title"), list) else "Unknown"
                    
                    paper = {
                        'PMID': None,
                        'doi': doi,
                        'title': title,
                        'authors': authors_str,
                        'journal': journal,
                        'year': year,
                        'abstract': item.get("abstract", "")[:500] if item.get("abstract") else "",
                        'mesh_terms': [],
                        'source': 'crossref'
                    }
                    
                    papers.append(paper)
                    
                    if doi:
                        self.seen_dois.add(doi)
                        
        except Exception as e:
            print(f"  Crossref error: {e}")
        
        return papers


def filter_digenic_papers(papers: List[Dict]) -> List[Dict]:
    """Filter papers to only those with digenic/oligogenic in title."""
    filtered = []
    for paper in papers:
        title_lower = paper.get('title', '').lower()
        if 'digenic' in title_lower or 'oligogenic' in title_lower:
            filtered.append(paper)
    return filtered


def classify_papers(papers: List[Dict], classifier: SVMClassifier) -> List[Dict]:
    """Classify papers using SVM model."""
    print(f"\n🤖 Classifying {len(papers)} papers with SVM...")
    
    for i, paper in enumerate(papers):
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        text = f"{title}. {abstract}".strip()
        
        result = classifier.predict(text)
        paper['category'] = result['ml_category']
        paper['ml_confidence'] = result['ml_confidence']
        
        if (i + 1) % 50 == 0:
            print(f"  Classified {i + 1}/{len(papers)}...")
    
    return papers


def load_existing_papers() -> Dict:
    """Load existing papers from JSON."""
    with open(PAPERS_JSON, 'r') as f:
        return json.load(f)


def merge_papers(existing: Dict, new_papers: List[Dict]) -> Dict:
    """Merge new papers with existing, removing duplicates."""
    existing_pmids = {p.get('PMID') for p in existing['papers'] if p.get('PMID')}
    existing_dois = {p.get('doi') for p in existing['papers'] if p.get('doi')}
    
    added = 0
    skipped = 0
    
    for paper in new_papers:
        pmid = paper.get('PMID')
        doi = paper.get('doi')
        
        if pmid and pmid in existing_pmids:
            skipped += 1
            continue
        if doi and doi in existing_dois:
            skipped += 1
            continue
        
        existing['papers'].append(paper)
        added += 1
        if pmid:
            existing_pmids.add(pmid)
        if doi:
            existing_dois.add(doi)
    
    # Update metadata
    total = len(existing['papers'])
    categories = {'clinical': 0, 'tools': 0, 'review': 0}
    for p in existing['papers']:
        cat = p.get('category', 'clinical')
        if cat in categories:
            categories[cat] += 1
    
    existing['metadata']['last_updated'] = datetime.now().isoformat()
    existing['metadata']['total_papers'] = total
    existing['metadata']['categories'] = categories
    
    print(f"\n📊 Merge Results:")
    print(f"   New papers added: {added}")
    print(f"   Duplicates skipped: {skipped}")
    print(f"   Total papers: {total}")
    
    return existing


def save_papers(data: Dict):
    """Save papers to JSON."""
    with open(PAPERS_JSON, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved to {PAPERS_JSON}")


def generate_html(data: Dict):
    """Generate HTML viewer with embedded data."""
    print("\n🌐 Generating HTML viewer...")
    
    # Create HTML with embedded JSON data
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digenic/Oligogenic Disease Literature Viewer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        h1 {{ font-size: 2em; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .filters {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }}
        input, select {{ padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }}
        input[type="text"] {{ flex: 1; min-width: 200px; }}
        .papers {{ display: grid; gap: 15px; }}
        .paper {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .paper-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px; }}
        .paper-title {{ font-size: 1.2em; font-weight: 600; color: #333; margin-bottom: 8px; }}
        .paper-meta {{ color: #666; font-size: 0.9em; margin-bottom: 10px; }}
        .paper-abstract {{ color: #444; line-height: 1.6; margin-bottom: 10px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 500; }}
        .badge-clinical {{ background: #e3f2fd; color: #1976d2; }}
        .badge-tools {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-review {{ background: #e8f5e9; color: #388e3c; }}
        .confidence {{ font-size: 0.8em; color: #999; margin-left: 10px; }}
        .hidden {{ display: none; }}
        .no-results {{ text-align: center; padding: 40px; color: #666; }}
        .footer {{ text-align: center; margin-top: 40px; padding: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔬 Digenic/Oligogenic Disease Literature</h1>
            <p>Comprehensive database of digenic and oligogenic inheritance research</p>
            <p>Last updated: {data['metadata']['last_updated'][:10]}</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{data['metadata']['total_papers']}</div>
                <div class="stat-label">Total Papers</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data['metadata']['categories']['clinical']}</div>
                <div class="stat-label">Clinical</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data['metadata']['categories']['tools']}</div>
                <div class="stat-label">Tools</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data['metadata']['categories']['review']}</div>
                <div class="stat-label">Reviews</div>
            </div>
        </div>
        
        <div class="filters">
            <input type="text" id="searchInput" placeholder="Search titles, abstracts, authors...">
            <select id="categoryFilter">
                <option value="">All Categories</option>
                <option value="clinical">Clinical</option>
                <option value="tools">Tools</option>
                <option value="review">Review</option>
            </select>
            <select id="sourceFilter">
                <option value="">All Sources</option>
                <option value="pubmed">PubMed</option>
                <option value="europepmc">Europe PMC</option>
                <option value="openalex">OpenAlex</option>
                <option value="crossref">Crossref</option>
            </select>
            <select id="yearFilter">
                <option value="">All Years</option>
                <option value="2026">2026</option>
                <option value="2025">2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
                <option value="2021">2021</option>
                <option value="2020">2020</option>
                <option value="2019">2019</option>
            </select>
        </div>
        
        <div id="papersContainer" class="papers"></div>
        <div id="noResults" class="no-results hidden">No papers found matching your criteria.</div>
        
        <div class="footer">
            <p>Data sources: PubMed, Europe PMC, OpenAlex, Crossref | Classified using SVM model</p>
        </div>
    </div>
    
    <script>
        const papers = {json.dumps(data['papers'])};
        
        function renderPapers(papersToRender) {{
            const container = document.getElementById('papersContainer');
            const noResults = document.getElementById('noResults');
            
            if (papersToRender.length === 0) {{
                container.innerHTML = '';
                noResults.classList.remove('hidden');
                return;
            }}
            
            noResults.classList.add('hidden');
            container.innerHTML = papersToRender.map(paper => `
                <div class="paper" data-category="${{paper.category}}" data-source="${{paper.source}}" data-year="${{paper.year || ''}}">
                    <div class="paper-header">
                        <div>
                            <div class="paper-title">${{paper.title}}</div>
                            <div class="paper-meta">
                                ${{paper.authors}} | ${{paper.journal}} | ${{paper.year || 'N/A'}}
                                ${{paper.PMID ? `| <a href="https://pubmed.ncbi.nlm.nih.gov/${{paper.PMID}}/" target="_blank">PMID:${{paper.PMID}}</a>` : ''}}
                                ${{paper.doi ? `| <a href="https://doi.org/${{paper.doi}}" target="_blank">DOI</a>` : ''}}
                            </div>
                        </div>
                        <span class="badge badge-${{paper.category}}">${{paper.category}}</span>
                        ${{paper.ml_confidence ? `<span class="confidence">(${{(paper.ml_confidence * 100).toFixed(0)}}%)</span>` : ''}}
                    </div>
                    <div class="paper-abstract">${{paper.abstract || 'No abstract available.'}}</div>
                </div>
            `).join('');
        }}
        
        function filterPapers() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const category = document.getElementById('categoryFilter').value;
            const source = document.getElementById('sourceFilter').value;
            const year = document.getElementById('yearFilter').value;
            
            const filtered = papers.filter(p => {{
                const matchesSearch = !searchTerm || 
                    p.title.toLowerCase().includes(searchTerm) ||
                    (p.abstract && p.abstract.toLowerCase().includes(searchTerm)) ||
                    (p.authors && p.authors.toLowerCase().includes(searchTerm));
                const matchesCategory = !category || p.category === category;
                const matchesSource = !source || p.source === source;
                const matchesYear = !year || p.year === year;
                
                return matchesSearch && matchesCategory && matchesSource && matchesYear;
            }});
            
            renderPapers(filtered);
        }}
        
        document.getElementById('searchInput').addEventListener('input', filterPapers);
        document.getElementById('categoryFilter').addEventListener('change', filterPapers);
        document.getElementById('sourceFilter').addEventListener('change', filterPapers);
        document.getElementById('yearFilter').addEventListener('change', filterPapers);
        
        renderPapers(papers);
    </script>
</body>
</html>'''
    
    with open(HTML_FILE, 'w') as f:
        f.write(html_content)
    print(f"✓ Generated {HTML_FILE}")


def run_verify_sync():
    """Run sync verification script."""
    print("\n🔍 Running sync verification...")
    try:
        result = subprocess.run(
            ['python3', str(VERIFY_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_DIR)
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️  Verification warnings: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"⚠️  Could not run verification: {e}")
        return True


def push_to_github():
    """Push updates to GitHub."""
    print("\n📤 Pushing to GitHub...")
    try:
        # Copy files to repo
        subprocess.run(['cp', str(PAPERS_JSON), f'{GITHUB_REPO}/docs/'], check=True)
        subprocess.run(['cp', str(HTML_FILE), f'{GITHUB_REPO}/docs/'], check=True)
        
        # Git operations
        subprocess.run(['git', 'add', '-A'], cwd=GITHUB_REPO, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=GITHUB_REPO,
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            print("✓ No changes to push")
            return True
        
        # Commit and push
        date_str = datetime.now().strftime('%Y-%m-%d')
        subprocess.run(
            ['git', 'commit', '-m', f'Update literature database - {date_str}'],
            cwd=GITHUB_REPO,
            check=True
        )
        subprocess.run(['git', 'push'], cwd=GITHUB_REPO, check=True)
        
        print("✓ Pushed to GitHub successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub push failed: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Automated literature search with SVM classification')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving/pushing')
    args = parser.parse_args()
    
    print("=" * 60)
    print("AUTOMATED LITERATURE SEARCH + SVM CLASSIFICATION")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize classifier
    print("\n🤖 Loading SVM classifier...")
    classifier = SVMClassifier()
    print("✓ Classifier ready")
    
    # Load existing papers
    print("\n📚 Loading existing papers...")
    existing_data = load_existing_papers()
    prev_count = len(existing_data['papers'])
    print(f"✓ Loaded {prev_count} existing papers")
    
    # Search databases
    print("\n🔍 Searching databases...")
    searcher = LiteratureSearch()
    
    search_queries = [
        '(digenic[Title] OR oligogenic[Title]) AND ("2024"[Date - Publication] : "3000"[Date - Publication])',
        '(digenic inheritance[Title] OR oligogenic inheritance[Title])',
        '(digenic disease[Title] OR oligogenic disease[Title])',
    ]
    
    all_new_papers = []
    
    for query in search_queries:
        print(f"\n📖 Query: {query[:60]}...")
        papers = searcher.search_pubmed(query, limit=100)
        papers = filter_digenic_papers(papers)
        print(f"   Filtered to {len(papers)} digenic papers")
        all_new_papers.extend(papers)
    
    # Search other sources
    print("\n📖 Searching Europe PMC...")
    papers = searcher.search_europe_pmc('digenic OR oligogenic', limit=50)
    papers = filter_digenic_papers(papers)
    print(f"   Filtered to {len(papers)} digenic papers")
    all_new_papers.extend(papers)
    
    print("\n📖 Searching OpenAlex...")
    papers = searcher.search_openalex('digenic disease', limit=100)
    papers = filter_digenic_papers(papers)
    print(f"   Filtered to {len(papers)} digenic papers")
    all_new_papers.extend(papers)
    
    print("\n📖 Searching Crossref...")
    papers = searcher.search_crossref('digenic inheritance', limit=50)
    papers = filter_digenic_papers(papers)
    print(f"   Filtered to {len(papers)} digenic papers")
    all_new_papers.extend(papers)
    
    print(f"\n📊 Total unique papers found: {len(all_new_papers)}")
    
    if not all_new_papers:
        print("\n✓ No new papers found. Database is up to date.")
        return
    
    # Classify papers
    classified_papers = classify_papers(all_new_papers, classifier)
    
    # Merge with existing
    merged_data = merge_papers(existing_data, classified_papers)
    
    if args.dry_run:
        print("\n🏃 DRY RUN - Not saving changes")
        return
    
    # Save papers
    print("\n💾 Saving papers...")
    save_papers(merged_data)
    
    # Generate HTML
    generate_html(merged_data)
    
    # Verify sync
    run_verify_sync()
    
    # Push to GitHub
    push_to_github()
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE")
    print("=" * 60)
    print(f"New papers added: {len(merged_data['papers']) - prev_count}")
    print(f"Total papers: {len(merged_data['papers'])}")
    print(f"Live site: https://slavebot007-star.github.io/digenic-literature-viewer/")


if __name__ == "__main__":
    main()
