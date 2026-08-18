# Project Chronos — Live Sprint Kanban Board

**Current Sprint:** Sprint 1 — Project Foundation & Adaptive Engine Core  
**Sprint Status:** `PLANNED / READY TO START`  
**Sprint Goal:** Menyiapkan arsitektur project backend, skema database, isolated Adaptive Engine (step sizing, feasibility, tolerance matrix), dan test suite TDD 100% green.  
**Last Updated:** 18 August 2026  

---

## 📊 Ringkasan Metrik Sprint 1

| Metrik | Nilai |
| :--- | :--- |
| **Total Story Points / Tasks** | 6 Tasks |
| **Completed (DONE)** | 0 Tasks (0%) |
| **In QA / Testing** | 0 Tasks |
| **In Progress** | 0 Tasks |
| **To Do (Ready for Dev)** | 6 Tasks (100%) |

---

## 📌 Papan Kanban Sprint 1 (Trello / Jira Style)

```text
+---------------------+---------------------+---------------------+---------------------+
| SPRINT TODO (6)     | IN PROGRESS (0)     | IN QA (0)           | DONE (0)            |
+---------------------+---------------------+---------------------+---------------------+
| [TASK-01] Backend   |                     |                     |                     |
| Scaffold & Config   |                     |                     |                     |
|                     |                     |                     |                     |
| [TASK-02] Data      |                     |                     |                     |
| Schema & Models     |                     |                     |                     |
|                     |                     |                     |                     |
| [TASK-03] Feasibi-  |                     |                     |                     |
| lity Calculator     |                     |                     |                     |
|                     |                     |                     |                     |
| [TASK-04] Dynamic   |                     |                     |                     |
| Step Sizing Engine  |                     |                     |                     |
|                     |                     |                     |                     |
| [TASK-05] Collision |                     |                     |                     |
| Resolver & Budget   |                     |                     |                     |
|                     |                     |                     |                     |
| [TASK-06] Engine    |                     |                     |                     |
| Test Suite (TDD)    |                     |                     |                     |
+---------------------+---------------------+---------------------+---------------------+
```

---

## 📋 Kartu Detail Task Sprint 1

### [TASK-01] Backend Project Scaffold & Strict Type Config
- **Assignee**: Backend Engineer Agent
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Struktur folder backend modular (`controllers/`, `services/`, `engine/`, `models/`).
  - Strict linting, dependency manifest tanpa package usang.
  - Health check endpoint `/health` aktif.

### [TASK-02] Core Data Schema & Entity Models
- **Assignee**: Backend & Database Engineer Agent
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Model entitas: `User`, `UserConstraint`, `FinancialProfile`, `TransitionRoadmap`, `DailyPlan`, `PlanItem`, `ExecutionLog`, `DailyEvaluation`.
  - Type-safe schema validation (Pydantic / Zod / SQLAlchemy / Prisma).

### [TASK-03] Feasibility Assessment Calculator
- **Assignee**: Backend Engineer (Adaptive Engine Specialist)
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Implementasi rumus: $\Delta T_{\text{total}} / 7.5 \text{ min/day}$.
  - Mengembalikan validasi kelayakan atau saran penyesuaian durasi.

### [TASK-04] Dynamic Step Sizing & Tolerance State Machine
- **Assignee**: Backend Engineer (Adaptive Engine Specialist)
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Implementasi ambang toleransi ($\le$20m, 21-45m, 46-90m, >90m).
  - Aksi transisi: `ADVANCE_STEP`, `MAINTAIN_STEP`, `HOLD_TARGET`, `REDUCE_STEP_SIZE`, `ENTER_RECOVERY`.

### [TASK-05] Schedule Collision Resolver & Budget Re-balancer
- **Assignee**: Backend Engineer (Adaptive Engine Specialist)
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Validasi jadwal tidak bertabrakan dengan `UserConstraints`.
  - Rumus penyeimbangan sisa anggaran harian jika ada overspend/underspend.

### [TASK-06] Comprehensive Unit Test Suite (TDD 100% Green)
- **Assignee**: QA Tester & Security Auditor Agent
- **Status**: `SPRINT_TODO`
- **Worktree**: `.worktrees/feat-backend-engine/Backend`
- **Definition of Done (DoD)**:
  - Test suite unit mencakup: *Feasibility rejection*, *Midnight rollover*, *2x Missed hold*, *Zero app open*, *Budget cap update*.
  - Anti-slop zero error & zero emoji verification.
