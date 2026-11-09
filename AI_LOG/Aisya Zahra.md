# Pekerjaan Visualisasi Person 5

Catatan ini merangkum permintaan perbaikan **Interactive NBA Half-Court & Shot Chart**.

## Tujuan pekerjaan

Menyempurnakan visualisasi lapangan, persebaran tembakan, agregasi area, tooltip, dan interaksi pendukung keputusan sesuai tanggung jawab **Person 5 — Data Visualization Specialist**.

Ruang lingkup pekerjaan berpusat pada tab **Shot Explorer**. Implementasi mengikuti framework Streamlit, struktur proyek, integrasi data/API, dan model prediksi yang tersedia. Dataset aktual menjadi sumber seluruh visualisasi.

Hasil yang dituju mencakup lapangan proporsional, posisi shot akurat, kontrol yang mudah digunakan, statistik yang mengikuti filter, serta tampilan desktop, tablet, dan mobile yang responsif.

## Temuan pemeriksaan awal

- Implementasi awal di `charts.py` menggunakan scatter Plotly dasar dengan tooltip pemain, zona, dan koordinat.
- Restricted area, separuh belakang lingkaran free throw, mode agregasi, serta interaksi pemilihan area memerlukan penyempurnaan.
- Kontrak data proyek menetapkan `LOC_X` dan `LOC_Y` dalam persepuluh kaki. Konversi menjadi kaki menggunakan pembagian dengan 10, dengan basket sebagai origin `(0, 0)`.
- Label corner three pada data aktual mengonfirmasi X negatif di sisi kiri dan X positif di sisi kanan. Y positif mengarah ke midcourt.
- Dataset yang diperiksa memuat **218.701 attempts**, dengan **218.266 attempts** di dalam batas half-court dan **435 attempts** di luar batas tampilan. Koordinat invalid berjumlah **0**.
- Parquet yang diperiksa belum menyediakan kolom predicted probability per shot.

## Keputusan terakhir dan implementasi

### Geometri dan koordinat

- Menggunakan komponen lokal Streamlit dengan lapangan **SVG** dan marker scatter pada **canvas**.
- Half-court berukuran 50 × 47 kaki. Boundary, baseline, paint/key, free-throw line dan circle, three-point arc dan corner lines, restricted area, backboard, serta basket dirender dalam sistem koordinat yang konsisten.
- SVG memakai `viewBox="-27 -43.75 54 51"` dan `preserveAspectRatio="xMidYMid meet"`. SVG, canvas, dan pencarian shot melalui pointer menggunakan transformasi yang sama.
- Garis lapangan ditempatkan di atas marker dan sel agregasi, dengan halo gelap agar terbaca pada data padat.
- Seluruh shot yang dapat dipetakan dirender. Opacity disesuaikan terhadap kepadatan data.
- Shot dengan koordinat invalid atau di luar half-court dilaporkan melalui coverage. Attempts tersebut tetap masuk dalam total zona sumber dengan lokasi asli yang dipertahankan.

### Mode visualisasi

- **Scatter shots** membedakan made melalui lingkaran berwarna biru muda dan missed melalui tanda silang berwarna oranye. Hover, fokus, dan pilihan shot memperoleh highlight.
- **Hexbin heatmap** dipilih sebagai pendekatan agregasi. Grid beradius 2 kaki ditambatkan pada basket sehingga posisi sel konsisten ketika filter berubah.
- Heatmap menyediakan metrik **attempts** dan **FG%**. FG% dihitung dari made dibagi attempts pada setiap sel berdasarkan data terfilter.
- Area kosong menggunakan pola khusus, sedangkan sel dengan attempts dan 0 made memperoleh nilai FG% sebesar 0%.
- **Expected points** dihitung sebagai probability × nilai tembakan 2 atau 3 poin. Agregasi menampilkan rata-rata expected points per attempt dengan input prediksi valid dan jumlah coverage yang terlihat.
- Probability pecahan memakai skala 0–1. Kolom persen yang ditandai secara eksplisit dikonversi dari skala 0–100. Nilai di luar skala ditandai invalid.
- Pada dataset yang diperiksa, mode expected points menampilkan status **unavailable** karena probability per shot belum tersedia. Pengujian mode dengan prediksi tersedia menggunakan keluaran model tersimpan pada shot aktual dalam sesi browser pengujian.

### Interaksi dan tampilan

