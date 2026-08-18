Project Chronos — Revisi Flow & UI Integration Phase

Document: revisi-flow-ui-phase.md
Status: Planned
Scope: Perbaikan implementasi flow onboarding dan dashboard saat ini
Focus: Konsistensi UI ↔ Adaptive Engine
Important: Fase ini tidak membahas redesign keseluruhan produk. Ketidaksesuaian besar terhadap ekspektasi visual/experience akan dibahas pada fase terpisah setelah perbaikan logic-flow ini selesai.

1. Tujuan Fase

Implementasi Chronos saat ini sudah memiliki alur dasar:

Current Self
    ↓
Target Self
    ↓
Jadwal Wajib
    ↓
Feasibility
    ↓
Daily Plan

Namun masih terdapat beberapa ketidaksesuaian antara:

Input User
↓
Keputusan Adaptive Engine
↓
Informasi yang ditampilkan UI

Fase ini bertujuan memastikan UI tidak menampilkan data yang:

berubah tanpa penjelasan;

berbeda dari input user;

menyembunyikan keputusan engine;

mencampurkan measurement dengan micro-quest;

membuat Chronos terlihat seperti habit checklist biasa.

2. Kondisi Implementasi Saat Ini

Berdasarkan implementasi saat ini:

Onboarding

Langkah 1 — Current Self

User memasukkan:

Jam tidur saat ini
Jam bangun saat ini
Budget makan mingguan

Langkah 2 — Target Self

User memasukkan:

Target jam bangun
Target jam tidur
Durasi transisi

Langkah 3 — Constraint

User dapat menambahkan:

Kuliah
Kerja
Sekolah
atau jadwal wajib lainnya

Langkah 4 — Feasibility

Sistem menampilkan status apakah target dapat dijalankan.

Dashboard

Sistem menampilkan:

Target bangun
Target tidur
Budget
Progress task
Daily plan

3. PRIORITY P0 — Konsistensi Flow

P0.1 — Jangan Mengubah Durasi Tanpa Penjelasan

Masalah

User memasukkan:

Durasi transisi: 30 hari

namun dashboard dapat menampilkan:

Hari 1 / 45

Perubahan seperti ini tidak boleh terjadi tanpa penjelasan.

Flow yang Diharapkan

User meminta
30 hari
    ↓
Feasibility Engine
    ↓
Minimum recommended duration
45 hari
    ↓
UI menjelaskan
    ↓
User menerima / mengubah target

Jangan

Input 30 hari
↓
langsung dashboard 45 hari

Feasibility Screen Harus Menampilkan

Contoh:

Target Anda membutuhkan waktu lebih panjang

Durasi yang Anda minta
30 hari

Durasi transisi yang direkomendasikan Chronos
45 hari

Alasan
Target jam bangun membutuhkan pergeseran bertahap
agar perubahan tidak terlalu agresif.

Pilihan User

Minimal:

[Gunakan 45 Hari]

[Ubah Target]

Acceptance Criteria

Dashboard tidak boleh diam-diam mengubah total hari.

Semua perubahan durasi dari engine harus dijelaskan.

User mengetahui requested duration dan effective duration.

Roadmap hanya dibuat setelah durasi final dikonfirmasi.

P0.2 — Tentukan Behavior Hari Pertama

Masalah

Baseline user:

Tidur : 02:00
Bangun: 10:00

tetapi Day 1 langsung menjadi:

Tidur : 01:45
Bangun: 09:45

Ini membuat Day 1 langsung melakukan progression.

Keputusan untuk Fase Ini

Gunakan konsep:

DAY 1 = BASELINE / STABILIZATION DAY

Artinya:

Day 1

Target bangun = baseline bangun user
Target tidur  = baseline tidur user

Contoh:

Baseline
Tidur 02:00
Bangun 10:00

Day 1
Tidur 02:00
Bangun 10:00

Progress berikutnya baru diputuskan berdasarkan hasil Day 1.

Acceptance Criteria

Hari pertama tidak otomatis menggeser target.

Day 1 menggunakan current baseline.

Progression baru terjadi setelah evaluasi.

