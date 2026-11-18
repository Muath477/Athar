# الأدوار والصلاحيات والحوكمة · Roles, permissions and governance

Written 2026-11-20. Source of truth: `ROLE_PERMISSIONS` in `backend/src/sadu/modules/admin/api.py`. The dashboard reads the same matrix from `GET /api/v1/auth/roles`, so this page and the UI cannot drift from the code without a test failing (`test_each_role_gets_only_its_own_permissions`).

## 1. الأدوار · Roles

| الدور | Role | Who it is for |
|---|---|---|
| المساح الميداني | `inspector` | Field surveyor who photographs walls and creates draft damage maps. |
| مدير الموقع | `site_manager` | Runs one or more sites: photography permits, devices, periodic condition report. |
| أخصائي الترميم | `expert` | Conservation specialist who reviews, corrects and approves maps and visitor findings. |
| ممثل هيئة التراث | `authority` | Heritage Commission or Diriyah Gate officer: oversight, reports and the audit trail, read-only on the record. |
| مهندس النماذج | `ml_engineer` | Looks after the analysis models and their accuracy. |
| مسؤول النظام | `admin` | Manages accounts, roles, site scope and retention. Holds every permission. |

## 2. مصفوفة الصلاحيات · Permission matrix

| الصلاحية · Permission | inspector | site_manager | expert | authority | ml_engineer | admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| الاطلاع على المواقع والمخططات · `read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| تصوير الجدران وإنشاء المخططات · `survey` | ✓ | | ✓ | | | ✓ |
| مراجعة المخططات واعتمادها · `review` | | | ✓ | | | ✓ |
| إدارة الموقع وتصاريح التصوير · `manage_site` | | ✓ | | | | ✓ |
| إدارة الكاميرات والأجهزة · `manage_devices` | | ✓ | | | | ✓ |
| تصدير التقارير والجداول · `export` | | ✓ | ✓ | ✓ | ✓ | ✓ |
| استخدام مساعد أثر · `assistant` | ✓ | ✓ | ✓ | ✓ | | ✓ |
| إدارة نماذج التحليل · `manage_models` | | | | | ✓ | ✓ |
| قراءة سجل التدقيق · `read_audit` | | | | ✓ | | ✓ |
| إدارة الحسابات والصلاحيات · `administer` | | | | | | ✓ |

Every staff route declares one of the dependencies in `admin/interface/auth.py` (`Staff`, `Inspector`, `Expert`, `SiteManager`, `DeviceManager`, `Exporter`, `AssistantUser`, `ModelManager`, `AuditReader`, `AuditExporter`, `Admin`) or is explicitly `public`. Access is denied by default.

## 3. الشاشات · Screens

| الشاشة · Screen | Path | Shown to |
|---|---|---|
| الموقع ثلاثي الأبعاد، حالة الموقع، الرصد من الفضاء، المخططات | `/dashboard`, `/dashboard/condition`, `/dashboard/watch`, `/dashboard/maps` | Everyone signed in (`read`), limited to their sites |
| مخطط جديد | `/dashboard/maps/new` | `survey` |
| قائمة المراجعة، تعديل العناصر، الفحص الميداني، الاعتماد | `/dashboard/review`, `/dashboard/maps/{id}` | `review` |
| تصريح التصوير الميداني (في حالة الموقع) | `/dashboard/condition` | `manage_site` |
| تنزيل التقرير PDF والجدول CSV (في حالة الموقع) | `/dashboard/condition` | `export` |
| الحسابات والصلاحيات | `/dashboard/users` | `administer` |
| سجل التدقيق، وتنزيله CSV | `/dashboard/audit` | `read_audit`; the CSV also needs `export` |
| تغيير كلمة المرور | `/dashboard/password` | Every signed-in user; forced after a temporary password |

The navigation hides sections the user cannot open, and each page shows a plain message if opened directly. The API enforces the same rule; hiding a link is only convenience.

## 4. نقاط النهاية · Endpoints

| Permission | Endpoints (prefix `/api/v1`) |
|---|---|
| signed in, any role | `GET /auth/me`, `POST /auth/password` |
| `read` | `GET /sites`, `/sites/{id}/condition`, `/sites/{id}/coverage`, `/sites/{id}/pins`, `/maps`, `/maps/{id}`, `/maps/accuracy`, `/maps/glossary`, `/maps/{id}/report.pdf`, `/missions`, `/watch/sites`, `/watch/sites/{id}/scans`, `/findings/{id}`, `/treatments/catalog`, `/auth/roles` |
| `survey` | `POST /maps`, `/missions`, `/watch/sites/{id}/scans`, `/watch/scans/{id}/ground-check` |
| `review` | `GET /review-queue`; `POST /maps/{id}/cells`, `/maps/{id}/elements`, `/maps/{id}/field-inspection`, `/maps/{id}/approve`, `/findings/{id}/review`, `/watch/scans/{id}/acknowledge` |
| `manage_site` | `POST /sites/{id}/field-photography` |
| `export` | `GET /sites/{id}/condition.csv`, `/sites/{id}/condition.pdf`, `/maps/{id}/elements.csv` |
| `read_audit` | `GET /admin/audit` (filters `actor`, `action` prefix, `target_type`, `from`, `to`, `page`, `page_size`) |
| `read_audit` + `export` | `GET /admin/audit.csv` (same filters, up to 10,000 rows) |
| `administer` | `GET/POST /admin/users`, `POST /admin/users/{id}/role`, `/sites`, `/active`, `/password`; `POST /admin/retention/run`; `GET /admin/costs` |
| public | `POST /auth/login`, `/auth/logout`, visitor endpoints (`/sites/nearby`, `/sites/{id}`, `/facades/{id}/baseline`, `/missions/nearby`, observations, stories, passport) |

CSV files start with a UTF-8 byte order mark so Excel shows Arabic correctly, and any cell that starts with `=`, `+`, `-` or `@` is prefixed with `'` so a wall name cannot become a spreadsheet formula.

