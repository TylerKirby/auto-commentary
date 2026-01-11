# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Project Subagents

This project has two specialized subagents that should be used proactively:

### language-expert
**Use when:** Validating Greek/Latin linguistic output from the pipeline.

Call this agent:
- After generating samples to verify definitions are accurate
- After making changes to normalizers or lexicons
- When reviewing headword reconstructions or principal parts
- To validate morphological analysis accuracy

```
# Examples of when to invoke:
"Review the Greek definitions in output/greek_sample/"
"Check if the Latin headwords are correctly reconstructed"
"Validate the principal parts for the verbs in this output"
```

### book-formatting-qa
**Use when:** Reviewing PDF/LaTeX output for Steadman formatting compliance.

Call this agent:
- After generating commentary PDFs
- To verify glossary layout and typography
- When checking for rendering issues with Greek/Latin characters

```
# Examples of when to invoke:
"Review the formatting of output/latin_sample/commentary.pdf"
"Check if the glossary entries match Steadman style"
```

## Beads Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Session Completion Protocol

**When ending a work session**, complete ALL steps:

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```

**CRITICAL:** Work is NOT complete until `git push` succeeds.
