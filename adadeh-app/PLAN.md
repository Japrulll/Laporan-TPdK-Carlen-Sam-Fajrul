# PLAN — Aplikasi ADADeH

**Status: DISETUJUI PENGGUNA; IMPLEMENTASI BERTAHAP. Pelatihan ulang tetap tidak diizinkan.**

Lokasi aplikasi: `adadeh-app/`, sebagai folder saudara dari `Proposal-TA-template-v2-APA/`. Dokumen ini mengatur pekerjaan setelah persetujuan, bukan menyatakan fitur atau pengujian aplikasi sudah selesai.

## 0. Keputusan yang disetujui pengguna

- Q1: gunakan TensorFlow/Keras, `adadeh_cnn.keras` dan `meta.json`, tanpa konversi atau training ulang.
- Q2: untuk sekarang, kompatibilitas persis notebook: maksimum empat chunk awal, ekor tidak lengkap dibuang. Rentang yang diperiksa wajib terlihat; aplikasi tidak boleh mengklaim seluruh rekaman sudah dianalisis. Kebutuhan cakupan menyeluruh KP-06/KF-07 dicatat sebagai deviasi yang disetujui untuk versi ini.
- Q3: pertahankan threshold ekspor dan operator `>`, bukan `>=`.
- Q4: freeze lingkungan training dan audio referensi belum tersedia. Lakukan verifikasi model pada NPZ; kesetaraan audio mentah dengan runtime Kaggle asli tetap belum terbukti. Versi lingkungan aplikasi dicatat sebagai versi yang diuji, bukan versi training yang diketahui.
- Q5: ambang warning mutu boleh diusulkan terpisah. Analisis mutu tidak mengubah waveform yang masuk ke model dan tidak boleh dipresentasikan sebagai parameter training.

Status implementasi dan hasil tes aktual dicatat di README. Bagian audit berikut mempertahankan temuan sebelum implementasi; daftar pertanyaan awal dibaca bersama keputusan di atas.

## 1. Dasar spesifikasi dan batas pekerjaan

### 1.1 Sumber yang diperiksa

1. **Sumber utama:** `../Proposal-TA-template-v2-APA/ProposalTA.pdf`, 66 halaman. Seluruh halaman, termasuk daftar, pustaka, Bab IV–V, dan lampiran, telah dibaca. Referensi halaman dalam plan adalah **nomor halaman PDF**, bukan nomor cetak. SHA-256: `18bd36d7528a68ef2fab23a3b67feb4f163b99b2e851d08c4a937f893f42ffb7`.[1]
2. Notebook lampiran `tpdk-rek-sismul.ipynb`, 20 sel; penomoran sel di dokumen ini dimulai dari **0**. Salinannya berada di `artifacts/reference_notebooks/`. Sel kode cocok dengan notebook yang ditarik langsung dari Kaggle. Berkas `.virtual_documents/__notebook_source__.ipynb` ternyata berisi teks Python, bukan JSON notebook; perbedaannya hanya konversi perintah terminal `!ls` menjadi pemanggilan IPython.[2][5]
3. Semua keluaran kernel `japrul/tpdk-rek-sismul` berhasil diunduh. `meta.json`, konfigurasi di dalam arsip `.keras`, riwayat training, dan tiga split `.npz` diperiksa sebagai data tanpa mengeksekusi notebook atau mendeserialisasi model.[3][4][5]
4. PDF terpisah `Kelompok 1_Laporan Akhir TPdK_Bab I.pdf` merupakan versi Bab I saja, bukan pengganti laporan lengkap. `README.md` di folder laporan menjelaskan kompilasi LaTeX, bukan aplikasi.

**Urutan keputusan:** laporan menentukan kebutuhan produk; artefak dan kode training menentukan kontrak numerik model yang sudah dilatih. Pertentangan keduanya harus diputuskan secara eksplisit. Tidak akan mengubah laporan, mengganti model, mengubah threshold, mengonversi model ke framework lain, atau melatih ulang secara diam-diam.

### 1.2 Kondisi repositori

- Branch `main`, commit dasar `ecdfc1096ac6a51b9161685f3d60a9d22faadbc1` (`[update]: Bab III`). Ada perubahan format laporan lokal yang belum di-commit; pekerjaan aplikasi tidak boleh menimpa perubahan tersebut.
- Struktur awal berisi laporan LaTeX/PDF, aset gambar, contoh listing template, `.agents/`, dan metadata macOS. Belum ada paket aplikasi, dependency manifest Python, test suite, CI aplikasi, ataupun konvensi aplikasi yang dapat diwarisi.
- Bab IV pada PDF hlm. 57 dan Bab V pada hlm. 59 masih berupa instruksi template. Lampiran hlm. 65 membahas sensor ultrasonik dan contoh binary search, bukan implementasi ADADeH. Materi tersebut **tidak** diterjemahkan menjadi fitur aplikasi.[1]
- Aplikasi ditambahkan secara modular di `adadeh-app/`. Nama modul/variabel/kode memakai bahasa Inggris; UI, dokumentasi, pesan galat, dan laporan tahap memakai Bahasa Indonesia.
- Saat tahap perencanaan ini, hanya `PLAN.md`, `.gitignore`, dan berkas bukti/unduhan dalam `artifacts/` yang disiapkan. Struktur kode pada Bagian 6 masih rencana.

## 2. Ringkasan aplikasi menurut laporan

### 2.1 Tujuan, pengguna, dan ruang lingkup

ADADeH adalah purwarupa web untuk memberi **indikasi awal** apakah rekaman suara tergolong asli atau deepfake. Pengguna utama adalah masyarakat awam; pengguna pendamping memerlukan ringkasan hasil yang dapat disimpan. Aplikasi tidak mengidentifikasi pelaku atau metode pembentukan deepfake, dan hasilnya tidak menggantikan pemeriksaan forensik ahli. Cakupan generalisasi bahasa Indonesia dan teknik di luar dataset belum terbukti. Laporan menetapkan Streamlit dan pemrosesan di server, dengan laptop tanpa GPU khusus sebagai sasaran inferensi.[1]

Tidak ada kebutuhan yang menetapkan akun pengguna, database riwayat, pembayaran, browser extension, API publik terpisah, atau analisis streaming langsung. Fitur tersebut tidak masuk rencana. Sebutan browser extension pada pengantar notebook tidak mengalahkan ruang lingkup aplikasi web dalam laporan.[1][2]

### 2.2 Input, output, dan alur pengguna

