#!/usr/bin/env python3
"""
Digenic Paper Classifier - Batch Classification Script
======================================================

Uses the trained SVM model to classify all papers in comprehensive_papers.json
and compares with existing MeSH-based categorization.

Usage:
    python classify_digenic_papers.py
    python classify_digenic_papers.py --compare  # Show comparison with existing categories
    python classify_digenic_papers.py --update   # Update JSON with ML predictions
"""

import json
import sys
import pickle
import math
from pathlib import Path
from typing import Dict, List, Union, Optional
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

# Paths
WORKSPACE_DIR = Path("/root/.openclaw/workspace")
CLASSIFIER_DIR = Path("/root/.openclaw/media/inbound/paper_classifier")
PAPERS_JSON = WORKSPACE_DIR / "comprehensive_papers.json"

# Model files
MODEL_PATH = CLASSIFIER_DIR / "svm_model.pkl"
VECTORIZER_PATH = CLASSIFIER_DIR / "tfidf_vectorizer.pkl"


class DigenicPaperClassifier:
    """Classifier wrapper for digenic papers using the trained SVM model."""
    
    # Map SVM categories to our category names
    CATEGORY_MAP = {
        "Tool/Method": "tools",
        "Clinical/Biological": "clinical",
        "Review": "review"
    }
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.categories = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained SVM model and vectorizer."""
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        if not VECTORIZER_PATH.exists():
            raise FileNotFoundError(f"Vectorizer file not found: {VECTORIZER_PATH}")
        
        with open(MODEL_PATH, 'rb') as f:
            self.model = pickle.load(f)
        with open(VECTORIZER_PATH, 'rb') as f:
            self.vectorizer = pickle.load(f)
        
        # Extract categories from model
        if hasattr(self.model, 'classes_'):
            self.categories = list(self.model.classes_)
        else:
            self.categories = ["Tool/Method", "Clinical/Biological", "Review"]
        
        print(f"✓ Loaded model: {type(self.model).__name__}")
        print(f"✓ Categories: {self.categories}")
    
    def predict(self, text: str) -> Dict[str, Union[str, float]]:
        """Predict category for a single paper."""
        if not text or len(text.strip()) < 10:
            return {
                'ml_category': 'unknown',
                'ml_confidence': 0.0,
                'all_scores': {}
            }
        
        # Make prediction
        prediction = self.model.predict([text])[0]
        
        # Get confidence
        confidence = self._get_confidence([text], prediction)
        
        # Get all scores
        all_scores = self._get_all_scores([text])
        
        # Map to our category names
        ml_category = self.CATEGORY_MAP.get(prediction, prediction.lower())
        
        return {
            'ml_category': ml_category,
            'ml_confidence': confidence,
            'all_scores': all_scores
        }
    
    def _get_confidence(self, text, prediction) -> float:
        """Get confidence score for prediction."""
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
    
    def _get_all_scores(self, text) -> Dict[str, float]:
        """Get scores for all categories."""
        scores = {}
        
        if hasattr(self.model, 'predict_proba'):
            try:
                proba = self.model.predict_proba(text)[0]
                for cls, prob in zip(self.model.classes_, proba):
                    mapped = self.CATEGORY_MAP.get(cls, cls.lower())
                    scores[mapped] = float(prob)
                return scores
            except:
                pass
        
        if hasattr(self.model, 'decision_function'):
            try:
                decision = self.model.decision_function(text)[0]
                if hasattr(decision, '__iter__'):
                    exp_decisions = [math.exp(d) for d in decision]
                    sum_exp = sum(exp_decisions)
                    softmax = [e / sum_exp for e in exp_decisions]
                    for cls, score in zip(self.model.classes_, softmax):
                        mapped = self.CATEGORY_MAP.get(cls, cls.lower())
                        scores[mapped] = float(score)
                    return scores
            except:
                pass
        
        return scores
    
    def predict_batch(self, papers: List[Dict]) -> List[Dict]:
        """Predict categories for multiple papers."""
        results = []
        total = len(papers)
        
        for i, paper in enumerate(papers, 1):
            # Combine title and abstract for classification
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            text = f"{title}. {abstract}".strip()
            
            result = self.predict(text)
            result['pmid'] = paper.get('PMID', paper.get('pmid', 'unknown'))
            result['title'] = title[:80] + '...' if len(title) > 80 else title
            result['existing_category'] = paper.get('category', 'unknown')
            
            results.append(result)
            
            if i % 100 == 0 or i == total:
                print(f"  Processed {i}/{total} papers...")
        
        return results


def load_papers() -> Dict:
    """Load papers from JSON file."""
    with open(PAPERS_JSON, 'r') as f:
        return json.load(f)


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze classification results."""
    total = len(results)
    
    # Count ML predictions
    ml_counts = {}
    for r in results:
        cat = r['ml_category']
        ml_counts[cat] = ml_counts.get(cat, 0) + 1
    
    # Compare with existing categories
    agreements = 0
    disagreements = 0
    confusion = {}
    
    for r in results:
        ml_cat = r['ml_category']
        existing_cat = r['existing_category']
        
        if ml_cat == existing_cat:
            agreements += 1
        else:
            disagreements += 1
            key = f"{existing_cat} → {ml_cat}"
            confusion[key] = confusion.get(key, 0) + 1
    
    # High confidence predictions
    high_conf = sum(1 for r in results if r['ml_confidence'] >= 0.6)
    medium_conf = sum(1 for r in results if 0.4 <= r['ml_confidence'] < 0.6)
    low_conf = sum(1 for r in results if r['ml_confidence'] < 0.4)
    
    return {
        'total': total,
        'ml_distribution': ml_counts,
        'existing_distribution': {},  # Will be filled by caller
        'agreements': agreements,
        'disagreements': disagreements,
        'agreement_rate': agreements / total * 100 if total > 0 else 0,
        'confusion_matrix': confusion,
        'confidence_distribution': {
            'high': high_conf,
            'medium': medium_conf,
            'low': low_conf
        }
    }


