# TODO (GitHub)

## Completed / Implemented (push to GitHub)
- cricket/models.py
  - Added `Player` metadata fields: `batting_order`, `batting_category`, `bowling_role`.
- cricket/migrations/0002_*.py
  - Migration for the above `Player` fields.
- cricket/views.py
  - Wicket auto-replacement: after a wicket, selects the next not-out batter ordered by `batting_order`.
- cricket/scoring.py
  - Updated strike rotation logic (odd-runs swap + end-of-over swap on legal delivery).
- static/js/cricket-scoring.js
  - Updated wicket modal + striker/non-striker/bowler selection handling and state refresh.

## Pending (not yet pushed / still TODO)
- cricket/views.py / scoring flow
  - Initial auto-selection of striker/non-striker based on `batting_order` (current state still relies on UI/manual selection).
  - Sort bowling lists by role/category and surface role in UI.
- Templates/UI
  - Templates/cricket_match_detail.html: striker big/small stats + compact bowling over/wickets/maidens formatting.
  - Templates/create_cricket_match.html: collect batting order/category inputs for players.
- Styling
  - static/css/cricket.css updates for the new UI.
- Verification
  - Run `makemigrations` / `migrate` (if not already) and do a live test: strike swap at over end + 1/3 logic + wicket replacement order.