- **Input yang diminta laporan:** satu berkas WAV, FLAC, MP3, M4A, atau OGG; maksimum 100 MB dan 10 menit; minimum satu potongan model. Dari artefak, satu potongan berdurasi 2,5 detik. Angka minimum merupakan penggabungan kebutuhan laporan dengan parameter model, bukan angka baru dari laporan.[1][3]
- **Output:** label “Terindikasi asli” atau “Terindikasi deepfake”, skor/keyakinan model, peringatan mutu jika relevan, dan batas penafsiran hasil.[1]
- **Ringkasan unduhan wajib:** nama berkas, durasi, waktu pemeriksaan, SHA-256 berkas, label, skor, versi model, dan batasan hasil. Format JSON dan teks UTF-8 diusulkan; laporan tidak menentukan format unduhannya.[1]
- **Alur:** membuka halaman → mengunggah berkas → membaca hasil. Pemeriksaan, preprocessing, prediksi, dan agregasi berjalan otomatis; tidak menambah tombol analisis wajib yang menjadikan alurnya empat langkah. Jika gagal, pengguna mendapat penyebab dan cara memperbaiki masukan.[1]
- **Usulan transparansi tambahan:** tampilkan durasi audio asli, rentang yang benar-benar diperiksa, dan jumlah potongan. Ini bukan fitur wajib yang diklaim berasal dari laporan; tujuannya mencegah potongan awal disalahartikan sebagai analisis seluruh rekaman.

### 2.3 Pemetaan kebutuhan fungsional ke fitur

Semua kebutuhan berikut masih **akan dibangun**, bukan sudah terimplementasi. Tabel III.7 berada pada PDF hlm. 51–52.[1]

| ID | Kebutuhan laporan | Fitur/rencana dan kriteria penerimaan |
| --- | --- | --- |
| KF-01 | Unggah WAV, FLAC, MP3, M4A, OGG melalui peramban. | Uploader satu berkas; masing-masing format mempunyai uji decode yang nyata, bukan hanya filter ekstensi. |
| KF-02 | Periksa ukuran/durasi dan pastikan isi benar-benar audio; jelaskan penolakan. | Validasi byte, metadata, dan decode terbatas; uji berkas kosong, rusak, salah ekstensi, terlalu besar, terlalu pendek, dan terlalu panjang. |
| KF-03 | Mono, sample rate training, dan perlakuan keheningan yang sama dengan training. | Rata-rata kanal lalu resample TorchAudio menjadi 16 kHz; **tidak memangkas keheningan**, karena kode training tidak melakukannya. |
| KF-04 | Potongan sesuai input model; ekor mengikuti aturan training. | Potongan 40.000 sampel, langkah 20.000; kontrak asli membuang ekor yang tidak lengkap dan membatasi empat potongan, sesuai keputusan Q2 di Bagian 0. |
| KF-05 | Mel-spectrogram dB dan normalisasi statistik training. | Array numerik `float32` berukuran 128 × 157; gunakan `mu`/`sd` ekspor, bukan statistik unggahan. |
| KF-06 | CNN terlatih menghasilkan skor per potongan. | Muat `adadeh_cnn.keras`; ambil kolom kelas `fake`; tidak melakukan training atau tambahan sigmoid. |
| KF-07 | Gabungkan semua skor potongan dan pakai threshold validasi. | Rata-rata aritmetika skor potongan yang disetujui dalam kebijakan cakupan; threshold ekspor dipertahankan. |
| KF-08 | Label awam, skor persen, dan penjelasan singkat. | Pemetaan `real/fake` ke label Bahasa Indonesia; skor model tidak disebut kepastian keaslian. |
| KF-09 | Selalu tampilkan keterbatasan model dan sifat indikasi awal. | Disclaimer muncul bersama hasil dan di ekspor, tidak hanya di halaman informasi terpisah. |
| KF-10 | Peringatan terlalu singkat, dominasi keheningan, clipping, dan level rendah. | Analisis mutu terpisah dari waveform yang diberikan ke model; ambang mutu harus ditetapkan dan diuji, bukan dikarang sebagai parameter training. |
| KF-11 | Unduh ringkasan hasil dengan delapan kelompok informasi yang ditentukan. | Ekspor JSON/TXT yang diusulkan, SHA-256 dihitung dari byte unggahan asli; versi model diikat ke hash model dan metadata. |
| KF-12 | Hapus unggahan dan data antara seusai proses/sesi. | Utamakan buffer memori dan temporary directory per permintaan; cleanup pada sukses, galat, dan pembatalan; tidak ada cache global untuk audio pengguna. |

### 2.4 Kebutuhan nonfungsional dan cara membuktikannya

Tabel III.8 berada pada PDF hlm. 53–54. Batas waktu/durasi/ukuran masih disebut sebagai batas awal yang dapat disesuaikan berdasarkan pengujian, bukan alasan untuk mengubahnya tanpa persetujuan.[1]

| ID | Ketentuan laporan | Bukti kelulusan yang harus dihasilkan |
| --- | --- | --- |
| KNF-01 | Akurasi dan F1 kelas deepfake ≥90%; EER ≤10% pada test terpisah. | Evaluasi model beku pada split test yang sudah tersedia; bedakan metrik per chunk dan per file; laporkan EER sebenarnya. |
| KNF-02 | Rekaman ≤60 detik selesai ≤10 detik setelah unggahan; audio lebih panjang mempunyai indikator kemajuan. | Benchmark decode sampai hasil pada hardware acuan yang disepakati; catat cold start dan warm run secara terpisah. Tabel spesifikasi laptop dalam laporan masih kosong. |
| KNF-03 | Minimum satu potongan; maksimum 10 menit/100 MB. | Uji tepat di batas dan di kedua sisinya. Batas byte yang diusulkan: 100.000.000 byte; konvensi MB ini perlu disetujui. |
| KNF-04 | HTTPS dan WSS bila diakses melalui jaringan publik. | Uji konfigurasi reverse proxy/TLS dan koneksi WebSocket. HTTP localhost tidak dinyatakan sebagai kelulusan penerapan publik. |
| KNF-05 | Audio tidak disimpan permanen, tidak dikirim ke pihak ketiga, tidak dicatat pada log. | Inspeksi disk/cache/log dan uji koneksi keluar saat inferensi. Unduhan model saat persiapan dipisahkan dari pemrosesan audio pengguna. |
| KNF-06 | Bahasa Indonesia, istilah awam, maksimum tiga langkah. | Uji alur membuka–mengunggah–membaca; evaluasi keterpahaman pengguna dengan skenario yang disepakati. |
| KNF-07 | Peramban modern di laptop dan ponsel, tanpa instalasi klien. | Uji viewport desktop/mobile dan peramban sasaran; dukungan klien nyata dicatat, tidak disimpulkan hanya dari penggunaan Streamlit. |
| KNF-08 | Konfigurasi preprocessing/normalisasi/threshold bersama bobot; skor notebook dan aplikasi identik. | `meta.json` menjadi otoritas parameter; manifest mengikat pasangan model/config. Uji golden terhadap waveform, fitur, skor, dan label; toleransi numerik harus dinyatakan. |

