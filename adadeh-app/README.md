# ADADeH

Purwarupa web indikasi deepfake audio menggunakan model asli Kaggle, **tanpa training ulang**. Implementasi bertahap mengikuti `PLAN.md` yang telah disetujui.

> **Checkpoint pengembangan, bukan rilis produksi.** Unggah audio dan inferensi sudah diimplementasikan. Fitur mikrofon serta analisis bagian setelah empat potongan awal telah diminta pengguna, tetapi **belum diimplementasikan pada checkpoint ini**. Kontrak di bawah menjelaskan perilaku kode yang ada, bukan penolakan terhadap permintaan perubahan tersebut.

## Kontrak yang sudah diimplementasikan

- Model `adadeh_cnn.keras` dan `meta.json`; TensorFlow/Keras, bukan konversi PyTorch.
- Maksimal **empat chunk awal**: chunk 2,5 detik, stride 1,25 detik; cakupan maksimum **6,25 detik**. Ekor yang tidak lengkap dibuang. Audio panjang **tidak diperiksa seluruhnya**.
- `fake` adalah kelas indeks 1; rata-rata skor chunk; `p > 0.5099999999999999` berarti deepfake.
- Tidak ada silence trimming, denoise, padding, ataupun normalisasi level waveform tambahan.
- Peringatan mutu merupakan analisis terpisah; tidak mengubah input model.

## Status tahap

| Tahap | Hasil nyata |
| --- | --- |
| 0 — Persetujuan kontrak | Selesai. Keputusan pengguna tercatat di PLAN Bagian 0. |
| 1 — Loader dan parity fitur | **2 tes lulus**: metadata/normalisasi dan model asli pada seluruh test NPZ. CM chunk `[[299,6],[0,202]]`, CM file `[[136,4],[0,140]]` cocok notebook; AUC cocok dalam toleransi. Model dimuat `compile=False, safe_mode=True`; tidak training. |
| 2–5 — Audio, layanan, UI, evaluasi | Kode tersedia beserta tes unit, parity, integrasi, dan UI. Validasi keseluruhan belum selesai; bukan rilis terverifikasi penuh. |

Evaluasi CLI nyata juga sudah dijalankan: `scripts/evaluate_model.py`. Pada 280 file test, akurasi 98,571429%, F1 fake 98,591549%, ROC-AUC 0,997142857 dan **EER 1,428571%**. EER ini hasil hitung baru dari skor model lokal, bukan angka EER yang pernah diekspor notebook. Detail dan score vector lokal ada di `artifacts/evaluation/test-report.json` dan `local-score-reference.npz`.

## Usulan ambang peringatan mutu

Default engineering berikut terpisah dari model dan **belum divalidasi sebagai ambang mutu proyek**: frame 20 ms; dominasi keheningan jika ≥90% frame memiliki RMS <−50 dBFS; level rendah jika RMS rekaman <−35 dBFS; indikasi clipping jika ≥1% sampel mempunyai amplitudo absolut ≥0,999. Audio valid yang hanya menyediakan satu chunk (<3,75 detik) mendapat peringatan singkat. Tidak ada estimasi SNR/detektor derau tinggi yang diklaim akurat. Warning tidak mengubah waveform, fitur, threshold, atau skor model.


**Batas bukti:** belum ada `pip freeze` training atau audio mentah dengan golden score dari Kaggle. Parity fitur NPZ tidak membuktikan decoder/resampler audio mentah sama dengan runtime training asli. Versi di bawah adalah runtime aplikasi yang diuji, bukan klaim versi training.

## Lingkungan yang diuji

Windows x64, Python 3.11, TensorFlow 2.21.0, Keras 3.13.2, NumPy 2.4.6, scikit-learn 1.9.1, pytest 9.2.0. Python metadata notebook adalah 3.13.15; runtime aplikasi berbeda dan kesesuaian model diperiksa melalui tes, bukan diasumsikan.

### Instalasi Windows

Gunakan lingkungan virtual berpath pendek. Instalasi TensorFlow di `.venv` pada path repo ini gagal karena Windows LongPathsEnabled=0; konfigurasi Windows/registry tidak diubah. Lingkungan yang berhasil dibuat di `$HOME/.venvs/adadeh`.

PowerShell, dari folder `adadeh-app`:

```powershell
py -3.11 -m venv "$env:USERPROFILE\.venvs\adadeh"
$python = "$env:USERPROFILE\.venvs\adadeh\Scripts\python.exe"
& $python -m pip install -e ".[dev]"
```

`requirements.lock` mencatat lingkungan lokal yang diuji, bukan lingkungan training. Untuk memasang versi transitif yang tercatat, gunakan `& $python -m pip install -r requirements.lock` sebelum memasang paket aplikasi. Artefak model dan FFmpeg perlu disiapkan terpisah seperti di bawah.

### Artefak model

```powershell
kaggle kernels output japrul/tpdk-rek-sismul -p ./artifacts/kaggle_output
```

Seluruh `artifacts/`, lingkungan virtual, dan cache diabaikan Git. Jangan menambahkan model/dataset dengan `git add -f`.

CLI Kaggle harus tersedia dan sudah diautentikasi untuk perintah unduh tersebut. Jangan menaruh kredensial Kaggle di repositori.

### Runtime audio dan menjalankan aplikasi

```powershell
& $python scripts/setup_ffmpeg.py
& $python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Buka `http://127.0.0.1:8501`, tunggu persiapan model selesai, lalu unggah WAV, FLAC, MP3, M4A, atau OGG. Analisis dimulai otomatis. Di Windows, `start_app.cmd` merupakan launcher alternatif yang memakai lingkungan virtual di atas; `ADADEH_PYTHON` dapat diisi untuk memakai interpreter lain. Model dan runtime FFmpeg tidak disertakan dalam Git.

### Pengujian

```powershell
& $python -m pytest tests/unit/test_contracts.py tests/parity/test_model_artifact.py -q
& $python -m pytest tests -q
```

Loader memeriksa SHA-256 model dan metadata. Tidak ada fallback otomatis ke `best.keras`. Hasil akhir tetap merupakan indikasi awal, bukan pemeriksaan forensik ahli atau probabilitas kebenaran yang terkalibrasi.

### Pekerjaan tertunda dan batas keamanan

- Mikrofon dan analisis seluruh rekaman belum tersedia; aplikasi masih memakai empat potongan awal. Dua tes WIP untuk perubahan itu tetap lokal dan tidak disertakan pada checkpoint ini.
- Review independen menandai risiko kehabisan memori pada resampling untuk laju sampel tidak lazim. Pengaman alokasi kernel belum dipasang. Untuk uji lokal sementara, gunakan audio 16 kHz, 44,1 kHz, atau 48 kHz; jangan membuka layanan ini ke publik atau menerima unggahan yang tidak dipercaya.
- Pengujian browser otomatis belum selesai. Skrip opsional `scripts/browser_smoke.py` memerlukan Playwright, browser Chrome/Edge, serta artefak audio/evaluasi lokal; skrip tersebut bukan bukti bahwa seluruh alur browser telah lulus.
- Percobaan suite pra-commit mencapai batas waktu 180 detik sebelum selesai. Checkpoint ini tidak mengklaim suite akhir lulus atau review keamanan bersih.
