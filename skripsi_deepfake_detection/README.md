# Sistem Deteksi Deepfake Video Berbasis Hybrid CNN–BiLSTM

Aplikasi web untuk mendeteksi video deepfake menggunakan model **Hybrid CNN–BiLSTM**.
Fitur wajah diekstraksi per-frame dengan **MTCNN + CNN backbone (ResNet50)**, lalu
urutan fitur temporalnya diklasifikasikan oleh model **Bidirectional LSTM** menjadi
**REAL** atau **FAKE**. Hyperparameter model dioptimasi dengan **Metode Taguchi**.

> Skripsi — Program Studi Teknik Informatika, Fakultas Ilmu Komputer,
> Universitas Esa Unggul. Oleh **Helmy Pramudita**.

---

## Ringkasan Hasil Model

| Metrik | Nilai |
|---|---|
| Backbone | ResNet50 |
| Accuracy (test) | 0.9081 |
| Precision | 0.8898 |
| Recall | 0.9528 |
| F1-score | 0.9202 |
| ROC-AUC | 0.9725 |
| EER | 0.0835 |
| Best threshold | 0.59 |
| Epoch terlatih | 39 |

Dataset uji: 1.186 sampel (593 REAL / 593 FAKE), seimbang.

---

## Fitur Aplikasi

- **Deteksi deepfake** dari unggahan video (MP4, AVI, MOV, MKV), maksimal 50 MB.
- **Penanganan rotasi otomatis** untuk video HP/WhatsApp yang orientasinya
  disimpan sebagai metadata.
- **Autentikasi pengguna** (registrasi, login, ganti password) dengan dua peran:
  `admin` dan `user`.
- **Riwayat scan** per pengguna, lengkap dengan pemutar video (modal) untuk
  memverifikasi ulang hasil.
- **Kontrol akses berbasis peran (RBAC):** user hanya bisa membuka arsip video
  miliknya sendiri; admin bisa membuka milik siapa pun.
- **Dasbor admin:** statistik total scan, rasio FAKE/REAL, dan manajemen pengguna.
- **Retensi arsip otomatis:** berkas video dihapus setelah 30 hari, sementara
  metadata riwayat tetap tersimpan permanen.

---

## Struktur Proyek

```
.
├── app.py                     # Aplikasi Flask utama + logika inferensi
├── models.py                  # Model database (User, ScanHistory)
├── requirements.txt           # Daftar dependensi Python
│
├── templates/                 # Berkas HTML
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── history.html
│   ├── admin_dashboard.html
│   ├── admin_users.html
│   ├── admin_user_history.html
│   └── _video_modal.html
│
├── static/
│   └── style.css
│
├── arsip/                     # (dibuat otomatis) arsip video hasil scan
│   └── videos/
│
├── deepfake_skripsi.db        # (dibuat otomatis) basis data SQLite
│
└── ml/                             # Skrip machine learning (pelatihan model)
    ├── run_four_backbones.py        # 1a. Runner ekstraksi 4 backbone (b0, b2, resnet50, xception)
    ├── b_ekstraksi_frame_taguchi.py # 1b. Proses inti ekstraksi fitur wajah -> .npy
    ├── run_taguchi_full.py          # 2.  Optimasi hyperparameter (Taguchi)
    ├── balance_data_full.py         # 3.  Penyeimbangan dataset
    └── train_bilstm_full.py         # 4.  Pelatihan & evaluasi BiLSTM
```


---

## Prasyarat

- **Python 3.10** (disarankan 3.9–3.11)
- **pip** dan **virtual environment**
- Untuk pelatihan model: disarankan GPU NVIDIA + CUDA (opsional; CPU juga bisa,
  hanya lebih lambat)

---

## Instalasi

```bash
# 1. Buat & aktifkan virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 2. Pasang dependensi
pip install -r requirements.txt
```

---

## Menjalankan Aplikasi Web

Aplikasi memerlukan **model terlatih** (`model_best.h5`) dan berkas
`training_config.json` di folder model. Secara bawaan, `app.py` mencari model di:

```
<BASE_DIR>/final_trained_model_mtcnn_v7_single_3_<BACKBONE>/model_best.h5
```

Atur lokasi dan backbone lewat variabel lingkungan (contoh untuk model final ResNet50):

**Windows (PowerShell):**
```powershell
$env:BASE_DIR = "D:\Semester 6\celeb-v2"
$env:BACKBONE = "resnet50"
python app.py
```

**Linux / macOS:**
```bash
export BASE_DIR="/path/ke/celeb-v2"
export BACKBONE="resnet50"
python app.py
```

Lalu buka **http://localhost:5000** di peramban.

### Akun bawaan

Saat pertama dijalankan, aplikasi otomatis membuat akun admin:

| Username | Password | Peran |
|---|---|---|
| `admin` | `123` | admin |

> **Penting untuk keamanan:** ganti password admin default ini sebelum
> aplikasi dipakai di lingkungan nyata.

---

## Alur Pelatihan Model (Pipeline ML)

Jalankan berurutan. Semua skrip dikonfigurasi lewat variabel lingkungan
(lihat bagian Konfigurasi).

