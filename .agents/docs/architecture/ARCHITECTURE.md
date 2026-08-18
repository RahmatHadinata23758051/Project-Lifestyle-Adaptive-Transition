# Project Chronos — System Architecture & Technical Design

**Document Version:** 1.0.0  
**Status:** Architectural Blueprint  
**Reference Document:** [`PRD.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/prd/PRD.md)  
**System Category:** Adaptive Lifestyle Transition Engine & Mobile Companion  

---

## 1. High-Level System Architecture

Project Chronos beroperasi menggunakan arsitektur **Client-Server Event-Driven Closed-Loop System**. Arsitektur ini dirancang untuk memproses siklus hidup pengguna secara adaptif: dari Assessment, Roadmap Generation, Daily Plan Scheduling, Frictionless Tracking, hingga Dynamic Plan Adaptation.

```mermaid
graph TD
    subgraph Mobile_App [Mobile Client - Mobile First & Offline First]
        UI[UI / UX Layer]
        LocalDB[(Local SQLite / WatermelonDB)]
        SyncEngine[Sync Engine]
        QuickCheckin[Quick Check-in Widget]
    end

    subgraph Backend_Services [Backend Core Services]
        Gateway[API Gateway / Auth]
        UserService[User & Profile Service]
        ConstraintEngine[Schedule & Budget Constraint Service]
        AdaptiveEngine[Adaptive Transition Engine]
        PlannerService[Daily Plan Generator Service]
        EvaluationWorker[Daily Evaluation & Adaptation Worker]
    end

    subgraph Data_Storage [Persistent Storage & Cache]
        MainDB[(PostgreSQL - Primary DB)]
        Cache[(Redis - Caching & Job Queues)]
    end

    UI --> LocalDB
    LocalDB --> SyncEngine
    SyncEngine <--> Gateway
    Gateway --> UserService
    Gateway --> PlannerService
    Gateway --> AdaptiveEngine
    
    PlannerService --> ConstraintEngine
    PlannerService --> MainDB
    AdaptiveEngine --> MainDB
    AdaptiveEngine --> Cache
    EvaluationWorker --> AdaptiveEngine
```

---

## 2. Core Architectural Components

### 2.1 Mobile Client Architecture (Mobile-First)
- **Offline-First & Local Cache**: Seluruh daily plan di-cache di local storage perangkat (e.g. SQLite / WatermelonDB). User dapat melakukan check-in dan melihat plan tanpa ketergantungan koneksi internet real-time.
- **Frictionless Quick Check-in**:
  - Durasi interaksi ditargetkan **< 10 detik** ("Open -> Understand -> Check-in -> Close").
  - Optimistic UI updates untuk setiap status tugas (Tidur, Bangun, Makan, Olahraga).
- **Timezone & Local Alarm Sync**: Menyesuaikan reminder harian dan target waktu (misal: waktu tidur 02.45, bangun 09.30) dengan timezone lokal perangkat pengguna.

### 2.2 Adaptive Transition Engine (Core Brain)
Komponen ini adalah pembeda utama Chronos dibandingkan habit tracker konvensional.
- **Baseline Ingestion**: Membaca Current Self (baseline tidur, bangun, frekuensi makan, pengeluaran).
- **Feasibility Evaluator**: Menilai apakah durasi yang diminta (misal: 4 minggu) realistis untuk melompat dari kondisi awal ke target. Jika terlalu curam, sistem menyarankan penyesuaian durasi atau membaginya ke dalam beberapa fase (Step Sizing).
- **Closed-Loop Adaptation Controller**:
  - Menerima hasil tracking harian (`SUCCESS`, `WITHIN_TOLERANCE`, `MISSED`, `SIGNIFICANT_MISS`).
  - Mengambil keputusan adaptasi: `CONTINUE_PROGRESSION`, `HOLD_TARGET`, `REDUCE_STEP_SIZE`, `REDUCE_DAILY_LOAD`, atau `ENTER_RECOVERY`.
- **Constraint Matrix Resolver**: Memastikan rencana tidak pernah bertabrakan dengan jadwal wajib (Kuliah/Kerja/Commute) dan tidak melebihi alokasi budget harian.

---

## 3. Data Model & Schema Design

```mermaid
erDiagram
    USERS ||--o{ USER_CONSTRAINTS : has
    USERS ||--o{ FINANCIAL_PROFILES : has
    USERS ||--o{ TRANSITION_ROADMAPS : creates
    TRANSITION_ROADMAPS ||--o{ TRANSITION_PHASES : contains
    TRANSITION_PHASES ||--o{ DAILY_PLANS : generates
    DAILY_PLANS ||--o{ PLAN_ITEMS : contains
    PLAN_ITEMS ||--o{ EXECUTION_LOGS : tracked_in
    DAILY_PLANS ||--o{ DAILY_EVALUATIONS : evaluated_by

    USERS {
        uuid id PK
        string email
        string timezone
        jsonb current_self_baseline
        jsonb target_self_goal
        string status
        timestamp created_at
    }

    USER_CONSTRAINTS {
        uuid id PK
        uuid user_id FK
        string category "WORK | SCHOOL | COMMUTE | FAMILY"
        string day_of_week
        time start_time
        time end_time
        boolean is_flexible
    }

    FINANCIAL_PROFILES {
        uuid id PK
        uuid user_id FK
        decimal weekly_food_budget
        decimal daily_budget_cap
        string currency
    }

    TRANSITION_ROADMAPS {
        uuid id PK
        uuid user_id FK
        string status "ACTIVE | PAUSED | COMPLETED | RECALCULATING"
        date start_date
        date target_end_date
        int total_days
        jsonb domain_weights
    }

    DAILY_PLANS {
        uuid id PK
        uuid roadmap_id FK
        date plan_date
        int day_number
        string state "PLANNED | IN_PROGRESS | COMPLETED | ADJUSTED"
        decimal budget_estimate
    }

    PLAN_ITEMS {
        uuid id PK
        uuid daily_plan_id FK
        string domain "SLEEP | WAKE | NUTRITION | MOVEMENT | BODY"
        string title
        time scheduled_time
        jsonb item_metadata "sets, reps, target_time, estimated_cost"
        boolean is_critical
    }

    EXECUTION_LOGS {
        uuid id PK
        uuid plan_item_id FK
        time actual_time
        string status "COMPLETED | SKIPPED | PARTIAL | MISSED"
        decimal actual_cost
        string notes
    }

    DAILY_EVALUATIONS {
        uuid id PK
        uuid daily_plan_id FK
        string evaluation_result "SUCCESS | WITHIN_TOLERANCE | MISSED | SIGNIFICANT_MISS"
        jsonb adaptation_action "HOLD | REDUCE_STEP | RECOVER | CONTINUE"
        string reason
        timestamp evaluated_at
    }
```

---

## 4. State Machine: Adaptive Plan Lifecycle

Setiap hari pengguna melewati siklus status transisi:

```mermaid
stateDiagram-v2
    [*] --> PlanGenerated: 00:00 (Scheduler)
    PlanGenerated --> ActiveExecution: User starts day
    
    state ActiveExecution {
        [*] --> TrackingItems
        TrackingItems --> ItemLogged: Log Check-in
        ItemLogged --> TrackingItems: Next Item
    }

    ActiveExecution --> DayCompleted: Day ends (Cut-off Time)
    DayCompleted --> DailyEvaluation: Evaluate deviations
    
    state DailyEvaluation {
        [*] --> AnalyzeDeviations
        AnalyzeDeviations --> SuccessState: Delta <= Tolerance
        AnalyzeDeviations --> MissedState: Delta > Threshold
        AnalyzeDeviations --> SignificantMissState: Repeated or Large Delta
    }

    SuccessState --> NextPlanStep: Advance Step (+Step Size)
    MissedState --> HoldOrReduce: Hold target / Lower difficulty
    SignificantMissState --> RecoveryMode: Simplify tasks & Re-stabilize

    NextPlanStep --> [*]
    HoldOrReduce --> [*]
    RecoveryMode --> [*]
```

### 4.1 Logika Adaptasi (Adaptation Strategies)
1. **Continue Progression**:
   - Jika target tercapai atau dalam batas toleransi (misal selisih bangun < 15 menit), lanjutkan roadmap ke step berikutnya.
2. **Hold Target**:
   - Jika pengguna meleset 1 kali, jangan langsung menaikkan kesulitan. Pertahankan target yang sama untuk hari berikutnya agar ritme stabil.
3. **Reduce Step Size**:
   - Jika meleset berturut-turut (misal 2 hari), kecilkan lompatan perubahan (misal dari target maju 30 menit menjadi hanya 10 menit).
4. **Enter Recovery Mode**:
   - Jika terjadi significant miss (misal sakit atau jadwal berantakan), kurangi beban aktivitas harian ke level minimum (survival routine) tanpa memutus riwayat dan tanpa pesan yang menghakimi (non-judgmental).

---

## 5. Safety, Budget, & Resource Guardrails

1. **Safety Boundaries**:
   - Tidak memperbolehkan defisit/surplus kalori ekstrem atau pemotongan jam tidur di bawah batas aman medis (>6 jam tidur minimum).
   - Menolak target yang tidak realistis secara fisiologis (misal: perubahan bangun 6 jam lebih awal dalam 2 hari).
2. **Budget Guardrail**:
   - Rekomendasi makanan tidak boleh melebihi budget harian (Weekly Budget / 7).
   - Jika ada hari yang overbudget, sistem otomatis menyesuaikan rekomendasi hari berikutnya agar total mingguan tetap seimbang.
3. **Resource Guardrail**:
   - Memfilter workout berdasarkan input fasilitas (No Gym, No Equipment, Small Room).

---

## 6. Recommended Technology Stack

| Layer | Rekomendasi Teknologi | Alasan Pemilihan |
| :--- | :--- | :--- |
| **Mobile Client** | **Flutter** (atau React Native / Expo) | Performa native, kemudahan build cross-platform (Android/iOS), dukungan local storage offline yang matang. |
| **Backend API** | **FastAPI / Node.js (NestJS / Hono)** | Ringan, eksekusi kalkulasi algoritma cepat, mendukung type safety tinggi, dan integrasi mudah dengan worker. |
| **Database** | **PostgreSQL** | Relasional yang handal untuk constraint model, JSONB support untuk fleksibilitas metadata roadmap dan evaluasi. |
| **Caching & Workers** | **Redis + BullMQ / Celery** | Menangani background evaluation setiap pergantian hari (midnight evaluation worker) dan push reminders. |
| **Local Database** | **SQLite / WatermelonDB** | Menjamin aplikasi tetap responsif instan dan offline-ready. |

---

## 7. Implementation Phasing

1. **Phase 1 (Foundation & Schema)**: Inisiasi database models, User Life Profile, dan Constraint Matrix.
2. **Phase 2 (Adaptive Engine Core)**: Implementasi Roadmap Generator & Daily Plan Evaluator.
3. **Phase 3 (Mobile Client Core)**: Pembuatan UI Onboarding (Current Self vs Target Self), Daily Plan View, dan Fast Check-in.
4. **Phase 4 (Adaptation Loop & Notifications)**: Background Worker untuk Midnight Evaluation, Push Reminder, dan Recovery Trigger.
