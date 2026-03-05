# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## ⚠️ CRITICAL CHECKLIST - Always Do These!

### After Updating Literature Search / HTML
- [ ] Update `comprehensive_papers.json` with new data
- [ ] Regenerate `literature-viewer.html` with embedded data
- [ ] **RUN SYNC CHECK** - `cd /root/.openclaw/workspace && python3 scripts/verify_sync.py`
- [ ] **PUSH TO GITHUB** - `cd /tmp/digenic-literature-viewer && git add -A && git commit -m "..." && git push`
- [ ] **CHECK & FIX CI ISSUES** - `cd /tmp/digenic-literature-viewer && gh run list` then fix any failures
- [ ] Verify live site shows correct data

### GitHub Push Required For:
- Any HTML file changes
- Any paper data updates
- Category corrections
- New papers added

### Preventing Sync Bugs
1. **Always run verify_sync.py before pushing** - catches mismatches early
2. **Workspace is source of truth** - never edit /tmp/digenic-literature-viewer directly
3. **Check paper counts match** - workspace JSON vs repo JSON should be identical
4. **Verify JSON structure** - must have `metadata` + `papers` keys, not a plain list

---

Add whatever helps you do your job. This is your cheat sheet.
