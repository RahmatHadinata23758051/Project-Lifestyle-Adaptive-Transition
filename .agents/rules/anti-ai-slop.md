# Anti-AI Slop Manifesto & Strict Quality Directives

Dokumen ini mendefinisikan standar **Zero-AI-Slop** untuk **Project Chronos**. Aturan ini mengikat seluruh AI Agent, subagent, dan engineer di seluruh lini kode, arsitektur, UI mobile, copy/teks, dan logika adaptasi.

Referensi standar visual: [*Impeccable Style Anti-Patterns Guide*](https://impeccable.style/slop/).

---

## 1. 🚫 Kriteria AI Slop pada UI/UX Mobile (Design & Visual)

### 1.1 Visual & Decoration Slop (Dilarang Keras)
1. **No Purple/Neon Gradient Cliché**:
   - Hindari palet default AI: gradasi ungu-ke-biru/pink pada teks, tombol, background, atau badge.
   - Gunakan palet warna yang beralasan (*deliberate color tokens*), kontras tinggi, dan nyaman di mata (WCAG AAA compliant).
2. **No Glassmorphism & Neon Glow Abuse**:
   - Dilarang menambahkan efek blur kaca (*frosted glass*), border berpijar (*neon glow*), atau bola warna-warni kabur (*blurred background orbs*) yang hanya berfungsi sebagai hiasan kosong tanpa fungsi visual hierarchy.
3. **No Side-Tab Stripe Borders on Rounded Cards**:
   - Jangan membuat kartu dengan garis tebal di satu sisi (misal `border-left: 4px solid ...`) yang dipadukan dengan `border-radius` melengkung. Ini adalah ciri khas visual generatif AI yang paling klise.
4. **No Cardocalypse (Over-Nesting Cards)**:
   - Dilarang membuat kartu di dalam kartu di dalam kartu (3+ tingkat nesting). Jika struktur informasi padat, gunakan *spatial layout*, *divider tipis*, atau *section grouping* yang bersih.
5. **No Blob Cards (Extreme Border Radius)**:
   - Dilarang menggunakan border-radius ekstrem (misal 28px - 44px pada card kecil) yang mengubah elemen menjadi gumpalan bulat tak beraturan. Batas radius container umumnya 8px - 14px; bentuk pill penuh hanya untuk pill badge atau action tag.
6. **No Decorative Grid Backgrounds**:
   - Jangan menambahkan latar belakang garis-garis grid (*grid-line pattern*) yang tidak relevan dengan kanvas atau visualisasi data nyata.
7. **No Sketchy / Amateur SVG Mascots**:
   - Jangan membuat ilustrasi SVG buatan tangan sederhana/acak yang terlihat seperti doodle amatir. Jika belum ada aset ilustrasi produksi, gunakan layout tipografi dan whitespace yang presisi.

### 1.2 Typography & Layout Slop
1. **No Eyebrow / Kicker Uppercase Overhead**:
   - Hindari label huruf kapital kecil di atas setiap heading (contoh klise: `FEATURES`, `WHAT YOU GET`, `OVERVIEW`). Tulis langsung esensi pesan ke dalam heading.
2. **No Monospace Abuse for "Tech Vibes"**:
   - Font monospace hanya boleh digunakan untuk data numerik presisi (waktu tidur/bangun `06:30`, nominal rupiah `Rp350.000`), bukan untuk teks paragraf umum.
3. **No Generic Squircle Icon Tile Above Headings**:
   - Hindari pola klise kartu: ikon dalam kotak gradasi bulat melayang tepat di tengah atas judul. Buat tata letak natural (inline dengan judul atau menggunakan visual anchor yang bermakna).
4. **No Flat Type Hierarchy**:
   - Perbedaan ukuran font antar heading dan body text harus tegas (rasio minimal 1.25). Jangan gunakan ukuran font yang mirip-mirip (misal 17px, 16px, 15px bertumpuk).

### 1.3 Motion & Interaction Slop
1. **No Purposeless Bouncing / Continuous Floating**:
   - Dilarang menggunakan animasi berulang tanpa henti (misal tombol bergoyang terus-menerus).
   - Animasi hanya digunakan untuk *state transition* fungsional (e.g. check-in transition, modal sheet open/close) dengan durasi singkat (150ms - 250ms).

---

## 2. 📝 Kriteria AI Slop pada Copywriting, Teks & Dokumentasi

1. **Strict No-Emoji Policy**:
   - **Dilarang keras menyisipkan emoji** pada:
     - Nama variabel, fungsi, file, route, dan commit message.
     - Teks antarmuka mobile (label tombol, dialog error, header, deskripsi task harian).
     - Log sistem dan respons teknis.
   - Gunakan kata-kata yang lugas, profesional, dan berbobot.
2. **No Corporate Buzzword / Sycophantic Filler**:
   - Dilarang menulis teks klise AI seperti:
     - *"Seamlessly empower your daily routine with next-gen insights"*
     - *"Unlock your true potential today"*
     - *"As an AI lifestyle mentor, I am pleased to assist you"*
   - Tulis secara langsung, ringkas, dan fokus pada instruksi (*actionable microcopy*).
3. **No Redundant UX Writing**:
   - Dilarang membuat label, sublabel, helper text, dan placeholder yang mengulang kalimat yang sama dengan variasi tipis. Tulis sekali dengan jelas.
4. **Non-Judgmental Tone**:
   - Jangan pernah menampilkan teks yang menghakimi kegagalan user (*"You failed your goal"*, *"Streak broken"*).
   - Gunakan kalimat observasional yang adaptif (*"Target hari ini meleset. Rencana besok telah disesuaikan"*).

---

## 3. 💻 Kriteria AI Slop pada Rekayasa Kode (Code & Engineering)

1. **Zero Hallucinated APIs / Libraries**:
   - Jangan pernah mengimpor fungsi, method, atau package yang tidak nyata ada di ekosistem/SDK yang digunakan.
   - Selalu verifikasi API signature dan ketersediaan method sebelum memanggilnya.
2. **Zero Silent Failures (`catch (e) {}` Kosong)**:
   - Dilarang menelan error secara diam-diam. Setiap blok `try-catch` wajib memiliki logging kontekstual, error state update, atau recovery strategy.
3. **Zero "Fake Finished" Mock Masquerade**:
   - Dilarang membuat service yang hanya mengembalikan array dummy statis lalu menandai tugas sebagai "selesai diimplementasi".
   - Jika fitur membutuhkan database / algoritma, implementasikan alur logikanya secara nyata hingga ke data store.
4. **Zero Unhandled Edge Cases (Defensive Engineering)**:
   - Wajib menangani kasus nyata:
     - *Midnight rollover*: Jam tidur pukul 02.30 AM dihitung sebagai siklus tidur malam sebelumnya.
     - *Timezone changes*: Perubahan zona waktu saat bepergian.
     - *Offline queue drops*: Data tracking tidak boleh hilang saat koneksi terputus.
     - *Zero/Negative inputs*: Budget Rp0 atau input berat badan tidak masuk akal.
5. **No Premature Over-Engineering & Boilerplate Bloat**:
   - Hindari membuat 5 lapis kelas abstrak / factory / generic adapter jika kebutuhan saat ini hanya satu operasi sederhana yang jelas.
   - Utamakan kode yang bersih, mudah dibaca (*readable*), dan mudah diuji (*testable*).
6. **No "TODO Implement Later" in Production Code**:
   - Jangan meninggalkan placeholder fungsi setengah matang di alur kerja utama. Jika ada batasan fase, definisikan fallback yang aman.

---

## 4. 🧪 Checklist Verifikasi Anti-Slop Sebelum Commit / Release

- [ ] Apakah ada emoji yang tidak sengaja tertulis di kode, teks UI, atau commit message? **(Harus Bersih)**
- [ ] Apakah UI menggunakan warna beralasan tanpa gradasi ungu/neon AI dan tanpa glassmorphism berlebihan?
- [ ] Apakah ada kartu dengan garis tebal di samping atau nesting kartu lebih dari 2 lapis?
- [ ] Apakah semua endpoint dan fungsi benar-benar terhubung ke state/database nyata tanpa fake mock data tersembunyi?
- [ ] Apakah semua `try-catch` menangani dan mencatat error dengan benar?
- [ ] Apakah perhitungan waktu (tidur/bangun/jadwal) sudah menangani kasus penyeberangan tengah malam?
- [ ] Apakah bahasa/copy di aplikasi terasa manusiawi, ringkas, dan bebas dari buzzword klise AI?
