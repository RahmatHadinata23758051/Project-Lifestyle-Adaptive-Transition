# Project Chronos — Adaptive Lifestyle Transition System

Pusat pengetahuan (knowledge base), spesifikasi produk, cetak biru arsitektur, pedoman koding, dan standar kualitas (Zero-AI-Slop) untuk AI Agent dan tim pengembang.

---

## Metadata Repositori & Kontributor

| Properti | Detail |
| :--- | :--- |
| **Nama Proyek** | Project Chronos (Adaptive Lifestyle Transition System) |
| **Repositori GitHub** | [`Project-Lifestyle-Adaptive-Transition`](https://github.com/RahmatHadinata23758051/Project-Lifestyle-Adaptive-Transition.git) |
| **Owner / Lead Author** | **Rahmat Hadinata** ([@RahmatHadinata23758051](https://github.com/RahmatHadinata23758051)) |
| **Email Kontak** | `rsafei731@gmail.com` |

---

## 1. Hub Dokumentasi & Aturan

| Kategori | Lokasi File | Deskripsi |
| :--- | :--- | :--- |
| **PRD (Product Requirements)** | [`PRD.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/prd/PRD.md) | Visi, filosofi Current Life First, domain lifestyle, ambang batas toleransi, dan notifikasi berinterval. |
| **Ruang Lingkup MVP (Scope)** | [`PRODUCT_SCOPE.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/prd/PRODUCT_SCOPE.md) | Batasan modul in-scope, non-goals, dan User Acceptance Criteria (UAC). |
| **Papan Kanban Sprint 1** | [`SPRINT_BOARD.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/pm/SPRINT_BOARD.md) | Live Kanban board ala Trello/Jira pelacakan task aktif Sprint 1. |
| **Master Backlog Epics** | [`BACKLOG.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/pm/BACKLOG.md) | Master Product Backlog yang dipetakan ke Sprint 1 hingga Sprint 4. |
| **Protokol Agile PM** | [`pm-agile-protocol.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/pm-agile-protocol.md) | Aturan alur 4-fase: PM Inisiasi -> Dev Write Code -> QC Audit -> PM Update Done. |
| **Arsitektur Sistem** | [`ARCHITECTURE.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/architecture/ARCHITECTURE.md) | Diagram sistem, Data Model (ERD), State Machine, dan rekomendasi stack teknologi. |
| **Spesifikasi Adaptive Engine** | [`ADAPTIVE_ENGINE_SPEC.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/docs/architecture/ADAPTIVE_ENGINE_SPEC.md) | Rumus matematis step sizing, algoritma deviasi harian, re-balancing budget, dan collision resolver. |
| **AI Agency Squad Manifest** | [`agency-squad-manifest.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/agency-squad-manifest.md) | Pemetaan peran squad (PM, Arsitek, Backend, Flutter, UI, QA, Security) dan alur Loop Engineering. |
| **Git Worktrees Strategy** | [`git-worktrees.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/git-worktrees.md) | Panduan isolasi workspace branch terpisah untuk pengerjaan agen paralel simultan. |
| **Anti-AI Slop Manifesto** | [`anti-ai-slop.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/anti-ai-slop.md) | Aturan ketat larangan emoji, anti-pattern visual (Impeccable style), zero hallucination, dan defensive code. |
| **Pedoman Koding & Rules** | [`project-rules.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/rules/project-rules.md) | Standar struktur kode, modularitas, testing, dan konvensi git. |
| **Anti-Slop Audit Skill** | [`SKILL.md`](file:///c:/Users/user/Nata/Project/Adaptive%20Lifestyle%20Transition%20System/.agents/skills/anti-slop/SKILL.md) | Panduan audit otomatis untuk verifikasi kualitas kode, UI, dan copy. |

---

## 2. Struktur Direktori `.agents/`

```text
.agents/
├── docs/
│   ├── prd/
│   │   ├── PRD.md                  # PRD Inti Project Chronos (Markdown Polished)
│   │   ├── PRODUCT_SCOPE.md        # Spesifikasi Ruang Lingkup MVP & UAC
│   │   └── PRD_TEMPLATE.md         # Template pembuatan PRD fitur baru
│   └── architecture/
│       ├── ARCHITECTURE.md         # Cetak biru arsitektur teknis & database schema
│       └── ADAPTIVE_ENGINE_SPEC.md # Rumus matematis & algoritma Adaptive Engine
├── pm/
│   ├── SPRINT_BOARD.md             # Live Kanban Board Sprint 1 (Trello / Jira style)
│   └── BACKLOG.md                  # Master Backlog Roadmap (Sprint 1 - 4)
├── rules/
│   ├── pm-agile-protocol.md        # Protokol Operasional PM-Dev-QC-PM Loop
│   ├── agency-squad-manifest.md    # Pemetaan peran AI Agency Squad & Loop Engineering
│   ├── git-worktrees.md            # Strategi workspace isolasi Git Worktrees
│   ├── anti-ai-slop.md             # Kebijakan Zero-AI-Slop & standar visual/rekayasa
│   └── project-rules.md            # Standar koding, testing, & git workflow
├── skills/
│   └── anti-slop/
│       └── SKILL.md                # Skill audit Anti-Slop
└── README.md                       # Indeks utama direktori .agents
```

---

## 3. Prinsip Utama Sistem

1. **Current Self -> Target Self**: Transisi bertahap, bukan perubahan drastis semalam.
2. **Respect Life Constraints**: Waktu kuliah, kerja, commute, dan budget adalah batasan mutlak yang tidak boleh dilanggar.
3. **Adaptive Engine (Failure as Information)**: Kegagalan hari ini adalah input untuk penyesuaian target esok hari tanpa pesan menghakimi.
4. **Frictionless Mobile UX**: Check-in harian cepat (<10 detik), tata letak bersih tanpa dekorasi berlebih, dan siap bekerja secara offline.
5. **Zero-AI-Slop Standard**: Bebas emoji, tanpa gradasi klise AI, tanpa halusinasi API, dan penanganan error yang nyata.
