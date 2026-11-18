from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from gamification.models import Level

User = get_user_model()
PW = "Str0ng-pass-123"


def make_user(email="player@example.com", **kw):
    kw.setdefault("display_name", "Player One")
    return User.objects.create_user(email=email, password=PW, **kw)


def make_admin(email="boss@example.com"):
    return User.objects.create_user(email=email, password=PW, display_name="Boss", is_staff=True)


class LevelTableTests(TestCase):
    def test_seed_follows_br19_formula(self):
        got = {l.level_number: l.xp_required for l in Level.objects.filter(level_number__lte=4)}
        self.assertEqual(got, {1: 0, 2: 100, 3: 300, 4: 600})
        self.assertTrue(all(l.xp_required == 50 * l.level_number * (l.level_number - 1) for l in Level.objects.all()))

    def test_level_recalculated_when_xp_saved(self):
        u = make_user()
        self.assertEqual(u.current_level_id, 1)
        for xp, lvl in [(99, 1), (100, 2), (299, 2), (300, 3), (600, 4)]:
            u.total_xp = xp
            u.save()
            u.refresh_from_db()
            self.assertEqual(u.current_level_id, lvl, xp)

    def test_total_xp_cannot_be_negative(self):
        u = make_user()
        u.total_xp = -5
        with self.assertRaises(IntegrityError), transaction.atomic():
            u.save()


class RegistrationTests(TestCase):
    data = {"email": "New@Example.com", "display_name": "Newbie", "password1": PW, "password2": PW}

    def test_success_hashes_password_and_creates_regular_user(self):
        r = self.client.post(reverse("register"), self.data, follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertContains(r, "Account created")
        u = User.objects.get(email="new@example.com")
        self.assertFalse(u.is_staff)
        self.assertEqual((u.time_zone, u.reminders_enabled, u.total_xp, u.current_level_id), ("UTC", True, 0, 1))
        self.assertTrue(u.password.startswith("pbkdf2_"))
        self.assertNotIn(PW, u.password)

    def test_cannot_self_register_as_staff(self):
        self.client.post(reverse("register"), {**self.data, "is_staff": "on", "is_superuser": "on"})
        u = User.objects.get(email="new@example.com")
        self.assertFalse(u.is_staff or u.is_superuser)

    def test_required_fields_and_invalid_email(self):
        r = self.client.post(reverse("register"), {})
        for f in ("email", "display_name", "password1", "password2"):
            self.assertIn(f, r.context["form"].errors)
        r = self.client.post(reverse("register"), {**self.data, "email": "nope"})
        self.assertIn("email", r.context["form"].errors)

    def test_br01_duplicate_email_case_insensitive(self):
        make_user("taken@example.com")
        r = self.client.post(reverse("register"), {**self.data, "email": "TAKEN@Example.com"})
        self.assertIn("email", r.context["form"].errors)

    def test_br01_enforced_by_database_even_without_form(self):
        User.objects.bulk_create([User(email="Dup@Example.com", display_name="A", password="x")])  # skips save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="dup@example.com", display_name="B", password="x")

    def test_password_mismatch(self):
        r = self.client.post(reverse("register"), {**self.data, "password2": "Different-1pass"})
        self.assertIn("password2", r.context["form"].errors)

    def test_br02_password_rules(self):
        for bad in ("Ab1", "abcdefghij", "12345678901", "Abcdef-ghij"):  # short / no digit / no letter / no digit
            with self.assertRaises(ValidationError, msg=bad):
                validate_password(bad)
        validate_password("Zebra-quartz-49")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def login(self, email="player@example.com", password=PW):
        return self.client.post(reverse("login"), {"username": email, "password": password})

    def test_login_with_email_case_insensitive(self):
        r = self.login("PLAYER@Example.com")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_credentials_show_error(self):
        r = self.login(password="wrong")
        self.assertContains(r, "Incorrect email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_br03_lockout_after_5_failures(self):
        for _ in range(4):
            self.assertContains(self.login(password="wrong"), "Incorrect email or password")
        self.login(password="wrong")  # 5th failure locks the account
        r = self.login()  # even the correct password is refused now
        self.assertContains(r, "temporarily locked", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_br03_lock_lifts_after_15_minutes(self):
        from datetime import timedelta

        from axes.models import AccessAttempt
        from django.utils import timezone

        for _ in range(5):
            self.login(password="wrong")
        self.assertContains(self.login(), "temporarily locked", status_code=429)
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=14))
        self.assertContains(self.login(), "temporarily locked", status_code=429)  # still locked at 14 min
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.login().status_code, 302)  # unlocked after 15 min

    def test_br03_lockout_ignores_email_case(self):
        for e in ["player@example.com", "PLAYER@example.com", "Player@Example.com", "player@EXAMPLE.com", "PLAYER@EXAMPLE.COM"]:
            self.login(e, "wrong")
        self.assertContains(self.login(), "temporarily locked", status_code=429)

    def test_br03_consecutive_only(self):
        for _ in range(3):
            self.login(password="wrong")
        self.assertEqual(self.login().status_code, 302)  # success resets the counter
        self.client.post(reverse("logout"))
        for _ in range(3):
            self.login(password="wrong")
        self.assertEqual(self.login().status_code, 302)

    def test_br05_deactivated_account_cannot_log_in_and_data_retained(self):
        self.user.is_active = False
        self.user.save()
        self.assertContains(self.login(), "Incorrect email or password")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_logout_ends_session(self):
        self.login()
        r = self.client.post(reverse("logout"), follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(r, "logged out")
        self.login()
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_protected_pages_redirect_to_login(self):
        for name in ("dashboard", "user_dashboard", "admin_dashboard", "profile", "profile_edit", "password_change"):
            url = reverse(name)
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}", msg_prefix=name)


class RoleDashboardTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.admin = make_admin()

    def test_login_redirects_to_own_dashboard(self):
        r = self.client.post(reverse("login"), {"username": "player@example.com", "password": PW}, follow=True)
        self.assertRedirects(r, reverse("user_dashboard"))
        self.client.logout()
        r = self.client.post(reverse("login"), {"username": "boss@example.com", "password": PW}, follow=True)
        self.assertRedirects(r, reverse("admin_dashboard"))

    def test_user_cannot_open_admin_dashboard(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("admin_dashboard"), follow=True)
        self.assertRedirects(r, reverse("user_dashboard"))
        self.assertContains(r, "have access")

    def test_admin_cannot_open_user_dashboard(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("user_dashboard")), reverse("dashboard"), target_status_code=302)

    def test_dashboard_content_fits_role(self):
        self.user.total_xp = 150
        self.user.save()
        self.client.force_login(self.user)
        r = self.client.get(reverse("user_dashboard"))
        self.assertContains(r, "Today's habits")
        self.assertContains(r, "Apprentice")
        self.assertNotContains(r, "Data integrity")
        self.assertNotContains(r, "Django admin")
        self.client.force_login(self.admin)
        r = self.client.get(reverse("admin_dashboard"))
        self.assertContains(r, "Data integrity")
        self.assertContains(r, "Django admin")

    def test_integrity_check_detects_level_mismatch(self):
        User.objects.filter(pk=self.user.pk).update(total_xp=500)  # bypasses save(), level stays 1
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin_dashboard")), "1 user(s) have a level that does not match")


class DjangoAdminTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.admin = make_admin()

    def test_br04_only_staff_reach_admin_site(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/django-admin/login/", r["Location"])

    def test_staff_without_permissions_see_no_user_data(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_changelist")).status_code, 403)

    def test_br31_deactivate_and_reactivate_are_logged(self):
        su = User.objects.create_superuser("root@example.com", PW, display_name="Root")
        self.assertTrue(su.is_staff)
        self.client.force_login(su)
        url = reverse("admin:accounts_user_changelist")
        self.client.post(url, {"action": "deactivate_accounts", "_selected_action": [self.user.pk, su.pk]})
        self.user.refresh_from_db(); su.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(su.is_active)  # an admin cannot deactivate themselves by accident
        entry = LogEntry.objects.get(object_id=str(self.user.pk))
        self.assertEqual((entry.user_id, entry.change_message), (su.pk, "Deactivated account"))
        self.client.post(url, {"action": "reactivate_accounts", "_selected_action": [self.user.pk]})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(LogEntry.objects.filter(object_id=str(self.user.pk)).count(), 2)

    def test_admin_pages_render(self):
        su = User.objects.create_superuser("root@example.com", PW, display_name="Root")
        self.client.force_login(su)
        for name, args in [("admin:accounts_user_add", ()), ("admin:accounts_user_change", (self.user.pk,)),
                           ("admin:gamification_level_changelist", ())]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)
        r = self.client.post(reverse("admin:accounts_user_add"), {
            "email": "Made@Example.com", "display_name": "Made", "password1": PW, "password2": PW})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(email="made@example.com").exists())


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("other@example.com", display_name="Other Person")
        self.client.force_login(self.user)

    def test_view_own_profile_only(self):
        r = self.client.get(reverse("profile"))
        self.assertContains(r, "player@example.com")
        self.assertNotContains(r, "other@example.com")

    def test_update_profile(self):
        r = self.client.post(reverse("profile_edit"), {
            "display_name": "Pat", "personal_goal": "Run a 5K", "time_zone": "Asia/Manila"}, follow=True)
        self.assertRedirects(r, reverse("profile"))
        self.assertContains(r, "Profile updated")
        self.user.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual((self.user.display_name, self.user.personal_goal, self.user.time_zone, self.user.reminders_enabled),
                         ("Pat", "Run a 5K", "Asia/Manila", False))  # unchecked box = reminders off
        self.assertEqual(self.other.display_name, "Other Person")

    def test_validation(self):
        base = {"display_name": "Pat", "time_zone": "UTC"}
        for bad, field in [({"display_name": ""}, "display_name"), ({"display_name": "x" * 51}, "display_name"),
                           ({"time_zone": "Mars/Base"}, "time_zone")]:
            r = self.client.post(reverse("profile_edit"), {**base, **bad})
            self.assertIn(field, r.context["form"].errors)

    def test_email_staff_flag_and_xp_cannot_be_changed_via_profile(self):
        self.client.post(reverse("profile_edit"), {
            "display_name": "Pat", "time_zone": "UTC", "email": "hacked@example.com",
            "is_staff": "on", "total_xp": "9999", "is_active": ""})
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.is_staff, self.user.total_xp, self.user.is_active),
                         ("player@example.com", False, 0, True))

    def test_user_timezone_is_activated(self):
        self.user.time_zone = "Asia/Manila"
        self.user.save()
        self.client.get(reverse("profile"))
        from django.utils import timezone
        self.assertEqual(str(timezone.get_current_timezone()), "Asia/Manila")