### 2.5 Keterlacakan kebutuhan pengguna

Sembilan kebutuhan pengguna berada pada PDF hlm. 45–47; pemetaan berikut mengikuti Tabel III.9 pada PDF hlm. 55. KF-05, KF-06, dan KNF-08 merupakan kebutuhan teknis dari alternatif A2, bukan kebutuhan pengguna yang hilang.[1]

| ID | Kebutuhan pengguna, diringkas | Kebutuhan sistem terkait |
| --- | --- | --- |
| KP-01 | Pemeriksaan mandiri yang mudah diakses. | KF-01, KNF-06, KNF-07 |
| KP-02 | Rekaman perangkat sehari-hari diterima tanpa konversi manual. | KF-01, KF-02, KF-03, KNF-07 |
| KP-03 | Kesimpulan langsung dapat dipahami. | KF-08, KNF-06 |
| KP-04 | Keterbatasan hasil dijelaskan. | KF-09, KNF-01 |
| KP-05 | Hasil tersedia dalam waktu singkat. | KNF-02 |
| KP-06 | Rekaman panjang diperiksa secara menyeluruh. | KF-04, KF-07, KNF-03 |
| KP-07 | Peringatan mutu rekaman tersedia. | KF-02, KF-03, KF-10, KNF-03 |
| KP-08 | Kerahasiaan rekaman dijaga. | KF-12, KNF-04, KNF-05 |
| KP-09 | Pendamping dapat menyimpan ringkasan hasil. | KF-11 |

## 3. Hasil audit Kaggle dan notebook

### 3.1 Unduhan dan inventaris artefak

Perintah berikut benar-benar berhasil dari folder `adadeh-app/`:

```bash
kaggle kernels output japrul/tpdk-rek-sismul -p ./artifacts/kaggle_output
kaggle kernels pull japrul/tpdk-rek-sismul -p ./artifacts/kaggle_source -m
```

Status kernel yang diperiksa: `KernelWorkerStatus.COMPLETE`. CLI lokal memperingatkan bahwa versi Kaggle 2.0.0 sudah lebih lama; peringatan itu tidak menggagalkan unduhan. Tidak ada kegagalan kredensial yang dilewati.

Sembilan berkas keluaran berjumlah **240.121.444 byte**, sekitar **229,00 MiB**, tidak termasuk dua berkas hasil pull source. Semua keluaran di-hash dan tercatat di `artifacts/audit/artifact-audit.json`.[5]

| Berkas di `artifacts/kaggle_output/` | Ukuran byte | Peran/temuan |
| --- | ---: | --- |
| `adadeh_cnn.keras` | 1.391.412 | Model akhir yang diekspor sel 19; kandidat utama untuk aplikasi. |
| `best.keras` | 1.388.885 | Model berbeda; tanpa layer SpecAugment dan optimizer tersimpan berbeda. Tidak otomatis dipilih berdasarkan namanya. |
| `meta.json` | 218 | Normalisasi, threshold, sample rate, ukuran/langkah chunk, parameter mel, urutan kelas. |
| `history.json` | 4.543 | Lima deret riwayat, 46 epoch; bukan hasil test akhir. |
| `train.npz` | 167.071.454 | Fitur mel dB mentah, label, dan file ID training. |
| `val.npz` | 35.335.890 | Fitur/label/file ID validasi. |
| `test.npz` | 34.916.054 | Fitur/label/file ID test. |
| `.virtual_documents/__notebook_source__.ipynb` | 11.105 | Ekspor teks Python; bukan notebook JSON dan bukan pengganti bobot. |
| `tpdk-rek-sismul.log` | 1.883 | Log konversi notebook ke HTML; tidak berisi laporan metrik inferensi lengkap. |

Keluaran Kaggle tidak menyertakan waveform asli, golden prediction vector, `requirements.txt`, atau `pip freeze`. Notebook yang ditarik dari Kaggle mempunyai source yang sama dengan lampiran tetapi tidak membawa output sel. Output metrik yang dibahas di bawah berasal dari **lampiran pengguna**, bukan dari eksekusi ulang model saat audit.[2][5]

### 3.2 Pemilihan model dan struktur jaringan

- Usulan model utama: **`adadeh_cnn.keras` + `meta.json`**, karena pasangan ini diekspor bersama oleh sel 19 sesudah evaluasi. SHA-256 model: `adffd47c27d7dd14eca8d91e4de22dc366ab5d92d4e51c02138ab04e0863eb30`. SHA-256 metadata: `43ee9cb4331edc86b73f2a9b22c11461b949d61a7aedf9aa0d164f6cc8fcd793`.[2][5]
- Arsip berisi `metadata.json`, `config.json`, dan `model.weights.h5`; metadata menyatakan **Keras 3.13.2**, disimpan `2026-11-11@19:11:58` tanpa informasi zona waktu. Input `(None, 128, 157, 1)`, `float32`; output dua kelas softmax.[4][5]
- Jaringan: Input → SpecAugment → tiga blok Conv2D tanpa bias, BatchNormalization, ReLU, MaxPooling2D dengan filter 32/64/128 → GlobalAveragePooling2D → Dropout 0,4 → Dense 128 ReLU → Dropout 0,4 → Dense 2 softmax. Jumlah parameter yang dihitung dari konfigurasi adalah 110.114, termasuk 448 statistik BatchNorm nontrainable; ini perhitungan statis, belum verifikasi `model.count_params()`.[4][5]
- `best.keras` disimpan lebih awal, `2026-11-11@18:45:22`, tanpa SpecAugment; learning rate optimizer tersimpan sekitar 0,001, sedangkan model akhir sekitar 0,00001. Tidak ada dasar untuk memasangkan threshold model akhir dengan model alternatif tersebut tanpa evaluasi terpisah.[5]
- Loader setelah persetujuan akan memakai definisi custom layer SpecAugment dari sel 16, `custom_objects`, `compile=False`, dan `safe_mode=True`; tidak mengaktifkan deserialisasi lambda yang tidak aman. Model dipanggil dengan `training=False`, sehingga augmentasi, Dropout, dan pembaruan BatchNorm tidak berjalan sebagai training.[2][8]

