# Kimi Task Planning Guide

## How to Use Kimi for Coding Tasks

### Basic Command Structure

```bash
kimi --print --yolo -p "YOUR_TASK_HERE"
```

Or for interactive mode:
```bash
kimi -p "YOUR_TASK_HERE"
```

### Task Planning Template

Every coding task should follow this structure:

```
## Task: [Brief Title]

### Goal
[What needs to be accomplished in 1-2 sentences]

### Context
**Existing Files:**
- [file1] - [purpose]
- [file2] - [purpose]

**Current State:**
[Description of what currently exists]

**Dependencies:**
- [dependency1]
- [dependency2]

### Requirements
1. [Specific requirement 1]
2. [Specific requirement 2]
3. [Specific requirement 3]

### Constraints
- [Constraint 1]
- [Constraint 2]

### Expected Output
[Description of what the final result should be]

### Testing Criteria
- [Test 1: How to verify it works]
- [Test 2: Expected behavior]

### Additional Notes
[Any other relevant information]
```

## Example Tasks

### Example 1: Fix a Bug

```
Task: Fix bioRxiv search pagination bug

Goal:
Fix the cursor pagination in bioRxiv search script so it properly iterates through all papers.

Context:
Existing Files:
- /root/.openclaw/skills/literature-search/scripts/search_biorxiv.py - Main search script

Current State:
The script only checks 100 papers then stops because cursor isn't incrementing properly.

Dependencies:
- requests library
- bioRxiv API

Requirements:
1. Cursor should increment by 100 for each page
2. Stop when all papers are checked
3. Handle API rate limits

Constraints:
- Must use bioRxiv API format: /details/biorxiv/START_DATE/END_DATE/CURSOR
- Keep existing filtering logic

Expected Output:
Script that iterates through all papers in date range and finds matches.

Testing Criteria:
- Run script and verify it checks more than 100 papers
- Verify matches are found and saved
- Check output JSON is valid
```

### Example 2: Add Feature

```
Task: Add MeSH term extraction to PubMed search

Goal:
Extract MeSH terms from PubMed papers and use them for categorization.

Context:
Existing Files:
- /root/.openclaw/skills/literature-search/scripts/lit_search.py - Literature search script

Current State:
Script uses keyword matching for categorization, which is inaccurate.

Dependencies:
- PubMed E-utilities API
- XML parsing (ElementTree)

Requirements:
1. Parse MeSH terms from PubMed XML
2. Use MeSH terms as primary categorization signal
3. Fall back to keywords if no MeSH terms

Constraints:
- Must use efetch.fcgi with retmode=xml
- Parse MeshHeading elements
- Keep backward compatibility

Expected Output:
Updated lit_search.py with MeSH extraction and improved categorize_paper() function.

Testing Criteria:
- Search returns papers with mesh_terms field
- Categorization uses MeSH when available
- Papers without MeSH still work
```

### Example 3: Create New Script

```
Task: Create script to merge bioRxiv and PubMed results

Goal:
Create a script that converts bioRxiv search results and merges them with existing PubMed database.

Context:
Existing Files:
- /root/.openclaw/workspace/comprehensive_papers.json - Main database
- biorxiv_digenic_papers.json - bioRxiv search results

Current State:
Two separate data sources that need to be combined.

Dependencies:
- JSON handling
- DOI deduplication

Requirements:
1. Convert bioRxiv format to match comprehensive_papers.json
2. Deduplicate by DOI
3. Merge without losing existing data
4. Save to comprehensive_papers.json

Constraints:
- bioRxiv papers don't have PMIDs (set to None)
- Must preserve existing categories
- Add source field to track origin

Expected Output:
Python script convert_biorxiv_to_viewer.py that merges data sources.

Testing Criteria:
- Run script and verify output file
- Check that DOIs are unique
- Verify count increases correctly
- Test with --merge flag
```

## Best Practices

### 1. Be Specific
- ✅ "Fix cursor pagination to increment by 100"
- ❌ "Fix the script"

### 2. Provide Context
- Always mention relevant files
- Describe current behavior
- Explain what needs to change

### 3. Include Examples
- Show expected input/output
- Provide sample data if needed
- Describe edge cases

### 4. Define Success
- Clear testing criteria
- Expected results
- How to verify it works

### 5. Keep It Focused
- One main task per prompt
- Break complex tasks into steps
- Use multiple prompts for multi-step work

## Common Patterns

### Debugging Pattern
```
Task: Debug [issue]

Goal: Fix [specific error]

Context:
- File: [path]
- Error: [error message]
- Line: [line number if known]

Current Behavior:
[What happens now]

Expected Behavior:
[What should happen]

Testing:
[How to reproduce and verify fix]
```

### Refactoring Pattern
```
Task: Refactor [component]

Goal: Improve [aspect] of [component]

Context:
- Current implementation: [description]
- Issues: [what's wrong]

Requirements:
1. [Improvement 1]
2. [Improvement 2]

Constraints:
- Maintain backward compatibility
- Don't break existing tests

Testing:
- [Test case 1]
- [Test case 2]
```

### Integration Pattern
```
Task: Integrate [A] with [B]

Goal: Connect [component A] to [component B]

Context:
- A: [description]
- B: [description]
- Current relationship: [how they interact now]

Requirements:
1. [Integration requirement 1]
2. [Integration requirement 2]

Expected Output:
[Description of integrated system]

Testing:
- [Integration test 1]
- [Integration test 2]
```

## Quick Reference

| Task Type | Key Elements |
|-----------|--------------|
| Bug Fix | Error message, file location, expected behavior |
| Feature Add | New functionality, where to add, how it integrates |
| Refactor | Current issues, improvements, constraints |
| Integration | Components, data flow, interface requirements |
| Analysis | Data source, analysis goal, output format |

## Remember

1. **Always use `--print --yolo` for non-interactive tasks**
2. **Provide file paths explicitly**
3. **Include error messages when debugging**
4. **Define what success looks like**
5. **Test after Kimi completes the task**