## 5. نطاق المواقع · Site scope

- An admin can limit an account to chosen sites (`user_sites` table, `POST /admin/users/{id}/sites`).
- An empty list means every site, so existing accounts keep working unchanged.
- `admin` and `authority` always see every site, whatever is assigned to them.
- A resource outside the user's scope answers **404 `not_found`**, the same as a resource that does not exist, so a scoped user cannot learn which other sites or maps exist.
- Enforced on: site list, condition (JSON, CSV, PDF), coverage, field-photography permit, map list, map detail, map create, cell corrections, element edits, field inspection, approval, wall report PDF, elements CSV, map accuracy filter, mission list and create, satellite overview, site scans, scan now, acknowledge and ground check.
- Maps drawn for a free-standing wall with no site stay visible to every account with `read`.
- Not yet scoped: `GET /sites/{id}` (public, the visitor app needs it), the visitor review queue, finding detail and site pins. Visitor findings carry no sensitive data beyond what the public site page shows; scoping them is the next step for a multi-authority pilot.

## 6. دورة حياة الحساب · Account lifecycle

1. The admin creates the account with an email, display name, role, optional sites and a temporary password of at least 12 characters (the same policy as the `sadu create-user` command). The response never contains a password or hash.
2. On first sign-in the account is flagged `must_change_password`; every permission-checked route answers 403 `password_change_required` until the user sets a new password at `/dashboard/password`.
3. Changing a role or sites takes effect on the user's next request, because the role and sites are read with the session on each request.
4. Deactivating an account deletes all its sessions at once and refuses later sign-ins with `account_disabled`. Reactivating lets it sign in again.
5. A password reset sets a new temporary password, clears any lockout, ends all sessions and forces a change on next sign-in.
6. An admin cannot change their own role or deactivate themselves (409 `own_account`), so the last admin cannot lock everyone out by mistake.
7. The user list shows the last successful sign-in time for each account.

## 7. سجل التدقيق · Audit coverage

Each row stores the actor (or none for the system), action, target type and id, details and the request id.

| Action | المعنى |
|---|---|
| `login` | تسجيل دخول |
| `user.create`, `user.role`, `user.sites`, `user.deactivate`, `user.reactivate`, `user.password_reset`, `user.password_change` | إدارة الحسابات |
| `map.create`, `map.correct`, `map.edit_elements`, `map.field_inspection`, `map.approve` | دورة المخطط من الإنشاء إلى الاعتماد |
| `finding.confirm`, `finding.correct`, `finding.reject` | مراجعة ملاحظات الزوار |
| `site.field_photography` | تغيير تصريح التصوير |
| `mission.create` | فتح مهمة تصوير |
| `watch.scan`, `watch.acknowledge`, `watch.ground_check` | الرصد من الفضاء |
| `passport.delete` | حذف جواز زائر وصوره |
| `retention.purge` | حذف صور انتهت مدة حفظها |
| `notice.map_urgent`, `notice.approval_overdue` | إشعارات الحوكمة المرسلة |

The authority reads the trail but cannot change it; there is no endpoint that edits or deletes audit rows.

## 8. حفظ الصور · Retention

- Visitor photos are kept 30 days (`delete_after`). A photo that became evidence for a finding is kept two years.
- A background loop deletes expired observation rows and their stored objects (the photo and the inspection's aligned and difference images) every `SADU_RETENTION_INTERVAL_H` hours (default 24; `0` turns it off). Each run handles up to 1,000 photos.
- An admin can run it at once with `POST /admin/retention/run`; the answer gives the number of photos and stored files removed.
- Every run that deletes something, and every manual run, is audited as `retention.purge` with the counts and whether the schedule or an admin started it.

## 9. الإشعارات · Governance notices

Notices go to the same HTTPS webhook as satellite alerts (`SADU_ALERT_WEBHOOK_URL`); without it they only appear in the audit trail.

- **تلف عاجل:** the first time a map holds urgent elements (on creation, cell correction or element edit), one notice with the wall name, urgent count and dashboard link.
- **اعتماد متأخر:** an hourly check sends one reminder for each draft map waiting longer than `SADU_APPROVAL_OVERDUE_DAYS` days (default 7; `0` turns it off).

Each notice is recorded as an audit row first, which also stops it being sent twice. A failing webhook is logged and never blocks the request or the loop.
