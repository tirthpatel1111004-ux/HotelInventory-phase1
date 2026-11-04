# Hotel Inventory Management System — Web Version

A working, local web-based prototype for COMP-296. It uses **Python 3 standard library** for the server and **SQLite** for persistent SQL storage. No pip installation, third-party packages, or internet connection is required.

## Run

1. Install Python 3.9+ if not installed.
2. Open a terminal inside this folder.
3. Run `python3 app.py` (on Windows, `py app.py`).
4. Open `http://127.0.0.1:8000` in a browser.

### Demo accounts (local use only)

| Role | Employee ID | Password |
| --- | --- | --- |
| Manager | M100 | HotelDemo2026! |
| Staff | S101 | StaffDemo2026! |

**Change these demo credentials before any deployment.** The app is intended for local coursework demonstration, not public internet hosting. Sessions live in memory and end on server restart. The database is saved as `hotel_inventory.db` in this folder. To reset demo data, stop the server and delete that file.

## Functionality

- Staff: log in, view inventory, search by item/category, update quantities, view low-stock items.
- Manager: all staff actions plus add/edit items, category reports, employee creation, activity history, downloadable CSV exports.
- SQLite tables: `users`, `categories`, `inventory`, `activity`.
- Passwords are stored using salted PBKDF2 hashes, rather than plaintext.
- Login sessions, CSRF tokens on all write forms, role authorization and parameterized SQL queries.

## Testing

Run `python3 -m unittest -v test_app.py` from this folder. The tests use an isolated temporary database and a real local HTTP server; they do not change the application database.

## Dates and milestones in Deliverable 6

The original slide deck plans nine stages: Oct 30, Nov 3, Nov 7, Nov 12, Nov 16, Nov 20, Nov 23, Nov 26, and Nov 30, 2026. The bundled prototype illustrates those planned capabilities now. These dates are **planned academic milestones, not evidence of actual work completion on those dates**. Run acceptance tests and record completion dates as you implement and review each stage.

## Difference from the original deck

The earlier proposal explicitly specified **Java/JavaFX desktop + MySQL**. The latest request explicitly changes the project to **web-based**. This package implements a Python/SQLite web proof-of-concept rather than claiming it is the originally proposed JavaFX implementation. Check with the professor whether switching the technology stack is acceptable. The PowerPoint companion identifies this proposed change.

## GitHub upload

Extract the ZIP to a project folder, confirm tests pass, and commit `app.py`, `test_app.py`, `README.md`, and `.gitignore` to the existing GitHub repository. **Do not commit `hotel_inventory.db`, `.env` files, or any real passwords.** The ZIP is not automatically uploaded to GitHub.
