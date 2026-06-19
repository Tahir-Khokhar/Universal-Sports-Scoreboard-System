# Universal Sports Scoreboard — Cricket Scoring TODO

> Goal: make live cricket scoring feel complete (correct striker logic, wicket handling, and a clean match UI) and then prepare everything for a GitHub push.

---

## 1) ✅ Already implemented (in the current repo)

### Backend (Django)
- **Player meta fields**
  - `cricket/models.py`: `batting_order`, `batting_category` (top/middle/lower), `bowling_role` (bowler/allrounder)
- **Migrations**
  - `cricket/migrations/0002_*.py`: migration for the above fields
- **Wicket replacement logic**
  - `cricket/views.py` (`add_ball_score`): after a wicket, the next batter is selected automatically using `batting_order` among not-out batters.

### Scoring rules
- **Strike rotation**
  - `cricket/scoring.py`: swap on **odd runs** (legal delivery) and at **end of over**.

### Frontend (JS)
- **Live scoring controller updates**
  - `static/js/cricket-scoring.js`: wicket modal flow and state refresh with `striker_id` / `non_striker_id` / `bowler_id`.

---

## 2) 🔜 Next (must do before calling it “complete”)

### A) Auto-select striker / non-striker by batting order
- `cricket/views.py` / `build_match_state`: ensure initial striker & non-striker are set automatically based on `batting_order` when an innings starts.
- `static/js/cricket-scoring.js`: ensure UI selection is overridden only when backend returns updated striker/non-striker.

### B) Bowling list correctness (role/category)
- `cricket/views.py`: sort `bowling_players` based on batting-team bowler role/category rules.
- `Templates/cricket_match_detail.html` (and/or scoreboard template): show:
  - bowlers + all-rounders split (or role tag)
  - compact over line (e.g. `overs-wkts-maidens`)

---

## 3) 🎨 UI/Template improvements

### A) Match detail UI
- `Templates/cricket_match_detail.html`
  - striker block: big runs + balls faced
  - wicket indicators
  - compact bowling summary formatting

### B) Team/player creation UI
- `Templates/create_cricket_match.html`
  - add inputs for:
    - batting order (1..11)
    - batting category (top/middle/lower)
    - bowling role (bowler/allrounder)

### C) Styling
- `static/css/cricket.css`
  - make typography reflect striker vs other batters
  - compact over/wickets line styling

---

## 4) 🧪 Verification checklist (run and confirm)
- [ ] `python manage.py makemigrations`
- [ ] `python manage.py migrate`
- [ ] Live test: over-end strike swap works (after 6 legal balls)
- [ ] Live test: strike swap on odd runs (1/3/5)
- [ ] Live test: wicket replacement picks next not-out batter by `batting_order`
- [ ] Live test: wides/no-balls do not incorrectly trigger legal-ball rotations
- [ ] Regression: match end + innings transition still behaves correctly

---

## 5) 📦 GitHub push items
When this TODO is ready, push these key files (already changed):
- `cricket/models.py`
- `cricket/migrations/0002_*.py`
- `cricket/views.py`
- `cricket/scoring.py`
- `static/js/cricket-scoring.js`

Then add the remaining pending UI/CSS/template commits.

