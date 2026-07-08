# GitHub issue import — monsoon

`docs/roadmap_issues.csv` is the source of truth for the **active roadmap issues** (MS-01 …).

## One-time setup

1. Create milestones `V1.0` and `V1.1` on the repo (if missing).
2. Create labels from the CSV (`prio:p0`, `area:gmail`, …) or let `gh` skip unknown labels.

## Import

```bash
# Preview commands
python scripts/create_roadmap_issues.py

# Create issues (requires gh auth)
python scripts/create_roadmap_issues.py --apply
```

## Lifecycle

Per `agent_rules.md`:

- Every issue links to a milestone — no orphans.
- Board columns: Backlog → To Do → In Progress → Done.
- Update issue status when starting/finishing work; reference `MS-NN` in commits.

## Roadmap sync

When adding or closing issues, update `ROADMAP.md` and `docs/roadmap_issues.csv` together.