Target tidak maju hanya karena hari kalender bertambah.

P0.3 — Pisahkan Measurement dan Micro-Quest

Masalah

Saat ini terdapat task seperti:

Bangun & Hidrasi

Ini menggabungkan dua konsep berbeda.

Measurement

Measurement adalah data yang digunakan engine.

Contoh:

Jam bangun aktual
Jam tidur aktual
Berat badan
Pengeluaran aktual

Micro-Quest

Micro-quest adalah tindakan pendukung.

Contoh:

Minum air setelah bangun
Stretching
Jalan kaki
Persiapan tidur

Jangan

✓ Bangun & Hidrasi

Gunakan

BANGUN

Target
09:45

Aktual
09:52

Status
Dalam toleransi

Kemudian task terpisah:

○ Minum air setelah bangun

Acceptance Criteria

Wake time memiliki actual time.

Bedtime memiliki actual time.

Measurement tidak hanya berupa checkbox.

Hidrasi menjadi quest terpisah jika digunakan.

Adaptive Engine menerima actual value yang dibutuhkan.

P0.4 — Feasibility Screen Harus Menjelaskan Hasil

Masalah

Screen saat ini hanya menampilkan:

Target Realistis & Aman

dengan sedikit konteks.

Hal tersebut belum menunjukkan bahwa Chronos benar-benar memahami kondisi user.

Feasibility Screen Baru

Minimal menampilkan:

Kondisi Saat Ini
Bangun 10:00
Tidur 02:00

Target
Bangun 07:00
Tidur 23:00

Durasi yang Diminta
30 hari

Pergeseran Bangun
3 jam

Durasi Efektif
30 hari / hasil rekomendasi engine

Status
Target dapat dijalankan secara bertahap

Jika perlu penyesuaian:

Durasi yang Diminta
30 hari

Rekomendasi Chronos
45 hari

Tone

Hindari:

AMAN SECARA MEDIS

Gunakan:

Sesuai dengan policy transisi Chronos

atau:

Dapat dijalankan secara bertahap

Acceptance Criteria

Feasibility menjelaskan input utama.

Feasibility menjelaskan keputusan engine.

Perubahan roadmap tidak tersembunyi.

CTA baru aktif setelah hasil dipahami user.

4. PRIORITY P1 — Perbaikan Dashboard

P1.1 — Dashboard Jangan Terasa Seperti Checklist App

Masalah

Hierarchy saat ini terlalu menonjolkan:

1 / 5 selesai

Hal tersebut dapat membuat Chronos terasa seperti habit tracker biasa.

Hierarchy yang Diinginkan

Prioritas visual:

1. Posisi transisi hari ini
2. Target penting hari ini
3. Actual progress
4. Daily plan
5. Completion task

Contoh Struktur

HARI INI
Day 1 dari 30

Current Transition
Bangun: 10:00
Tidur : 02:00

Status
Baseline Day

Kemudian:

Today's Plan

Bangun
Target 10:00
Actual --:--

Meal 1
12:30

Movement
16:00

Meal 2
19:30

Wind-down
01:45

Progress checkbox tetap boleh ada tetapi bukan hero utama.

P1.2 — Tampilkan Transition Context

Dashboard harus menjawab:

Saya sekarang berada di mana?
Saya sedang menuju ke mana?
Apa target saya hari ini?
Kenapa target hari ini seperti ini?

Contoh

Current Wake
10:00

Final Goal
07:00

Today's Target
10:00

Transition State
STABILIZING

Jika hold:

Today's Target
09:45

Transition State
HOLD

Chronos mempertahankan target hari ini
agar rutinitas lebih stabil.

P1.3 — Perjelas Nutrition Task

Masalah

Label seperti:

Makan Siang / Sarapan Awal

terlalu ambigu.

Untuk Fase Ini

Belum perlu membuat full nutrition recommendation engine.

Gunakan terminology sederhana:

Meal 1
Meal 2
Meal 3
Snack

atau label kontekstual jika sudah diketahui:

Sarapan
Makan Siang
Makan Malam