### 3.3 Kontrak preprocessing dan postprocessing asli

Sel 8–11, 16–17, serta `meta.json` adalah sumber kontrak ini. Tidak diperlukan tokenizer, encoder teks, atau scaler terpisah; statistik normalisasi adalah dua skalar di metadata.[2][3]

| Langkah | Perilaku yang harus dipertahankan | Asal |
| --- | --- | --- |
| Decode | Dataset training memakai decoder audio Hugging Face berbasis TorchCodec; data berbentuk kanal × sampel. Versi decoder/FFmpeg belum tercatat. | Output sel 3; sel 11. |
| Mono | `s.data.mean(0, keepdim=True)`; rata-rata kanal sebelum resampling. | Sel 11. |
| Sample rate | Jika berbeda, `torchaudio.functional.resample` ke **16.000 Hz**; bukan `librosa.load` dengan sample rate default atau resampler lain. | Sel 11; metadata. |
| Potongan | `chunk_dur=40000` sampel = **2,5 detik**; `step=20000` = **1,25 detik**; overlap 1,25 detik; `max_chunk=4`. | Sel 8; metadata. |
| Banyak potongan | `n = min((len(y)-40000)//20000 + 1, 4)`; potongan diambil dari awal rekaman. | Sel 11. |
| Ekor/masukan singkat | Ekor yang tidak membentuk chunk lengkap dibuang. Tidak ada padding untuk audio <2,5 detik; kode training akan menghasilkan daftar chunk kosong. Aplikasi sebaiknya menolak audio terlalu singkat dengan galat yang jelas. | Sel 11; KNF-03. |
| Keheningan dan level | Tidak ada silence trimming, denoise, peak normalization, atau loudness normalization. Jangan menambahkannya ke jalur model. | Sel 11. |
| Mel | `librosa.feature.melspectrogram`, `n_fft=1024`, `hop_length=256`, `n_mels=128`, `fmax=8000`. | Sel 11; metadata. |
| dB | `librosa.power_to_db(mel, ref=1.0, top_db=80)` untuk setiap chunk. | Sel 11. |
| Array | Stack numerik `(n,128,157)` menjadi `float32`, tambah dimensi kanal terakhir menjadi `(n,128,157,1)`. Bukan citra PNG/RGB dan tidak di-resize. | Sel 11 dan 16; konfigurasi model. |
| Normalisasi | `(x - mu) / (sd + 1e-8)` dengan **`mu=-28.45931625366211`**, **`sd=16.406835556030273`**. Tidak dihitung ulang dari unggahan. | Sel 16; metadata. |
| Urutan kelas | `classes=["real","fake"]`: indeks 0 asli, indeks 1 fake. | Output sel 3; metadata. |
| Prediksi chunk | Ambil output softmax `[:,1]`. Jangan menambah sigmoid atau softmax kedua. | Sel 17. |
| Agregasi file | Rata-rata aritmetika skor chunk; bukan voting label, maksimum, atau pembobotan ulang overlap. | Sel 17. |
| Threshold | Nilai persis tersimpan **`0.5099999999999999`**. Keputusan asli: `p_file > threshold`; nilai yang sama dengan threshold masuk kelas `real`. | Sel 17; metadata. |
| Keyakinan UI | Laporan mendefinisikan `c=max(p_file,1-p_file)`; tampilkan sebagai skor model yang belum terkalibrasi. Karena threshold bukan 0,5, skor ini tidak selalu sama dengan probabilitas kelas yang dipilih. | Laporan PDF hlm. 30 dan 52–53. |

**Default library belum boleh dianggap sebagai parameter training yang terbukti.** Kode tidak menuliskan `win_length`, `window`, `center`, `pad_mode`, `power`, `fmin`, `htk`, `norm`, `amin`, atau parameter kernel resampling. Dokumentasi yang diperiksa menunjukkan default API, tetapi tidak membuktikan versi yang dipakai ketika artefak dibuat. Setelah versi runtime dipastikan, semua default efektif dikunci secara eksplisit dan diperiksa menggunakan golden fixture. Tidak mengganti resampler hanya agar dependensi lebih sedikit.[9][10]

**Temuan presisi:** perhitungan ulang mean `train.npz` pada runtime audit menghasilkan `-28.45929718017578`, berbeda `0.000019073486328125` dari ekspor; standard deviation cocok. Penyebab perbedaan belum dibuktikan. Nilai di `meta.json` tetap menjadi acuan; plan tidak menggantinya dengan hasil hitung mesin audit. Perbedaan ini perlu tercakup dalam uji numerik lintas runtime.[3][5]

### 3.4 Data, training, dan hasil yang benar-benar tersedia

Notebook memuat `garystafford/deepfake-audio-detection` dari Hugging Face, bukan memuat dataset melalui Kaggle API. Data sumber mempunyai 1.866 rekaman dan dua kelas. Source masih memanggil `tr`, `va`, `te` tanpa sel pembentukan indeksnya; seed dan perintah split tidak dapat direkonstruksi dari notebook yang tersimpan. Untuk evaluasi model beku, split aktual tetap tersedia melalui `file_id` dalam NPZ.[2][5]

| Split | Rekaman unik | Chunk | Chunk real / fake | Rekaman real / fake |
| --- | ---: | ---: | --- | --- |
| Training | 1.306 | 2.415 | 1.442 / 973 | 653 / 653 |
| Validasi | 280 | 512 | 301 / 211 | 140 / 140 |
| Test | 280 | 507 | 305 / 202 | 140 / 140 |

Ketiga split tidak mempunyai irisan `file_id`, label dalam setiap file konsisten, dan maksimum empat chunk per file. Ini membuktikan pemisahan berdasarkan file ID yang tersedia, **bukan** pemisahan speaker atau bebas duplikasi akustik. Fitur NPZ adalah mel dB sebelum normalisasi, dengan label/file ID `int64`.[5]

Training sel 16 memakai Adam awal `3e-4`, sparse categorical cross-entropy, class weight seimbang, batch 64, maksimum 60 epoch, EarlyStopping `patience=10` dengan `restore_best_weights=True`, dan ReduceLROnPlateau. Riwayat berisi 46 epoch; val loss minimum pada epoch ke-36. Threshold dipilih dari 91 nilai antara 0,05–0,95 dengan memaksimalkan **macro-F1 pada chunk validasi**, bukan dituning pada test.[2][6]

Baseline berikut dibaca dari output sel 17 lampiran. Akurasi dan F1 dihitung ulang dari matriks konfusi yang tercetak; **model hasil unduhan belum dijalankan kembali untuk mengesahkan baseline tersebut**.[2]

