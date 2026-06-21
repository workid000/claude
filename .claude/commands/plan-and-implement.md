---
description: Create a plan file and switch to feature branch if not already on related spec branch.
argument-hint: "Step number and feature name e.g. 2 registration-plan"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer spinning up a new feature for the
Spendly expense tracker. Always follow the rules in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status` and check for uncommitted, unstaged, or
untracked files. If any exist, stop immediately and tell
the user to commit or stash changes before proceeding.
DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `step_number` — zero-padded to 2 digits: 2 → 02, 11 → 11

2. `feature_title` — human readable title in Title Case
   - Example: "Registration" or "Login and Logout"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: registration, login-logout

4. `branch_name` — format: `feature/<feature_slug>`
   - Example: `feature/registration`

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.

## Step 3 — Check current branch and switch to feature branch 
Run `git branch` to list existing branches.
If current branch is not `branch_name` then switch to the feature branch
Run:
```
git checkout <branch_name>
```

## Step 4 — Research the spec
Read these files before planning:
- `CLAUDE.md` — roadmap, conventions, schema
- `app.py` — existing routes and structure
- `database/db.py` — existing schema and functions
- Spec file - `.claude/specs/<step_number>-<feature_slug>.md`


## Step 5 — Write the plan
Enter Plan Mode with Shift+Tab twice
Generate a plan document based on spec file - `.claude/specs/<step_number>-<feature_slug>.md`
Save the plan at `.claude/plans/<step_number>-<feature_slug>-plan.md` 
Then tell the user:
"Review the plan at `.claude/plan/<step_number>-<feature_slug>-plan.md`
Don't write any code until user acknowledges.