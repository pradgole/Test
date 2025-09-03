Project Tracker (Flask + SQLite)
================================

A lightweight CRUD web app to replace the spreadsheet for tracking client projects, modules, and per-module entries (event rows) with estimated/actual efforts, statuses, comments, and assigned developers.

Quickstart
----------

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the server:

```bash
python app.py
```

The app will create `tracker.db` on first run and start at `http://localhost:5000`.

Data Model
----------

- Client → Project → Module → Entry
- Developers are managed separately and can be assigned to each entry (many-to-many)

Key fields in Entry:
- event_id, template_type, subevents_count
- estimated_efforts, actual_efforts (floats)
- content_integration_status, assets_alignment_status, comments

Notes
-----

- Deleting a parent cascades down (e.g., deleting a Project deletes its Modules and Entries)
- Totals per Module and per Entries page are shown in the UI

Importing from Excel
--------------------

Export your sheet to CSV and adapt it to the Entry fields per Module. You can either:
- Manually add via UI, or
- Use a one-off import script using SQLAlchemy (not included here yet)