| Tingkat | Matriks konfusi, urutan real/fake | Akurasi | F1 fake | ROC-AUC tercetak |
| --- | --- | ---: | ---: | ---: |
| Chunk | `[[299,6],[0,202]]`, 507 chunk | 98,816568% | 98,536585% | 0,9987015094952119 |
| File | `[[136,4],[0,140]]`, 280 file | 98,571429% | 98,591549% | 0,9971428571428571 |

**EER tidak dihitung atau diekspor oleh notebook.** ROC-AUC bukan EER. Target EER ≤10% dalam laporan belum boleh dinyatakan tercapai. Laporan sendiri hanya memuat target kinerja; angka EER 1,86% pada pembahasan alternatif adalah hasil literatur, bukan hasil ADADeH.[1][2]

### 3.5 Versi library dan resource

| Komponen | Yang diketahui | Tindak lanjut |
| --- | --- | --- |
| Python | Metadata notebook: `3.13.15`. | Titik awal reproduksi; bukan klaim interpreter lokal sudah cocok. |
| Keras | `3.13.2` dari metadata kedua model. | Usulan pin versi ini saat pemeriksaan kompatibilitas. |
| TensorFlow | Dipakai source training; versi tidak diekspor. | Dapatkan versi runtime asli atau verifikasi pasangan kompatibel sebelum penguncian dependency. |
| PyTorch/TorchAudio/TorchCodec | Dipakai decode/mono/resampling; versi belum diketahui. | Pertahankan jalur DSP, minta freeze lingkungan; jangan menganggap PyTorch adalah framework CNN ekspor. |
| librosa/NumPy/SciPy | Versi training belum diketahui. | Kunci versi dan default setelah uji parity; termasuk sensitivitas normalisasi float32. |
| datasets/FFmpeg | Decoder dan data loading terlibat, versi/revisi dataset belum dipin. | Perlukan identitas dataset/revisi dan waveform referensi untuk uji dari audio mentah. |
| Streamlit | Ditetapkan laporan, tidak ada aplikasi training yang mencatat versinya. | Pilih dan pin pada tahap implementasi; dokumentasi 1.55.0 hanya acuan perancangan. |

Konfigurasi kernel menyebut image `gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a` dan mesin `NvidiaTeslaT4`. Namun metadata notebook hasil pull menyebut akselerator `none`; metadata lampiran juga tidak konsisten antara nama akselerator dan flag GPU. Konfigurasi tersebut tidak dipakai untuk mengklaim resource aktual training atau latency CPU.[2][7]

Untuk aplikasi, sasaran tetap **inferensi CPU**, tanpa training. Bobot numerik model diperkirakan 440.456 byte dari jumlah parameter; ukuran paket TensorFlow, PyTorch, decoder, aktivasi, dan buffer audio jauh lebih besar. Kebutuhan RAM/disk lingkungan dan latency belum diukur. Usulan awal lingkungan pengujian: Python 64-bit, CPU laptop, lingkungan virtual terisolasi, dan RAM 8 GB sebagai titik awal uji—**bukan spesifikasi minimum yang telah dibuktikan**. Model di-cache sebagai resource baca-saja; fitur/audio pengguna tidak di-cache lintas sesi. Batching membatasi penggunaan memori bila kebijakan full-coverage disetujui.[1][4][5]

## 4. Pertentangan yang tidak boleh diselesaikan diam-diam

| Topik | Laporan | Artefak/notebook | Status rencana |
| --- | --- | --- | --- |
| Framework CNN | PyTorch. | TensorFlow/Keras `.keras`. | Keras disetujui pada Q1 untuk memakai bobot asli. |
| Output/loss | Sigmoid satu logit, binary cross-entropy. | Dua softmax, sparse categorical cross-entropy. | Ikuti kontrak model asli, tanpa konversi atau retraining; catat deviasi terhadap uraian teori. |
| Cakupan rekaman | Semua potongan rekaman panjang, sampai 10 menit. | Maksimum empat chunk dari awal; cakupan maksimal **6,25 detik**, ekor lain dibuang. | Mode notebook disetujui pada Q2. Tidak boleh mengaku menganalisis seluruh 10 menit dengan hanya membaca awalnya. |
| Batas keputusan | `p >= tau`. | `p > best_t`. | Operator notebook disetujui pada Q3, termasuk uji tepat di batas. |
| Sumber dataset | Disebut dataset Kaggle. | Memuat dataset Hugging Face; revision tidak dicatat. | Catat lineage sebenarnya; jangan mengubah laporan dalam pekerjaan ini. |
| Hasil pengujian | Target akurasi/F1/EER; Bab V belum berisi hasil. | Ada akurasi/F1/AUC lampiran, tidak ada EER. | Reproduksi dan hitung EER setelah persetujuan; jangan menulis hasil target sebagai hasil aktual. |
| Makna keyakinan | `max(p,1-p)` disebut tingkat keyakinan. | Threshold sekitar 0,51. | Jelaskan keterbatasan kalibrasi dan kemungkinan skor maksimum bukan skor label yang dipilih. |

**Riwayat dua pilihan cakupan: pengguna menyetujui pilihan pertama; pilihan kedua tidak diterapkan.**

- **Kompatibilitas training ketat:** tetap maksimum empat chunk dan membuang ekor. Harus mengungkapkan batas cakupan dengan jelas; tidak memenuhi janji analisis seluruh rekaman panjang dalam KP-06/KF-07.
- **Perluasan cakupan sesuai laporan:** gunakan lebih banyak window dan aturan ekor yang disetujui, sementara preprocessing setiap window tetap identik. Ini mengubah kebijakan sampling/agregasi end-to-end; threshold dan hasil file-level harus dievaluasi ulang tanpa training. Menambah padding, window terakhir yang bergeser, atau pooling bertingkat juga bukan perilaku yang boleh dipilih tanpa persetujuan.

Implementasi sekarang mempertahankan empat chunk. Perluasan cakupan memerlukan persetujuan terpisah.

## 5. Tech stack yang diusulkan

