Antigravity Task Prompt — Identity & User State Foundation v0.1

Context

Project: Chronos

Chronos adalah aplikasi mobile adaptive lifestyle transition mentor yang membantu user memperbaiki gaya hidup secara bertahap berdasarkan kondisi nyata mereka, goal, rutinitas wajib, budget, dan progress harian.

Backend saat ini menggunakan:

Python

FastAPI

Pydantic v2

Pure Adaptive Engine

Pytest

Modular monolith

Adaptive Engine sudah dipisahkan dari I/O/database dan harus tetap pure.

Phase sebelumnya sedang menyelesaikan:

flow onboarding;

transparent feasibility;

baseline day;

adaptive transition;

daily measurement;

budget context;

state machine.

Phase ini bukan phase intelligence domain.

Jangan implementasikan Nutrition Engine, Workout Engine, AI recommendation, atau dynamic assessment secara penuh.

Objective

Bangun fondasi:

Identity & User State Foundation v0.1

Tujuannya adalah memastikan setiap data Chronos:

User
↓
Profile
↓
Goals
↓
Baselines
↓
Constraints
↓
Budget
↓
Roadmap
↓
Tracking

memiliki owner yang jelas dan dapat disimpan secara persisten dengan aman.

Authentication digunakan untuk mengidentifikasi user.

Data profile digunakan sebagai state aplikasi.

Historical measurements tidak boleh hilang ketika nilai terbaru berubah.

Core Technology Decision

Gunakan:

Authentication
→ Supabase Auth

Database
→ Supabase PostgreSQL

Authorization
→ Row Level Security (RLS)

Backend
→ FastAPI

Identity Token
→ Supabase JWT

FastAPI tetap menjadi backend application layer Chronos.

Supabase digunakan untuk:

Auth
PostgreSQL
RLS

Jangan memindahkan Adaptive Engine ke Supabase Edge Functions.

Architectural Principle

Pertahankan:

Mobile
   ↓
Supabase Auth
   ↓ JWT
FastAPI
   ↓
Repository / Persistence Layer
   ↓
Supabase PostgreSQL

Adaptive Engine tetap:

app/engine/

dan:

MUST NOT
depend on Supabase
depend on PostgreSQL
perform network I/O
perform database I/O

P0.1 — Supabase Configuration

Tambahkan konfigurasi environment yang dibutuhkan.

Contoh:

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=

Jangan hardcode secret.

Semua environment variable harus dibaca melalui:

Pydantic Settings

Service role key:

NEVER expose to mobile client
NEVER return through API
NEVER commit to Git

Tambahkan:

.env.example

tanpa secret asli.

P0.2 — Authentication Flow

Implementasikan authentication foundation.

Required flow:

User Sign Up
↓
Supabase Auth

User Login
↓
Supabase Access Token

Mobile Request
↓
Authorization: Bearer <JWT>

FastAPI
↓
JWT Verification
↓
Authenticated User Context

FastAPI harus dapat memperoleh:

authenticated_user_id
email

dari token yang valid.

P0.3 — Authentication Dependency

Buat reusable FastAPI dependency.

Contoh conceptual API:

get_current_user()

Dependency ini bertanggung jawab untuk:

Read Authorization header
↓
Validate JWT
↓
Extract user identity
↓
Return authenticated user

Unauthorized request:

401 Unauthorized

Invalid token:

401 Unauthorized

User tidak boleh memberikan:

user_id

secara bebas pada endpoint protected untuk menentukan ownership.

Ownership harus berasal dari authenticated JWT.

P0.4 — Core Profile Table

Buat application-level profile table.

Jangan menggunakan auth.users sebagai application profile.

Conceptual schema:

profiles
├── id / user_id
├── display_name
├── birth_date
├── sex
├── timezone
├── height_cm
├── current_weight_kg
├── occupation_type
├── onboarding_status
├── created_at
└── updated_at

Primary identity:

profiles.user_id
→ references auth.users.id

Use UUID.

P0.5 — Profile Data Principle

Pisahkan:

IDENTITY
STATE
HISTORY

Identity

Contoh:

user_id
email
account identity

Protected.

Profile State

Contoh:

display name
height
occupation
timezone
current weight

Editable.

Historical Data

Contoh:

weight history
sleep measurements
budget spending
check-ins

Jangan overwrite history.

Contoh:

Initial Weight
48.0 kg

Week 1
48.4 kg

Week 3
49.0 kg

Jangan hanya mengubah:

48.0
→
49.0

dan kehilangan historical baseline.

P0.6 — Do Not Overload profiles

Jangan memasukkan seluruh domain Chronos ke satu table.

