# MEMORY.md - Long-Term Memory

## Core Preferences

### Use Kimi for Coding Tasks
**Rule:** Always use Kimi (kimi-cli) for coding tasks when possible.

**Why:**
- Kimi provides better code generation and debugging
- Can handle complex multi-file tasks
- Has access to tools and can execute commands
- Provides structured output and diffs

**When to use Kimi:**
- Writing new scripts or functions
- Debugging existing code
- Refactoring or improving code
- Creating complex workflows
- Analyzing code issues

**When NOT to use Kimi:**
- Simple one-line commands (use direct exec)
- File reading/writing without logic (use direct tools)
- Quick checks (use direct tools)

### Kimi Task Planning Template

For every coding task given to Kimi, provide:

1. **Clear Goal** - What needs to be accomplished
2. **Context** - Relevant files, existing code, dependencies
3. **Constraints** - Limitations, requirements, must-haves
4. **Expected Output** - What the result should look like
5. **Testing Criteria** - How to verify it works

### Example Kimi Prompt Structure:

```
Task: [Brief description]

Goal:
[What needs to be done]

Context:
- Existing files: [list relevant files]
- Current implementation: [describe current state]
- Dependencies: [what it needs to work with]

Requirements:
- [Requirement 1]
- [Requirement 2]
- [Constraint 1]

Expected Output:
[Description of final result]

Testing:
[How to verify it works]
```

## Project Context

### Digenic/Oligogenic Disease Literature Viewer
- **Repository:** slavebot007-star/digenic-literature-viewer
- **Website:** https://slavebot007-star.github.io/digenic-literature-viewer/
- **Current Papers:** 1238 (2019-2026)
- **Categories:** Tools (51), Clinical (1161), Review (26)
- **Data Source:** PubMed, Europe PMC, OpenAlex, CrossRef with MeSH-based categorization

### Key Files:
- `/root/.openclaw/workspace/comprehensive_papers.json` - Main paper database
- `/root/.openclaw/workspace/literature-viewer.html` - HTML viewer template
- `/root/.openclaw/workspace/scripts/verify_sync.py` - Sync verification script
- `/tmp/digenic-literature-viewer/` - GitHub repo clone

### Literature Search Skill:
- Location: `/root/.openclaw/skills/literature-search/`
- Script: `scripts/lit_search.py`
- Features: PubMed search with MeSH extraction, categorization

### Scientific Skills Installed:
- 148+ skills from K-Dense AI repository
- Key: biorxiv-database, pubmed-database, biopython, chembl-database
- Location: `/root/.openclaw/skills/`

## Important Decisions

1. **MeSH-based Categorization** - Use MeSH terms as primary signal for paper categorization
2. **Strict Title Filtering** - Only keep papers with "digenic" or "oligogenic" in title
3. **Date Range:** 2019-2026 for comprehensive coverage
4. **GitHub Integration** - Auto-push updates to GitHub Pages

## Lessons Learned

1. **PubMed API is better than bioRxiv** - bioRxiv lacks search API, requires iteration
2. **MeSH terms are reliable** - Better than keyword counting for categorization
3. **Parallel subagents speed up searches** - Use for multiple queries
4. **Always verify after updates** - Check counts and key papers
5. **ALWAYS run verify_sync.py before pushing** - Prevents workspace/repo sync bugs (March 2025 incident: repo had 231 papers, workspace had 1238)

## Active Tasks

- [ ] Monitor literature search cronjob (runs weekdays 9 AM Houston time)
- [ ] Add more papers from bioRxiv when API allows
- [ ] Improve categorization accuracy
- [ ] Add citation network analysis