- Pengguna dapat memfilter zona sumber, memilih sel hexbin atau shot, melihat statistik terkait, dan menghapus pilihan.
- Kontrol minimum sample size menampilkan nilai aktif. Sel di bawah threshold diredupkan dan diberi pola serta keterangan **“sampel belum mencukupi”**.
- FG% dilengkapi **95% Wilson confidence interval** berdasarkan made dan attempts. Statistik model menampilkan probability dan expected points beserta coverage tersendiri.
- Tooltip shot menampilkan pemain, hasil, tipe/zona, jarak dalam kaki, periode, waktu tersisa, probability, dan expected points sesuai ketersediaan data.
- Tooltip area menampilkan identitas sel, attempts, made, FG%, Wilson CI, statistik prediksi, dan kecukupan sampel.
- Interaksi mendukung hover mouse, tap, fokus keyboard, tombol panah, Enter/Space untuk memilih, dan Escape untuk menghapus pilihan.
- Legenda berada di luar lapangan. Panel statistik tersusun di bawah lapangan pada layar kecil. Komponen menyediakan loading, empty, dan error state.
- Filter sidebar, pilihan zona/sel, tooltip, legenda, dan ringkasan statistik memakai data yang sama. Kartu zona juga menampilkan benchmark FG% liga berdasarkan filter quarter dan shot type.
- Komponen menggunakan aset lokal dan paket runtime proyek. Playwright digunakan sebagai alat verifikasi browser lokal.

## File yang diubah dalam pekerjaan visualisasi

| File | Perubahan |
| --- | --- |
| `app.py` | Menghubungkan tab Shot Explorer dengan komponen visualisasi dan benchmark liga. |
| `charts.py` | Menyiapkan data visualisasi, geometri, validasi koordinat/probability, coverage, dan adapter komponen Streamlit. |
| `visualization/index.html` | Menyediakan struktur SVG, kontrol mode/filter, legenda, inspector, tooltip, dan elemen aksesibilitas. |
| `visualization/style.css` | Mengatur gaya visual, layer, marker, pola sampel, tooltip, serta layout responsif. |
| `visualization/chart.js` | Mengimplementasikan rendering, hit testing, pemilihan shot/area, tooltip, keyboard/touch, dan sinkronisasi statistik. |
| `visualization/math.js` | Menghitung transformasi koordinat, grid/agregasi hexbin, FG%, Wilson CI, dan expected points. |
| `test_charts.py` | Menguji kontrak data visualisasi, koordinat, probability, coverage, dan keselarasan data aktual. |
| `visualization/math.test.js` | Menguji agregasi, perhitungan statistik, transformasi responsif, dan konservasi jumlah attempts/made. |
| `visualization/check_browser.py` | Memverifikasi interaksi, filter aktual, responsivitas, tooltip, prediction coverage, serta empty/error state melalui browser. |
| `docs/visualization.md` | Mendokumentasikan keputusan geometri, agregasi, interpretasi statistik, keterbatasan prediksi, dan cara verifikasi. |

## Hasil verifikasi pada akhir pekerjaan yang dirujuk

- **36 tes Python lulus**, termasuk alur aplikasi dan pemeriksaan koordinat pada data aktual.
- **6 tes JavaScript lulus**, termasuk pemeriksaan jumlah attempts dan made shots pada seluruh musim serta filter zona sumber.
- Pemeriksaan sintaks JavaScript, kompilasi Python, dan diff perubahan berhasil.
- Pengujian browser lulus untuk desktop, tablet, layar sentuh 390 px, dan lebar 320 px dengan proporsi lapangan terjaga serta layout tanpa overflow horizontal.
- Pemilihan/reset, threshold sampel, tooltip dalam viewport, keyboard, touch, dan filter pemain aktual berhasil diverifikasi.
- Expected points dari prediksi model tersimpan sesuai perhitungan pada shot aktual. Status unavailable serta pemulihan empty/error state juga terverifikasi.
- Pemeriksaan browser selesai tanpa page error atau console error baru.
- Suite Python melaporkan satu `SettingWithCopyWarning` pada pengujian ETL di `etl/pipeline.py`.

## Status akhir dan keterbatasan data

Implementasi visualisasi telah selesai dan terverifikasi pada data aktual.

Interpretasi statistik tetap memperhatikan ukuran sampel, coverage koordinat, dan coverage prediksi. Data mencakup NBA 2023/24 regular season. Expected points mencakup nilai field goal dari probability dan shot value, dengan konteks defender, shot clock, free throw, dan possession lanjutan yang terbatas pada data proyek.
