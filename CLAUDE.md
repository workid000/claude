# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app:**
```powershell
python app.py
```
Starts on `http://localhost:5001` with Flask debug mode.

**Install dependencies:**
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Run tests:**
```powershell
pytest
```

## Architecture

Flask + SQLite application. Backend in `app.py`, templates in `templates/`, CSS/JS in `static/`.

**Route structure (`app.py`):**
- Implemented: `/`, `/login`, `/register`, `/terms`, `/privacy`
- Stubs (to be built out): `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`

**Database layer (`database/db.py`):** SQLite helper module — currently a stub. This is where the db connection, schema creation, and query functions belong.

**Template inheritance:** All pages extend `templates/base.html`, which provides the navbar and footer.

## Design System

CSS custom properties are defined at the top of `static/css/style.css`:
- Colors: `--ink`, `--paper`, `--accent` (dark green `#1a472a`), `--accent-2` (amber `#c17f24`), `--danger`
- Fonts: DM Sans (body), DM Serif Display (headings) via Google Fonts
- Use class-based styling from `style.css` and `static/css/landing.css`. Do not use inline styles.

## Current State

Marketing, legal pages, and auth templates are complete. The core app (expenses CRUD, database, session auth) is not yet implemented — those are the next steps.