Hindari:

profiles
├── bedtime
├── target_bedtime
├── food_budget
├── meals_per_day
├── dumbbell_access
├── workout_level
├── target_weight
├── wake_target
├── ...

Gunakan domain separation.

Persiapkan struktur konseptual:

profiles
│
├── user_goals
├── sleep_baselines
├── nutrition_baselines
├── activity_baselines
├── user_constraints
├── financial_profiles
├── transition_roadmaps
└── measurements

Tidak semua table harus memiliki full business logic pada phase ini.

Tujuan phase adalah foundation and ownership.

P0.7 — User Goal Table Foundation

Buat schema minimal untuk goal ownership.

Contoh:

user_goals
├── id
├── user_id
├── domain
├── priority
├── status
├── created_at
└── updated_at

Allowed conceptual domains:

SLEEP_ROUTINE
NUTRITION_WEIGHT_GAIN
PHYSICAL_ACTIVITY

Priority:

PRIMARY
SECONDARY
SUPPORTING

Jangan implementasikan goal intelligence penuh.

Jangan implementasikan recommendation logic.

P0.8 — Constraint Persistence

Persist existing:

UserConstraint

ke database.

Constraint harus memiliki ownership:

user_id

Minimal:

id
user_id
title
category
day_of_week
start_time
end_time
is_flexible
created_at
updated_at

Pertahankan compatibility dengan schema engine yang sudah ada.

P0.9 — Financial Profile Persistence

Persist financial profile.

Minimal:

financial_profiles
├── id
├── user_id
├── weekly_food_budget
├── currency
├── created_at
└── updated_at

Jangan implementasikan full nutrition-budget planner pada phase ini.

Existing budget engine tetap pure.

P0.10 — Baseline Foundation

Buat tempat penyimpanan baseline per domain.

Minimal sleep baseline dapat berisi:

user_id
bedtime
wake_time
captured_at

Nutrition/activity baseline boleh dipersiapkan secara minimal.

Jangan mendesain final dynamic assessment sekarang.

Jika field belum final:

keep schema minimal

dan jangan mengarang requirement baru.

P0.11 — Row Level Security

Aktifkan RLS pada semua user-owned tables.

Rule utama:

authenticated user
can only access
rows where user_id = auth.uid()

Apply minimal ke:

profiles
user_goals
user_constraints
financial_profiles
baseline tables

Pastikan:

User A
cannot SELECT User B
cannot UPDATE User B
cannot DELETE User B
cannot INSERT row owned by User B

P0.12 — Profile API

Tambahkan protected endpoints.

Minimal:

GET /api/v1/profile

Mengambil profile user yang sedang login.

PATCH /api/v1/profile

Mengubah field profile yang memang editable.

Jangan menerima:

user_id

dari body sebagai ownership source.

Gunakan authenticated user.

P0.13 — Onboarding Status

Tambahkan state onboarding.

Contoh:

NOT_STARTED
IN_PROGRESS
COMPLETED

atau model sederhana ekuivalen.

Tujuannya:

Login
↓
Check profile
↓
Onboarding completed?
├── No → Onboarding
└── Yes → Dashboard

Jangan implementasikan seluruh dynamic onboarding baru pada phase ini.

Cukup foundation state.

P0.14 — Repository Layer

Pisahkan database access dari API endpoint.

Target structure:

app/
├── api/
├── engine/
├── schemas/
├── models/
├── repositories/
├── services/
└── core/

Contoh:

ProfileRepository
GoalRepository
ConstraintRepository
FinancialProfileRepository

Endpoint tidak boleh dipenuhi raw SQL.

Adaptive Engine tidak boleh mengakses repository.

P0.15 — Persistence Models vs API Schemas

Pisahkan:

Database models
≠
API schemas
≠
Pure engine models

Jangan membuat engine bergantung pada ORM entity.

Transformation layer diperbolehkan.

Contoh:

DB Row
↓
Repository
↓
Pydantic Domain Data
↓
Pure Engine

P0.16 — Preserve Baseline History

Jika baseline baru dibuat:

DO NOT silently overwrite historical baseline

Gunakan strategi yang memungkinkan historical comparison.

Minimal:

captured_at
is_current

atau design equivalent.

Initial baseline harus tetap dapat diketahui di masa depan.

P0.17 — Migration Strategy

Gunakan database migrations.

Jangan mengandalkan manual table creation tanpa versioning.

Simpan SQL/migration files di repository.

Contoh struktur:

supabase/
└── migrations/

Setiap schema change harus reproducible.

P0.18 — Error Handling

Standardize error response untuk:

Unauthorized
Profile not found
Validation error
Database unavailable
Ownership violation