def print_report(analysis: Dict, data: Dict):
    """Print classification report."""
    print("\n" + "=" * 60)
    print("DIGENIC PAPER CLASSIFICATION REPORT")
    print("=" * 60)
    
    print(f"\n📊 Total Papers: {analysis['total']}")
    
    # Existing categories
    print("\n📁 Existing Categories (MeSH-based):")
    for cat, count in data['metadata']['categories'].items():
        pct = count / analysis['total'] * 100
        print(f"   {cat:12s}: {count:4d} ({pct:5.1f}%)")
    
    # ML predictions
    print("\n🤖 ML-Predicted Categories (SVM):")
    for cat in ['clinical', 'tools', 'review', 'unknown']:
        count = analysis['ml_distribution'].get(cat, 0)
        pct = count / analysis['total'] * 100 if analysis['total'] > 0 else 0
        print(f"   {cat:12s}: {count:4d} ({pct:5.1f}%)")
    
    # Agreement
    print("\n📈 Agreement Analysis:")
    print(f"   Agreements:    {analysis['agreements']:4d} ({analysis['agreement_rate']:.1f}%)")
    print(f"   Disagreements: {analysis['disagreements']:4d} ({100-analysis['agreement_rate']:.1f}%)")
    
    # Confidence distribution
    print("\n🎯 Confidence Distribution:")
    conf = analysis['confidence_distribution']
    total = analysis['total']
    print(f"   High (≥60%):   {conf['high']:4d} ({conf['high']/total*100:.1f}%)")
    print(f"   Medium (40-60%): {conf['medium']:4d} ({conf['medium']/total*100:.1f}%)")
    print(f"   Low (<40%):    {conf['low']:4d} ({conf['low']/total*100:.1f}%)")
    
    # Top disagreements
    if analysis['confusion_matrix']:
        print("\n⚠️  Top Category Disagreements:")
        sorted_confusion = sorted(
            analysis['confusion_matrix'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for change, count in sorted_confusion:
            print(f"   {change:30s}: {count:3d}")
    
    print("\n" + "=" * 60)


def save_results(results: List[Dict], output_path: str):
    """Save classification results to JSON."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {output_path}")


def update_papers_json(data: Dict, results: List[Dict]):
    """Update the papers JSON with ML predictions."""
    # Create lookup by PMID
    result_lookup = {r['pmid']: r for r in results}
    
    # Update each paper
    updated_count = 0
    for paper in data['papers']:
        pmid = paper.get('PMID', paper.get('pmid'))
        if pmid in result_lookup:
            result = result_lookup[pmid]
            paper['ml_category'] = result['ml_category']
            paper['ml_confidence'] = result['ml_confidence']
            paper['ml_scores'] = result['all_scores']
            updated_count += 1
    
    # Update metadata
    data['metadata']['ml_classified'] = True
    data['metadata']['ml_classification_date'] = "2026-03-03"
    
    # Save updated JSON
    with open(PAPERS_JSON, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Updated {updated_count} papers in {PAPERS_JSON}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Classify digenic papers using SVM model')
    parser.add_argument('--compare', action='store_true', help='Show detailed comparison')
    parser.add_argument('--update', action='store_true', help='Update JSON with ML predictions')
    parser.add_argument('--output', type=str, help='Save results to file')
    args = parser.parse_args()
    
    print("Loading papers...")
    data = load_papers()
    papers = data['papers']
    print(f"✓ Loaded {len(papers)} papers")
    
    print("\nInitializing classifier...")
    classifier = DigenicPaperClassifier()
    
    print("\nClassifying papers...")
    results = classifier.predict_batch(papers)
    
    print("\nAnalyzing results...")
    analysis = analyze_results(results)
    
    print_report(analysis, data)
    
    if args.compare:
        print("\n📋 Sample Predictions:")
        print("-" * 80)
        for r in results[:5]:
            match = "✓" if r['ml_category'] == r['existing_category'] else "✗"
            print(f"{match} PMID: {r['pmid']}")
            print(f"  Title: {r['title'][:70]}...")
            print(f"  Existing: {r['existing_category']:12s} | ML: {r['ml_category']:12s} | Conf: {r['ml_confidence']:.1%}")
            print()
    
    if args.output:
        save_results(results, args.output)
    
    if args.update:
        print("\nUpdating papers JSON...")
        update_papers_json(data, results)
    
    print("\n✓ Classification complete!")


if __name__ == "__main__":
    main()
