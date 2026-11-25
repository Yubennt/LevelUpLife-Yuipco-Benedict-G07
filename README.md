# LevelUp Life: A Gamified Habit and Goal Tracking System

Software Design Document: *LevelUp Life SDD v2*. Student: Yuipco, Benedict E. · CSIT327 · Section G7.

This repository holds the **Account feature** (F-01 Registration and Authentication, F-02 Profile Management,
F-11 Account Administration), the `users` and `levels` tables, and role-based dashboards, built to the SDD.
Habits, completions, streaks, badges, notifications and analytics (F-03 to F-10, F-12 in full) come in later sprints.

**Stack:** Django (server-rendered templates) · PostgreSQL, with Supabase used only as hosted PostgreSQL ·
Django's built-in authentication with a custom user model (Supabase Auth is **not** used) · Django Admin for administrators.

## What follows the SDD
| SDD item | Implementation |
|---|---|
| `users` table (4.3) | `accounts.User`, `db_table="users"`. Email is `USERNAME_FIELD`; username/first/last name removed. Has `display_name`, `personal_goal`, `time_zone`, `reminders_enabled`, `total_xp` (CHECK >= 0), `current_level` FK to `levels.level_number` |
| `levels` table, BR-19 | `gamification.Level`, seeded by data migration with `xp_required = 50 * n * (n - 1)` (0, 100, 300, 600 ...), levels 1 to 100 |
| BR-19 / BR-20 | `User.save()` recalculates `current_level` whenever `total_xp` is saved |
| BR-01 | Case-insensitive unique email: form check, lowercase on save, and a database `UniqueConstraint(Lower('email'))` |
| BR-02 | Hashed with Django's hashers. Minimum 8 characters plus `LetterAndNumberValidator` (a letter and a number) |
| BR-03 | `django-axes`: 5 consecutive failures locks the account for 15 minutes (counted per email, case-insensitive); a success resets the count |
| BR-04 | Administrators are `is_staff = true`. Only staff can open Django Admin (`/django-admin/`) and the admin dashboard |
| BR-05 | Deactivated accounts (`is_active = false`) cannot log in; their data is kept |
| BR-06 | Profile URLs contain no user id, so users only ever see and edit their own profile |
| BR-31 | Account deactivate/reactivate admin actions write to the Django admin log (`LogEntry`) |
| F-02 | Users edit display name, personal goal, time zone and reminder preference; the time zone is activated per request |
| F-11 / F-12 (partial) | Django Admin user management; admin dashboard shows health indicators and a level-vs-XP integrity check |

Two dashboards satisfy the course's role-based requirement: `/dashboard/user/` for regular users and
`/dashboard/admin/` for staff. `/dashboard/` sends each person to theirs, and opening the other one redirects back with an error message.

**Notes**
- `CommonPasswordValidator` stays enabled. It is stricter than BR-02 requires.
- BR-03 locks the *account*, so someone could deliberately trigger a 15-minute lock on another person's email. This is the SDD's rule; adding `ip_address` to `AXES_LOCKOUT_PARAMETERS` in `settings.py` would soften it.
- The SDD's profile has no contact number or photo, so those are not included.

## Setup
```bash
git clone https://github.com/<your-username>/LevelUpLife-Yuipco-Benedict-G7.git
cd LevelUpLife-Yuipco-Benedict-G7
python -m venv venv
venv\Scripts\activate            # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env           # macOS/Linux: cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY and DATABASE_URL (local PostgreSQL or Supabase)

python manage.py migrate         # also creates and seeds the levels table
python manage.py createsuperuser # asks for email, display name, password; superusers are staff/admins
python manage.py runserver
```
Open http://127.0.0.1:8000/. To make another administrator, tick **Staff status** on the user in Django Admin.

### Database
Set `DATABASE_URL` in `.env`. SQLite is intentionally rejected.
- **Local PostgreSQL:** create a database named `levelup_life`, then `postgresql://postgres:<password>@localhost:5432/levelup_life`
- **Supabase:** Project Settings > Database > Connection string (URI), keep `?sslmode=require`. Use it only as PostgreSQL.

### Tests
```bash
python manage.py test
```

## Layout
```
levelup_life/   settings and root urls
accounts/       User model, forms, validators, timezone middleware, register/login/logout/profile, Django Admin setup
gamification/   Level model + seed migration, level/XP progress service (badges and streaks come later)
dashboard/      landing page, role router, user and admin dashboards
templates/      Django templates      static/css/   stylesheet
```
# Habit Management Feature 