Jangan bocorkan:

database credentials
SQL query
JWT secret
internal stack trace

ke mobile client.

P0.19 — Automated Tests

Tambahkan tests untuk authentication dan persistence.

Minimum test scenarios:

✓ protected endpoint rejects missing token
✓ invalid token rejected
✓ valid authenticated user accepted

✓ user can GET own profile
✓ user can PATCH own profile

✓ user A cannot access user B profile

✓ user A cannot access user B goals
✓ user A cannot access user B constraints

✓ onboarding status persists

✓ financial profile ownership works

✓ baseline can be saved
✓ historical baseline is preserved

✓ existing adaptive engine tests remain green

Jika integration testing langsung dengan Supabase tidak praktis pada local test suite:

use appropriate test boundary

tetapi jangan mengubah pure engine architecture.

P1 — Nice-to-Have After P0

Jika seluruh P0 stabil, boleh tambahkan:

automatic profile creation after signup
updated_at trigger
soft delete where relevant
audit timestamps
repository protocol/interface
database health check

Jangan mengerjakan P1 jika P0 belum selesai.

Security Rules

Wajib:

No service-role key in mobile
No JWT secret in frontend
No raw ownership user_id from client
RLS enabled
Secrets via environment
Protected endpoints verify token
Sensitive errors sanitized

Jangan disable RLS hanya untuk mempermudah development.

Out of Scope

JANGAN kerjakan pada phase ini:

Nutrition calculation
Calorie calculation
BMR/TDEE calculation
Meal recommendation
Food database
Food pricing engine
Workout recommendation
Exercise knowledge base
Workout progression
AI/LLM
Vector database
Dynamic assessment full flow
Wearable integration
Push notification
Gamification
Social feature
Advanced analytics

Jika menemukan kebutuhan tersebut:

document as TODO
do not implement

Compatibility Requirement

Pastikan phase ini tidak merusak:

Pure Adaptive Engine
Feasibility Engine
Step Sizing
State Machine
Collision Resolver
Budget Engine
Existing API health endpoints
Existing test suite

Authentication dapat ditambahkan pada endpoint user-data baru.

Jangan sembarang memproteksi health endpoint.

Recommended Implementation Order

Kerjakan secara berurutan:

1. Supabase configuration
2. Database migrations
3. RLS
4. JWT authentication dependency
5. Profile persistence
6. Profile GET/PATCH
7. Onboarding status
8. Goal foundation
9. Constraint persistence
10. Financial profile persistence
11. Baseline persistence
12. Repository layer cleanup
13. Automated tests
14. Security review

Jangan parallelize migration dan schema assumptions tanpa sinkronisasi.

Definition of Done

Phase dianggap selesai jika:

Supabase Auth terintegrasi.

FastAPI dapat memverifikasi authenticated user.

Protected endpoint menolak request tanpa token.

profiles terhubung dengan auth.users.

Profile user dapat dibaca dan diedit.

Ownership tidak ditentukan oleh body request.

RLS aktif pada semua user-owned tables.

User tidak dapat membaca data user lain.

User goal foundation tersedia.

Constraint dapat disimpan per user.

Financial profile dapat disimpan per user.

Baseline dapat disimpan dengan history.

Onboarding status persisten.

Repository layer terpisah dari engine.

Adaptive Engine tetap zero I/O.

Secrets tidak hardcoded.

.env.example tersedia.

Database migrations tersedia.

Auth/persistence test suite tersedia.

Existing Adaptive Engine tests tetap lulus.

Tidak ada Nutrition/Workout/AI logic baru pada phase ini.

Required Final Report From Agent

Setelah selesai, berikan report dengan format:

# Identity & User State Foundation v0.1 — Implementation Report

## Implemented
- ...

## Database Tables
- ...

## RLS Policies
- ...

## API Endpoints
- ...

## Authentication Flow
- ...

## Tests
- total:
- passed:
- failed:

## Files Added
- ...

## Files Modified
- ...

## Security Notes
- ...

## Known Limitations
- ...

## TODO for Next Phase
- ...

Jangan mengklaim phase selesai jika ada P0 acceptance criteria yang belum terpenuhi.

Final Instruction

Prioritas phase ini adalah:

IDENTITY
OWNERSHIP
PERSISTENCE
SECURITY

Bukan:

FEATURE EXPANSION

Jika menemukan business rule yang belum ditentukan:

mark as TBD

Jangan mengarang behavior baru.

Pertahankan prinsip utama Chronos:

Pure Engine
+
Secure User State
+
Clear Ownership
+
Historical Progress

Execute: Identity & User State Foundation v0.1