| Lapisan | Pilihan | Alasan dan batas keputusan |
| --- | --- | --- |
| UI/server | Python + Streamlit. | Mengikuti laporan; satu layanan cukup, tanpa FastAPI/database tambahan. |
| Model | TensorFlow backend + Keras 3.13.2. | Memuat model yang benar-benar dilatih; deviasi framework memerlukan persetujuan Q1. |
| Decode | TorchCodec/FFmpeg yang kompatibel dengan runtime training. | Mendekati decoder asli; pertahankan sample rate dan kanal sampai langkah mono/resampling eksplisit. Perbedaan backend decode harus diuji. |
| DSP | PyTorch/TorchAudio + librosa + NumPy. | Mono dan resampling mengikuti source; mel/dB mengikuti librosa. SoundFile boleh dipakai untuk fixture lossless hanya jika hasil decode terbukti konsisten, bukan pengganti otomatis decoder asli. |
| Konfigurasi | `meta.json` + manifest kontrak/versi/hash. | Satu otoritas parameter; manifest tambahan merekam default implisit dan kebijakan cakupan yang telah disetujui. |
| Ekspor | JSON dan teks UTF-8. | Mudah disimpan dan diperiksa; usulan format, bukan ketentuan laporan. |
| Pengujian | pytest, NumPy assertions, scikit-learn, pengujian UI/browser. | Parity numerik, evaluasi terpisah, tes input/privasi, serta bukti alur pengguna. Tidak menambahkan data training baru. |
| Deployment | Localhost dahulu; reverse proxy TLS jika publik. | Sesuai batas purwarupa dan KNF-04; deployment publik bukan asumsi otomatis. |

Belum membuat `requirements.txt` dengan nomor versi tebakan. Versi final dikunci hanya setelah lingkungan yang disetujui dapat memuat model dan melewati uji referensi. Safe mode Keras bukan pengganti verifikasi integritas artefak; definisi custom layer tetap berasal dari source yang diaudit.[8]

## 6. Arsitektur dan struktur folder

### 6.1 Aliran komponen

```text
Peramban / Streamlit UI
  → validasi ukuran, format, dan batas durasi
  → decode dengan batas resource
  → penilaian mutu terpisah (tanpa mengubah audio model)
  → mono → resample → chunk policy yang disetujui
  → mel dB → normalisasi metadata → tensor channels-last
  → model Keras beku, training=False
  → rata-rata skor fake → threshold asli → hasil + disclaimer
  → ekspor ringkasan; cleanup buffer/temp pada semua jalur
```

Model dan metadata dapat dibagi sebagai resource baca-saja. State hasil dan byte audio hanya milik sesi pengguna; tidak ada database, global cache audio, atau pemanggilan layanan deteksi pihak ketiga. Jika thread-safety model bersama belum terbukti, serialisasi pemanggilan inferensi sampai uji konkurensi lulus.

### 6.2 Struktur yang direncanakan — bukan implementasi saat ini

```text
repo/
├── Proposal-TA-template-v2-APA/       # laporan, tidak diubah
└── adadeh-app/
    ├── PLAN.md                      # tersedia
    ├── .gitignore                   # tersedia; seluruh artifacts diabaikan
    ├── README.md                    # dibuat sesudah persetujuan
    ├── pyproject.toml + lockfile     # dibuat setelah kompatibilitas disepakati
    ├── streamlit_app.py
    ├── .streamlit/config.toml
    ├── src/adadeh/
    │   ├── contracts.py             # schema metadata dan versi/hash
    │   ├── audio.py                 # decode, batas input, mono, resample
    │   ├── preprocessing.py         # chunk, mel, dB, normalisasi
    │   ├── model.py                 # loader, custom layer, inference-only
    │   ├── prediction.py            # agregasi, threshold, label
    │   ├── quality.py               # warning, tanpa transformasi waveform
    │   ├── reporting.py             # ringkasan JSON/TXT
    │   └── service.py               # orkestrasi dan cleanup
    ├── scripts/evaluate_model.py    # evaluasi model beku, bukan training
    ├── tests/{unit,integration,parity,ui}/
    └── artifacts/                   # tersedia sebagian; tidak masuk Git
        ├── kaggle_output/           # sembilan keluaran asli
        ├── kaggle_source/           # source notebook + metadata kernel
        ├── reference_notebooks/     # lampiran asli
        ├── audit/                   # hash, hasil inspeksi, bukti sumber
        ├── golden/                  # perlu dilengkapi sesudah persetujuan
        └── evaluation/              # hasil tes/evaluasi sesudah persetujuan
```

Tidak menyimpan unggahan pengguna secara permanen di `artifacts/`. Direktori itu untuk artefak pengembangan/evaluasi yang diizinkan, bukan riwayat pengguna.

## 7. Tahapan implementasi setelah persetujuan

| Tahap | Pekerjaan | Kriteria selesai dan gate |
| --- | --- | --- |
| 0 — Bekukan keputusan | Jawab Q1–Q5; tetapkan model, cakupan/ekor, operator threshold, lingkungan, dan fixture referensi. | Tidak ada konflik kritis yang dibiarkan implisit. Tidak memulai implementasi preprocessing sebelum kontraknya disetujui. |
| 1 — Lingkungan dan loader | Buat struktur paket/dependency lock, validasi manifest, definisi custom layer tepercaya, loader inference-only; evaluasi langsung fitur NPZ. | Model termuat tanpa unsafe mode/retraining; input/output benar; normalisasi memakai metadata asli; baseline CM/AUC direproduksi atau selisih diblokir dan dijelaskan sebelum lanjut. |
| 2 — Pipeline audio | Implementasikan decode, mono, resample, chunk, mel, dB, normalisasi, serta validasi input. | Golden waveform→fitur lulus; fitur `(n,128,157,1)` float32; label dan skor sesuai referensi. Semua batas dan kasus audio pendek/ekor/cakupan diuji. |
| 3 — Layanan inferensi | Orkestrasi, rata-rata skor, threshold, penilaian mutu non-destruktif, cleanup, serta result schema. | Tidak ada perubahan bobot; hasil deterministik dalam toleransi; seluruh jalur sukses/galat membersihkan data; warning tidak mengubah prediksi. |
| 4 — UI dan ekspor | Streamlit Bahasa Indonesia, auto-analisis setelah unggah, kemajuan, hasil/disclaimer, unduh JSON/TXT. | Alur tiga langkah dan KF-01–KF-12 diuji end-to-end; ekspor mempunyai semua field wajib dan cakupan sebenarnya. |
| 5 — Validasi dan serah terima | Evaluasi test beku, EER, benchmark CPU, browser/mobile, privasi/resource, dan TLS bila publik. | Matriks KF/KNF terisi hasil nyata; target yang belum lulus dilaporkan sebagai belum lulus; README instalasi/jalankan/uji lengkap. Tidak menutupi kegagalan dengan mock metrics. |

Setelah **setiap tahap**, jalankan tes terkait, laporkan hasil singkat, dan perbarui README: prasyarat, instalasi, lokasi artefak, perintah menjalankan, perintah tes, batasan, dan status yang belum lolos. Tidak commit/push tanpa permintaan terpisah.

