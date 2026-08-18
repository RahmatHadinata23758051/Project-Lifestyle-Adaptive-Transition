# Git Worktree Strategy for Parallel Agent Squads

Dokumen ini mendefinisikan standar penggunaan **Git Worktrees** untuk mengisolasi pengembangan antar peran AI Agency Squad (Backend, Mobile, Adaptive Engine, QC) secara simultan tanpa konflik branch atau dirty state.

---

## 1. Konsep Utama Git Worktree dalam AI Agency

Git Worktree memungkinkan satu repositori git memiliki **beberapa folder kerja fisik secara bersamaan**, di mana masing-masing folder terhubung ke branch yang berbeda namun berbagi riwayat komit (`.git`) yang sama.

```text
Adaptive Lifestyle Transition System/ (Root Repository - Branch: main)
├── .worktrees/
│   ├── feat-backend-engine/   (Isolated Directory - Branch: feat/backend-engine)
│   ├── feat-mobile-ui/        (Isolated Directory - Branch: feat/mobile-ui)
│   └── fix-qc-tests/          (Isolated Directory - Branch: fix/qc-tests)
├── Backend/
├── Mobile/
└── .agents/
```

---

## 2. Standar Setup & Keamanan

### 2.1 Verifikasi .gitignore (Wajib)
Folder `.worktrees/` **wajib diabaikan** oleh git agar tidak sengaja ter-commit ke dalam repositori utama:

```gitignore
# Git Worktrees Directory
.worktrees/
worktrees/
```

### 2.2 Perintah Pembuatan Worktree
Untuk membuat workspace terisolasi bagi agen:

```powershell
# 1. Pastikan folder .worktrees di-ignore
# 2. Buat worktree dengan branch baru
git worktree add .worktrees/feat-backend-engine -b feat/backend-engine
git worktree add .worktrees/feat-mobile-ui -b feat/mobile-ui
```

### 2.3 Perintah Penghapusan & Cleanup Setelah Merge
Setelah tugas selesai, di-review, dan di-merge ke branch `main`:

```powershell
# Hapus worktree setelah selesai
git worktree remove .worktrees/feat-backend-engine
git branch -d feat/backend-engine
```

---

## 3. Protokol Eksekusi Agen pada Worktree
1. **Isolasi Penuh**: Agen Backend bekerja eksklusif di dalam path `.worktrees/feat-backend-engine`, sementara Agen Mobile bekerja di `.worktrees/feat-mobile-ui`.
2. **Zero File Locking**: Tidak ada risiko konflik penguncian file build atau node_modules/gradle cache.
3. **Independent Verification**: QA Tester dapat menjalankan test suite lengkap di satu worktree tanpa mengganggu agen lain yang sedang mengedit kode.