**1. Ekstraksi fitur** — mendeteksi wajah tiap frame dengan MTCNN, mengekstrak
fitur dengan CNN backbone, lalu menyimpannya sebagai berkas `.npy` per video.
Proses inti ada di `b_ekstraksi_frame_taguchi.py`, sedangkan
`run_four_backbones.py` menjalankannya berurutan untuk keempat backbone
(b0, b2, resnet50, xception) dengan menyetel variabel lingkungan secara otomatis.

```bash
# Jalankan ekstraksi untuk keempat backbone sekaligus
python ml/run_four_backbones.py
```

Atau jalankan satu backbone saja secara manual (mis. resnet50):

```bash
# Windows (PowerShell)
$env:BACKBONE = "resnet50"
python ml/b_ekstraksi_frame_taguchi.py
```

Keluaran disimpan ke `new_output_features_mtcnn_v7_single_3_<backbone>/`.
Konfigurasi tiap run juga dicatat ke folder `configs/`.

**2. Optimasi Taguchi** — mencari kombinasi hyperparameter terbaik
(learning rate, units, dropout, batch size) dan menyimpannya ke
`best_config_<backbone>.json`.

```bash
python ml/run_taguchi_full.py
```

**3. Penyeimbangan dataset** — menyamakan jumlah sampel REAL dan FAKE
(undersampling kelas mayoritas), lalu menyimpan `X_balanced_<backbone>.npy`
dan `y_balanced_<backbone>.npy`.

```bash
python ml/balance_data_full.py
```

**4. Pelatihan & evaluasi BiLSTM** — melatih model dengan konfigurasi Taguchi
terbaik, membagi data 70/10/20, lalu menyimpan `model_best.h5` beserta seluruh
artefak evaluasi (`metrics.json`, `metrics.csv`, `history.csv`,
`classification_report.txt`, `cm.png`, `roc.png`, `training_plot.png`).

```bash
python ml/train_bilstm_full.py
```

---

## Konfigurasi (Variabel Lingkungan)

| Variabel | Bawaan | Dipakai oleh | Keterangan |
|---|---|---|---|
| `BASE_DIR` | `D:\Semester 6\celeb-v2` | semua | Folder induk dataset & model |
| `BACKBONE` | `resnet50` (app) | semua | Pilih: `b0`, `b2`, `resnet50`, `xception` |
| `FACE_COLOR` | `bgr` | app | Ruang warna crop wajah — **harus sama** dengan saat ekstraksi fitur |
| `FOLDERS` | `video_real,video_synthesis,youtube-real` | ekstraksi | Sub-folder video sumber |
| `TOP_K_FACES` | `2` | ekstraksi | Jumlah wajah per frame yang diambil |
| `BATCH_SIZE` | `64` | ekstraksi | Ukuran batch inferensi CNN |
| `USE_PILOT` | `0` | ekstraksi | `1` = pakai subset video (uji cepat) |
| `PILOT_RATIO` | `0.10` | ekstraksi | Proporsi subset saat pilot |
| `OUT_ROOT` | `new_output_features_mtcnn_v7_single_3` | ekstraksi | Prefix folder keluaran fitur |
| `DATA_DIR` | `<BASE_DIR>/new_final_dataset_mtcnn_v7_single_3` | training | Folder data balanced |
| `EPOCHS` | `100` | training | Jumlah epoch maksimum |
| `SEED` | `42` | training/balance | Seed acak untuk reprodusibilitas |
| `MAX_FRAMES` | `30` | balance | Panjang sekuens (padding) |
| `INPUT_TAG` | `new_output_features_mtcnn_v7_single_3` | balance | Prefix folder fitur |
| `FOLDERS_REAL` | `video_real,youtube-real` | balance | Sub-folder sumber kelas REAL |
| `FOLDERS_FAKE` | `video_synthesis` | balance | Sub-folder sumber kelas FAKE |

---

## Arsitektur Model

```
Input (sekuens fitur wajah, panjang 30)
  → Bidirectional LSTM (return_sequences)
  → LayerNormalization
  → Bidirectional LSTM (return_sequences)
  → LayerNormalization
  → GlobalAveragePooling1D
  → Dense(64, ReLU) + L2
  → Dropout
  → Dense(1, Sigmoid)  →  probabilitas FAKE
```

- **Loss:** Focal Loss (α=0.75, γ=2.0) untuk menangani ketidakseimbangan.
- **Optimizer:** AdamW (weight decay 1e-4, clipnorm 1.0).
- **Callbacks:** EarlyStopping, ModelCheckpoint, ReduceLROnPlateau.

---

## Teknologi

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login
- **Basis data:** SQLite
- **Deep learning:** TensorFlow / Keras
- **Computer vision:** OpenCV, MTCNN
- **Evaluasi & visualisasi:** scikit-learn, Matplotlib

---

## Catatan

- Berkas basis data (`deepfake_skripsi.db`), folder `arsip/`, `venv/`, dan
  `__pycache__/` **tidak perlu** disertakan saat pengumpulan — semuanya dibuat
  ulang otomatis.
- Untuk keperluan produksi, jalankan lewat WSGI server (mis. `waitress`)
  alih-alih server pengembangan bawaan Flask.