## 8. Rencana pengujian dan kesetaraan dengan notebook/laporan

### 8.1 Integritas dan parity model

1. Periksa hash model/metadata, urutan kelas, input/output, serta custom layer sebelum menerima inferensi. Larang fallback diam-diam ke `best.keras`.
2. Muat `test.npz` dengan `allow_pickle=False`, normalisasi dari metadata, ambil skor kolom fake, kelompokkan berdasarkan `file_id`, dan gunakan `>` dengan nilai threshold tersimpan. Data test tidak digunakan untuk memilih threshold.
3. Cocokkan CM chunk `[[299,6],[0,202]]` dan CM file `[[136,4],[0,140]]` dengan lampiran; reproduksi AUC tercetak dalam toleransi yang ditetapkan. Jika berbeda, hentikan integrasi dan periksa pasangan artefak/runtime, bukan mengganti hasil pembanding.
4. Buat golden prediction vector dari runtime referensi yang dipercaya. Usulan awal toleransi skor: `rtol=1e-5, atol=1e-6`, dengan label dan CM harus sama. Ini kriteria yang diusulkan, bukan hasil tes yang sudah lulus; permintaan “identik” KNF-08 perlu disepakati apakah berarti bitwise atau kesetaraan numerik.
5. Hitung akurasi, F1 fake, ROC-AUC, dan **EER** terpisah per chunk dan per file. Usulkan file-level sebagai hasil utama aplikasi, tetapi tetap tampilkan kedua tingkat. Metode interpolasi/perpotongan ROC untuk EER harus dicatat; EER bukan error rate pada threshold operasi 0,51.

### 8.2 Parity dari waveform

- Golden fixture harus menyertakan byte audio asli, identitas file/dataset revision, hasil decode, fitur mel dB, fitur ternormalisasi, skor chunk, skor file, dan label dari pipeline referensi. NPZ saja tidak membuktikan decode/resampling audio mentah identik.
- Cakup mono/stereo, 16 kHz dan sample rate lain yang dipakai sumber, serta satu/lengkap/beberapa chunk. Bandingkan tiap tahap, bukan hanya label akhir.
- Uji panjang sampel: `39999`, `40000`, `40001`, batas langkah, dan batas empat chunk. Untuk kebijakan full-coverage, tambahkan kasus ekor dan file panjang sesuai keputusan Q2; perbedaannya dari mode training harus terlihat jelas.
- Uji threshold: tepat sama, sedikit di bawah, dan sedikit di atas nilai ekspor; uji indeks kelas agar real/fake tidak tertukar.
- Ulangi inferensi untuk memastikan SpecAugment/Dropout tidak aktif dan BatchNorm tidak memperbarui statistik. Tidak memanggil `fit`, optimizer, atau menyimpan ulang bobot sebagai bagian inferensi.

### 8.3 Validasi aplikasi, privasi, dan resource

- Tes nyata WAV/FLAC/MP3/M4A/OGG, audio hening, level rendah, clipping, rusak, kosong, ekstensi palsu, byte/durasi tepat batas, serta nama berkas berbahaya. File type pada widget bukan jaminan keamanan; decode/validasi server tetap wajib.[11]
- Rencana batas resource mencakup timeout decoder, batas durasi PCM sebelum alokasi besar, isolasi temporary directory, dan larangan decoder mengambil URL jaringan dari input pengguna. Nilai batas tambahan harus terdokumentasi sebagai guard aplikasi, bukan parameter training.
- Tidak menggunakan cache lintas pengguna untuk audio/fitur/hasil. Uji dua sesi bersamaan, galat decoder/model, pembatalan, dan unggahan berulang. Verifikasi file/temp/log serta koneksi keluar; model boleh bertahan sebagai resource, bukan data audio.
- Model diinisialisasi saat aplikasi siap menerima unggahan. Benchmark tetap melaporkan cold start dan warm run. Hitung waktu sejak unggahan selesai sampai hasil siap, mencakup decode, DSP, inferensi, dan agregasi; tidak hanya waktu panggilan model.
- Untuk KNF-02, tampilkan waktu setiap run dan maksimum terukur, bukan hanya rata-rata. Frasa “paling lama 10 detik” tidak terbukti hanya karena rata-ratanya di bawah 10 detik. Persentil dapat dilaporkan sebagai informasi tambahan, bukan pengganti batas penerimaan yang disepakati.
- Usulan benchmark: beberapa pengulangan pada durasi 2,5/10/60 detik dan, jika disetujui, hingga 600 detik; catat CPU, RAM, OS, versi library, waktu, dan peak memory. Jangan mengklaim target 10 detik terpenuhi sebelum hardware acuan dan hasil pengukuran tersedia.
- Uji UI desktop/mobile, label mudah dipahami, field unduhan, kemajuan, disclaimer, dan TLS/WSS pada deployment publik yang benar-benar dipilih.

### 8.4 Kriteria penghentian yang jujur

Kelulusan mempunyai dua lapisan: **parity terhadap model/notebook asli** dan **pemenuhan kebutuhan produk laporan**. Mode empat chunk dapat lulus parity tetapi gagal cakupan KP-06. Mode seluruh rekaman dapat memenuhi cakupan tetapi bukan otomatis setara dengan evaluasi notebook. Jika metrik, latency, atau kesetaraan tidak lulus, laporkan hasil dan minta keputusan; jangan melatih ulang, mengganti threshold, atau mengendurkan toleransi tanpa persetujuan.

## 9. Risiko dan asumsi

| Risiko | Dampak | Mitigasi/rencana |
| --- | --- | --- |
| Kontrak laporan dan model berbeda. | Aplikasi terlihat sesuai UI tetapi salah secara numerik atau mengklaim cakupan palsu. | Gate keputusan eksplisit sebelum kode. |
| Versi training tidak lengkap dan default implisit. | Decode, mel, normalisasi, atau skor dapat bergeser. | Freeze runtime/identifikasi image, golden waveform, dependency lock; tidak mengisi versi dengan dugaan. |
| Bobot alternatif tertukar. | Threshold dan metrik tidak lagi sesuai. | Hash/pasangan model-config dan larangan fallback. |
| Baseline berasal dari output notebook tersimpan. | Reproduksi artefak belum terbukti. | Evaluasi model beku sebelum UI; simpan score vector dan bukti hasil nyata. |
| EER tidak tersedia. | Target laporan belum dapat dinyatakan lulus. | Hitung setelah persetujuan tanpa memakai test untuk tuning. |
| Sumber dataset/revisi dan split source tidak lengkap. | Reproduksi waveform atau identitas speaker tidak dapat dipastikan. | Gunakan NPZ untuk evaluasi awal; minta dataset revision/fixture dan freeze lingkungan. |
| Generalisasi bahasa/codec/durasi. | Skor tinggi tidak menjamin benar di dunia nyata. | Disclaimer, uji tambahan berlabel bila tersedia; tidak mengarang klaim dukungan bahasa Indonesia. |
| File kompresi atau audio panjang memakan resource. | Kegagalan respons dan risiko denial-of-service. | Decode terbatas, batching, timeout dan pengukuran CPU/memori. |
| Data pribadi tertinggal di cache/log. | KNF-05/KF-12 tidak terpenuhi. | Proses lokal server, buffer per sesi, cleanup dan tes privasi; tidak ada layanan deteksi pihak ketiga. |