Jangan mencampurkan dua jenis meal dalam satu nama.

P1.4 — Budget Dashboard Harus Jelas

Saat ini terdapat:

Alokasi Makan Hari Ini
Sisa Hari Ini

Ini sudah baik.

Tambahkan konteks mingguan secara bertahap.

Contoh:

Budget Mingguan
Rp350.000

Budget Hari Ini
Rp50.000

Terpakai
Rp0

Sisa
Rp50.000

Budget harus tetap dianggap constraint planning.

5. State UI yang Harus Dipersiapkan

UI harus dapat membedakan:

BASELINE
PROGRESSING
MAINTAINING
HOLD
RECOVERY
NO_DATA
COMPLETED

Tidak semua state harus memiliki visual kompleks.

Minimal dashboard dapat menerima state tersebut dari backend.

6. Daily Evaluation UI

Setelah user memasukkan actual wake/sleep:

Contoh:

Target Bangun
09:45

Aktual
09:52

Selisih
7 menit

Status
Sesuai target

Untuk miss:

Target
09:45

Aktual
11:20

Status
Hari ini cukup jauh dari target.

Chronos akan mempertahankan langkah berikutnya
agar transisi tidak terlalu berat.

Gunakan tone non-judgmental.

7. Flow yang Diharapkan Setelah Revisi

ONBOARDING
│
├── Current Self
│
├── Target Self
│
├── Constraints
│
└── Feasibility
       │
       ├── Requested Duration
       ├── Recommended Duration
       └── User Confirmation
               ↓
         CREATE ROADMAP
               ↓
            DAY 1
         BASELINE DAY
               ↓
           CHECK-IN
               ↓
           EVALUATION
               ↓
     ADAPTIVE ENGINE DECISION
               ↓
        NEXT DAILY PLAN

8. Data Flow UI ↔ Backend

Onboarding

Mobile
↓
baseline
goal
constraints
budget
duration
↓
Backend Feasibility
↓
recommendation
↓
Mobile Confirmation
↓
Roadmap Creation

Daily Flow

Mobile
↓
actual wake
actual bedtime
quest completion
actual spending
↓
Backend
↓
domain evaluation
adaptive action
next plan
↓
Mobile Dashboard

9. Jangan Dilakukan pada Fase Ini

DO NOT redesign entire application
DO NOT replace visual design system
DO NOT add gamification
DO NOT add social feature
DO NOT add AI chatbot
DO NOT build full nutrition engine
DO NOT build full workout engine
DO NOT add wearable integration
DO NOT add complex analytics

Fase ini hanya memperbaiki:

Flow
Data consistency
Engine visibility
Measurement
Daily plan semantics

10. Acceptance Checklist

Input duration tidak berubah diam-diam.

Recommended duration dijelaskan pada feasibility.

User mengonfirmasi effective duration.

Day 1 menggunakan baseline.

Calendar day dan transition progression tidak dicampur.

Wake measurement memiliki actual time.

Bedtime measurement memiliki actual time.

Hidrasi tidak digabung dengan wake measurement.

Feasibility menjelaskan kondisi awal, target, dan keputusan engine.

Dashboard menampilkan transition state.

Completion count bukan fokus utama dashboard.

Nutrition task tidak menggunakan label ambigu.

Budget menampilkan alokasi dan realisasi secara jelas.

UI mampu menerima state HOLD / RECOVERY / NO_DATA.

Tidak ada behavior engine tersembunyi dari user.

Tidak ada perubahan besar visual di luar scope fase ini.

11. Definition of Done

Chronos Flow Revision v0.1
│
├── transparent feasibility
├── explicit duration decision
├── baseline-first Day 1
├── measurement separated from quest
├── adaptive state visible
├── budget context visible
├── daily plan semantically clear
└── ready for broader UX redesign discussion

Setelah fase ini selesai:

NEXT
Broader Product Experience Review

Pada fase berikutnya baru dibahas kenapa hasil aplikasi secara keseluruhan masih belum sesuai ekspektasi produk, termasuk:

UX direction
visual identity
information architecture
onboarding experience
dashboard composition
product personality
interaction model