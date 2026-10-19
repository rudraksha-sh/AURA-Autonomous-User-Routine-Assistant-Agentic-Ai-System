# Frontend feature roadmap

Plan recorded after reviewing the current App Router pages, shared components, services, and response types. Each phase gets its own checkpoint, frontend lint/build run, fixes, and commit. Backend work is included where the requested UX needs persistent or server-owned data.

| Phase | Expected touch points | Status |
| --- | --- | --- |
| 1. Dashboard | `app/(private)/dashboard/page.tsx`, `components/dashboard/*`, `app/globals.css` | Implemented; lint and build passed |
| 2. Kanban tasks | tasks page, task service/types, task API/model/migrations/tests for bulk, subtasks and history | Planned |
| 3. Calendar views | planner pages/components, planner services/types, schedule APIs for custom slots and conflicts | Planned |
| 4. Assistant chat | assistant page/components, assistant services/types, conversation model/migration/routes/tests, voice panel | Planned |
| 5. Notifications and inbox | Header, dashboard and notifications page, services/types, notification and Gmail APIs/models/migrations/tests | Planned |
| 6. Goal detail | goal detail/form/services/types, goal APIs and migrations/tests for templates/archive/duplicate as needed | Planned |
| 7. Global UX | private layout, navigation, command palette, quick add, shortcuts, toast and theme services | Planned |
| 8. Settings | settings page/components/services/types, profile/integration/security/export APIs and migrations/tests | Planned |
| 9. Insights | insights page/components/services/types, completion/time tracking and review APIs/models/migrations/tests | Planned |
| 10. Public pages | landing/auth/onboarding pages, app metadata/assets, error pages, PWA files and Playwright coverage | Planned |

## Phase status

### Phase 1: Dashboard

Implemented: daily workload summary, active-goal progress rings, weekly completion chart, next-action card, streak and 12-week activity heatmap, plus a first-goal call to action. Completion activity uses the existing task `updated_at` timestamp because the API does not expose a dedicated `completed_at` field. The next-action rank is a client-side estimate from priority, deadline, goal priority, and effort because the API does not expose a score yet. Reduced-motion preferences are respected.

Verification: `npm.cmd run lint` passed; `npm.cmd run build` passed.