**Asumsi yang memerlukan persetujuan plan:** purwarupa satu unggahan per proses; default deployment localhost; JSON/TXT sebagai format ringkasan; 100 MB diartikan 100.000.000 byte; autentikasi, database, browser extension, dan penyimpanan riwayat tidak ditambahkan. Persetujuan plan tidak otomatis mengizinkan perubahan laporan atau pelatihan ulang.

## 10. Pertanyaan awal dan hal yang masih perlu divalidasi

Jawaban Q1–Q5 sudah dicatat di Bagian 0. Teks berikut dipertahankan sebagai jejak keputusan; ketiadaan referensi pada Q4 bukan klaim parity audio mentah sudah terpenuhi.

### Pertanyaan yang menghalangi kontrak implementasi

1. **Q1 — Framework/model:** apakah disetujui memakai **TensorFlow/Keras dan pasangan `adadeh_cnn.keras` + `meta.json`** sebagai acuan, bukan memaksa implementasi CNN PyTorch/sigmoid seperti uraian laporan? Rekomendasi: pakai artefak asli, tanpa konversi/retraining.
2. **Q2 — Audio panjang dan ekor:** apakah harus mempertahankan **empat chunk awal + pembuangan ekor** persis notebook, atau boleh mengubah kebijakan menjadi **seluruh rekaman** agar memenuhi laporan? Jika seluruh rekaman, aturan chunk terakhir/ekor dan evaluasi file-level harus disetujui. Kedua kontrak tidak dapat diklaim sama persis.
3. **Q3 — Keputusan/skor:** apakah disetujui mempertahankan **operator `>` dan threshold persis ekspor**, sementara laporan menulis `>=`? Untuk UI, usulan menampilkan label, skor fake, dan skor keyakinan sesuai rumus laporan dengan penjelasan bahwa keduanya bukan kepastian forensik/kalibrasi.
4. **Q4 — Lingkungan dan referensi:** dapatkah disediakan `pip freeze`/versi TensorFlow, librosa, NumPy, torch, torchaudio, torchcodec/FFmpeg dari runtime training serta beberapa audio referensi dengan skor aslinya atau dataset revision? Tanpa itu, parity dari audio mentah belum dapat disahkan; fitur NPZ hanya menguji bagian model/normalisasi/agregasi.
5. **Q5 — Peringatan mutu:** adakah ambang keheningan, clipping, level rendah, atau noise yang memang ditetapkan proyek? Jika belum ada, bolehkah mengusulkan ambang engineering terpisah untuk disetujui, tanpa mengubah waveform model atau menyebutnya parameter training? Audio di bawah minimum satu chunk harus ditolak; perlu keputusan apakah audio yang masih valid tetapi relatif singkat juga diberi warning, beserta ambangnya.

### Hal yang perlu dipastikan saat validasi

- Hardware/OS dan peramban acuan untuk target latency/kompatibilitas; apakah aplikasi hanya lokal atau akan dipublikasikan?
- Apakah kesetaraan KNF-08 menerima toleransi floating point yang dinyatakan dengan label sama, atau mensyaratkan bitwise pada runtime identik?
- Apakah format ekspor JSON/TXT dan konvensi 100 MB yang diusulkan sudah sesuai?

## 11. Status akhir tahap perencanaan

- [x] Laporan lengkap dan struktur repositori diperiksa.
- [x] Keluaran Kaggle berhasil diunduh; model, konfigurasi, source, split, history, dan output metrik lampiran diaudit.
- [x] Artefak besar ditempatkan di `artifacts/` dan benar-benar diabaikan Git.
- [x] Plan, pemetaan kebutuhan, tahapan, uji parity, risiko, dan pertanyaan terbuka ditulis.
- [x] Persetujuan pengguna dan jawaban atas konflik kritis; mode notebook dipilih.
- [ ] Implementasi, pemuatan model untuk inferensi, pengujian aplikasi, deployment, dan training ulang: **belum dilakukan**; training ulang tetap di luar izin tugas.

**Batas tahap plan sudah terpenuhi. Lanjutkan implementasi bertahap sesuai keputusan di Bagian 0, jalankan tes dan perbarui README tiap tahap; jangan melatih ulang.**

## Sources

[1] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/Proposal-TA-template-v2-APA/ProposalTA.pdf — Laporan ADADeH — ProposalTA.pdf, 66 halaman
[2] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/reference_notebooks/tpdk-rek-sismul.ipynb — Notebook training yang dilampirkan, 20 sel; sumber identik dengan hasil pull Kaggle
[3] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/kaggle_output/meta.json — Metadata preprocessing dan postprocessing model
[4] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/audit/adadeh_cnn-config.json — Config model adadeh_cnn.keras, dibaca dari arsip Keras
[5] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/audit/artifact-audit.json — Audit sembilan keluaran Kaggle, split data, hash dan statistik
[6] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/kaggle_output/history.json — Riwayat training yang diunduh dari Kaggle
[7] file:///C:/Users/Carlen/Documents/GitHub/Laporan-TPdK-Carlen-Sam-Fajrul/adadeh-app/artifacts/kaggle_source/kernel-metadata.json — Konfigurasi kernel Kaggle dan digest Docker image
[8] https://keras.io/api/models/model_saving_apis/model_saving_and_loading — Keras: Whole model saving & loading
[9] https://librosa.org/doc/0.11.0/generated/librosa.feature.melspectrogram.html — librosa 0.11.0: melspectrogram; rujukan API, bukan bukti versi training
[10] https://docs.pytorch.org/audio/2.11.0/generated/torchaudio.functional.resample.html — TorchAudio 2.11.0: functional.resample; rujukan API, bukan bukti versi training
[11] https://docs.streamlit.io/1.55.0/develop/api-reference/widgets/st.file_uploader — Streamlit 1.55.0: st.file_uploader; rujukan perancangan
