# Project Chronos — Coding Standards & Engineering Rules

Dokumen ini adalah aturan absolut bagi seluruh AI Agent dan engineer yang berkontribusi pada pengembangan **Project Chronos (Adaptive Lifestyle Transition System)**.

---

## 1. Core Product & Architectural Directives

Setiap baris kode, API endpoint, dan komponen UI yang dibuat harus mematuhi filosofi inti dari [PRD.md](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/prd/PRD.md):

1. **Current Life First**:
   - Jangan pernah membuat asumsi default bahwa semua user bangun jam 05.00 atau bisa ke gym.
   - Semua kalkulasi roadmap wajib berangkat dari `Current Self Baseline` pengguna.
2. **Failure as Information, Never as Punishment**:
   - Dilarang keras menggunakan tone yang menghakimi seperti "You failed", "Streak broken", atau penalti visual agresif.
   - Gunakan pendekatan adaptif: "Plan hari ini meleset, mari sesuaikan untuk besok".
3. **Respect Constraints & Budget**:
   - Algoritma daily planner tidak boleh menjadwalkan aktivitas yang bertabrakan dengan jadwal wajib (`School/Work/Commute`).
   - Rekomendasi nutrisi/makanan harus selalu berada di bawah batas budget harian yang realistis.
4. **Mobile-First & Frictionless**:
   - Proses tracking/check-in harian harus dapat diselesaikan dalam kurang dari 10 detik ("Open -> Understand -> Act/Check-in -> Close").
   - Jangan membebani user dengan form pengisian yang panjang dan rumit di rutinitas harian.
5. **Zero AI Slop Compliance**:
   - Wajib mengikuti seluruh ketentuan dalam [anti-ai-slop.md](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/anti-ai-slop.md).

---

## 2. Architecture & Code Structure Rules

### 2.1 Modularity & Separation of Concerns
- **Backend ([`Backend/`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/Backend))**:
  - `controllers/` / `routers/`: Hanya menangani HTTP request/response dan validasi skema payload.
  - `services/`: Business logic, orkestrasi data, dan integrasi antar domain.
  - `engine/` (`Adaptive Engine`): Komponen murni (pure logic) untuk kalkulasi feasibility, roadmap generation, deviation analysis, dan adaptation trigger. Terisolasi dari dependensi database langsung agar mudah di-unit test.
  - `models/` / `repositories/`: Akses data dan skema database.
- **Mobile ([`Mobile/`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/Mobile))**:
  - `presentation/` (Screens & Widgets): Menangani UI dan animasi micro-interaction.
  - `state/` (State Management): Mengelola state lokal, offline sync, dan optimistic updates.
  - `domain/` / `data/`: Local storage, API client, dan data mapping.

### 2.2 Defensive Programming & Type Safety
- Gunakan strict typing di semua layer (TypeScript, Python Pydantic/Type Hints, Dart).
- Hindari tipe `any` atau dynamic casting tanpa validasi skema runtime (e.g. Zod / Pydantic).
- Setiap kalkulasi waktu (tidur/bangun/jadwal) wajib memperhitungkan Timezone dan penyeberangan tengah malam (midnight rollover, misal tidur jam 02.00 AM esok harinya).

---

## 3. Testing & Verification Standards

1. **Adaptive Engine Unit Tests**:
   - Setiap rule adaptasi (`SUCCESS`, `WITHIN_TOLERANCE`, `MISSED`, `SIGNIFICANT_MISS`) wajib memiliki unit test skenario waktu nyata.
   - Uji skenario edge case: perubahan shift kerja mendadak, budget minus, atau jeda absensi pengguna beberapa hari.
2. **Constraint Collision Tests**:
   - Wajib ada test yang memverifikasi bahwa item plan tidak pernah di-generate pada rentang waktu `USER_CONSTRAINTS`.

---

## 4. Git, Commit Granularity & Continuous Push Rules

### 4.1 Granular Atomic Commits (Wajib Pecah Commit)
- **Dilarang keras melakukan monolithic commit raksasa** (misal menggabungkan 20 file arsitektur, backend, UI, dan test dalam 1 commit tunggal).
- Setiap perubahan harus dipecah ke dalam unit-unit commit kecil yang atomik dan deskriptif:
  - Commit terpisah untuk dokumen PRD & spesifikasi.
  - Commit terpisah untuk skema database/model data.
  - Commit terpisah untuk implementasi unit test.
  - Commit terpisah untuk core logic Adaptive Engine.
  - Commit terpisah untuk komponen UI screen/widget.
  - Commit terpisah untuk integrasi service API.

### 4.2 QC-Validated Continuous Push Flow
- Setiap kali satu unit pekerjaan atomik selesai dan **telah divalidasi oleh Agen QC** (linter lolos, unit test hijau, zero-slop audit terverifikasi):
  1. Buat commit terisolasi dengan pesan Conventional Commit.
  2. Langsung lakukan `git push origin <branch>` secara berkesinambungan.
- Riwayat commit di repositori GitHub harus terlihat aktif, terstruktur, dan merefleksikan proses engineering bertahap secara transparan.

### 4.3 Commit Message Standard
Gunakan format Conventional Commits tanpa emoji:
- `docs(prd): define tiered tolerance thresholds and interval notification rules`
- `docs(arch): define adaptive engine mathematical step sizing specification`
- `feat(engine): implement feasibility calculator for sleep transition`
- `test(engine): add test suite for consecutive missed wakeups`
- `feat(mobile): implement 1-tap quick checkin widget for daily meals`
- `fix(backend): resolve midnight rollover time interval collision`

### 4.4 Documentation Integrity
- Selalu perbarui dokumen di [`.agents/docs/`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs) jika terjadi perubahan struktur skema atau logika adaptasi.
