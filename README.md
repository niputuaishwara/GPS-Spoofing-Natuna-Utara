# 🛰️ Natuna GPS Spoofing Detection System

> **Sistem Deteksi Indikasi GPS Spoofing pada Pergerakan Kapal di Perairan Natuna**
> Maritime Anomaly Detection System berbasis analisis data navigasi NMEA-0183

---

## 📋 Daftar Isi

- [Deskripsi Sistem](#-deskripsi-sistem)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Struktur Folder](#-struktur-folder)
- [Penjelasan Modul](#-penjelasan-modul)
- [Algoritma Deteksi](#-algoritma-deteksi)
- [Dataset](#-dataset)
- [Basis Data](#-basis-data)
- [Sistem Autentikasi & Peran Pengguna](#-sistem-autentikasi--peran-pengguna)
- [Cara Menjalankan Sistem](#-cara-menjalankan-sistem)
- [Format Data Input](#-format-data-input)
- [Dependensi](#-dependensi)

---

## 📌 Deskripsi Sistem

Sistem ini merupakan implementasi perangkat lunak untuk mendeteksi indikasi **GPS Spoofing** — sebuah serangan siber yang memanipulasi sinyal GPS sehingga kapal melaporkan posisi palsu — pada data pergerakan kapal di wilayah **Perairan Laut Natuna Utara**, Indonesia.

Sistem dibangun menggunakan bahasa pemrograman **Python** dengan framework **Streamlit** sebagai antarmuka pengguna berbasis web, dan **SQLite** sebagai sistem manajemen basis data. Sistem memproses data navigasi dalam format standar **NMEA-0183** (kalimat `$GPRMC`) secara sekuensial, mengevaluasi empat parameter anomali, dan menghasilkan nilai **Risk Score** sebagai indikator tingkat indikasi GPS spoofing.

> Sistem ini bekerja **sepenuhnya berbasis perangkat lunak** tanpa memerlukan penambahan perangkat keras (hardware) apapun.

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 📂 **Multi-format Data Loader** | Mendukung upload file CSV, Excel (.xlsx/.xls), dan NMEA-0183 mentah |
| ⚡ **Live Vessel Tracking** | Animasi real-time pergerakan kapal titik per titik dengan peta langsung |
| 🧪 **Mode Simulasi** | 4 skenario serangan GPS spoofing yang dapat dijalankan dari antarmuka |
| 🔍 **4 Algoritma Deteksi** | Speed Check, Rate of Turn Check, Geofence Check, Border Proximity Check |
| 📊 **Risk Scoring** | Kalkulasi tingkat risiko berbobot (0-100) dengan 4 level klasifikasi |
| 🗺️ **Visualisasi Peta Interaktif** | Peta navigasi berbasis Folium dengan penanda anomali berwarna |
| 👥 **Multi-user & Role-based Access** | Tiga level akses: Admin, Analyst, dan User |
| 📝 **Audit Log** | Pencatatan seluruh aktivitas pengguna untuk keperluan forensik |
| 📄 **Laporan Analisis** | Ekspor dan anotasi hasil analisis oleh analyst |

---

## 🏗️ Arsitektur Sistem

Sistem dirancang dengan alur pemrosesan **sekuensial tiga lapisan**:

```
LAPISAN PRESENTASI
  app.py · dashboard.py · report.py · admin.py

LAPISAN DETEKSI (CORE)
  data_loader.py -> detection_engine.py -> risk_engine.py
       |                  |
  geofence.py        border_analysis.py · utils.py

LAPISAN DATA
  database.py · auth.py · audit.py · SQLite DB
```

**Alur Pemrosesan Data:**
```
Input Data (CSV/XLSX)
       |
  data_loader.py          <- Parsing, validasi, normalisasi
       |
  detection_engine.py     <- Analisis anomali per titik data
    |-- utils.py           (Haversine distance)
    |-- geofence.py        (Point-in-polygon check)
    +-- border_analysis.py (Jarak ke batas maritim)
       |
  risk_engine.py          <- Kalkulasi Risk Score & Risk Level
       |
  database.py             <- Penyimpanan hasil ke SQLite
       |
  dashboard.py / report.py <- Visualisasi & Pelaporan
```

---

## 📁 Struktur Folder

```
natuna/
|
|-- app.py                  # Entry point utama aplikasi Streamlit
|-- data_loader.py          # Pembaca & validasi data navigasi
|-- detection_engine.py     # Mesin deteksi anomali (core algorithm)
|-- risk_engine.py          # Kalkulasi Risk Score & Risk Level
|-- geofence.py             # Validasi batas wilayah (Point-in-Polygon)
|-- border_analysis.py      # Analisis jarak ke batas maritim
|-- utils.py                # Fungsi utilitas (Formula Haversine)
|-- simulation.py           # Generator skenario simulasi GPS spoofing
|-- dashboard.py            # Komponen visualisasi dashboard
|-- report.py               # Modul laporan & anotasi analyst
|-- admin.py                # Panel administrasi pengguna
|-- auth.py                 # Autentikasi & manajemen pengguna
|-- audit.py                # Pencatatan log aktivitas (audit trail)
|-- database.py             # Skema & operasi basis data SQLite
|-- natuna.md               # Dokumentasi tambahan proyek
|
|-- datasets/               # Dataset navigasi kapal (CSV)
|   |-- normal_route.csv            # Data rute normal (baseline)
|   |-- sudden_jump.csv             # Skenario lompatan posisi tiba-tiba
|   |-- slow_drift.csv              # Skenario pergeseran arah bertahap
|   |-- geofence_escape.csv         # Skenario keluar batas wilayah
|   +-- mixed_attack_spoofing.csv   # Skenario serangan campuran
|
|-- database/               # Penyimpanan basis data SQLite
|   +-- natuna_spoofing.db          # File database utama
|
|-- assets/                 # Aset statis (gambar, ikon, dll.)
|
+-- venv/                   # Virtual environment Python
```

---

## 📦 Penjelasan Modul

### 1. app.py — Entry Point Utama

File utama aplikasi Streamlit. Mengorkestrasi seluruh alur aplikasi mulai dari autentikasi, sidebar navigasi, pemrosesan live animasi, hingga routing ke halaman.

| Fungsi | Deskripsi |
|--------|-----------|
| `main()` | Titik masuk aplikasi, inisialisasi DB dan autentikasi |
| `render_login_page()` | Merender halaman login dengan validasi kredensial |
| `render_sidebar(user)` | Sidebar navigasi berbasis peran pengguna |
| `process_row(row, prev)` | Memproses satu baris data: deteksi + risk scoring |
| `run_live_animation(df, ...)` | Animasi tracking kapal real-time titik per titik |
| `process_dataframe_batch(df, ...)` | Pemrosesan batch seluruh dataset (mode simulasi) |
| `run_simulation(type, user)` | Menjalankan skenario simulasi yang dipilih |

---

### 2. data_loader.py — Pembaca & Validator Data

Modul untuk mengakuisisi, memvalidasi, dan menormalisasi data navigasi kapal. Menerapkan kontrol keamanan berlapis untuk mencegah injeksi data dan serangan DoS.

**Konstanta Konfigurasi:**
```python
MAX_FILE_SIZE_MB   = 10      # Batas ukuran file upload (MB)
MAX_ROWS           = 2000    # Batas maksimum baris data
MIN_ROWS           = 2       # Batas minimum baris data
SOG_MAX            = 100.0   # Batas maksimum SOG (knots)
REQUIRED_COLUMNS   = {"timestamp", "latitude", "longitude", "sog", "cog"}
```

| Fungsi | Deskripsi |
|--------|-----------|
| `load_dataset(filepath)` | Memuat dataset dari file lokal (untuk simulasi) |
| `load_from_upload(file)` | Memuat & memvalidasi file yang diupload pengguna |
| `normalize_columns(df)` | Normalisasi nama kolom (lowercase, alias mapping) |
| `validate_columns(df)` | Memverifikasi ketersediaan kolom yang dibutuhkan |
| `validate_data_ranges(df)` | Memfilter koordinat & kecepatan yang tidak valid |
| `sanitize_filename(name)` | Membersihkan nama file dari karakter berbahaya |

---

### 3. detection_engine.py — Mesin Deteksi Anomali (Core)

Inti pemrosesan komputasi sistem. Mengevaluasi setiap titik data navigasi secara sekuensial menggunakan empat algoritma deteksi.

**Threshold Deteksi:**
```python
SPEED_THRESHOLD_KMH        = 80.0   # Kecepatan maksimum wajar (km/jam)
COURSE_THRESHOLD_DEG       = 45.0   # Deviasi arah maksimum wajar (derajat)
BORDER_CHANGE_THRESHOLD_KM = 5.0    # Perubahan jarak ke batas maksimum (km)
```

**Urutan Algoritma yang Dieksekusi:**
1. Geofence Check (semua titik data)
2. Border Proximity Check (semua titik data)
3. Speed Check (jika ada data sebelumnya)
4. Rate of Turn Check (jika ada data sebelumnya)

---

### 4. risk_engine.py — Kalkulasi Tingkat Risiko

**Skema Pembobotan (masing-masing 25 poin):**
```python
speed_alert    -> +25 poin
course_alert   -> +25 poin
geofence_alert -> +25 poin
border_alert   -> +25 poin
# Total maksimum: 100 poin
```

**Klasifikasi Risk Level:**

| Risk Score | Risk Level | Spoofing Detected |
|-----------|------------|:-----------------:|
| 0 – 25 | NORMAL | Tidak |
| 50 | MEDIUM RISK | Ya |
| 75 | HIGH RISK | Ya |
| 100 | CRITICAL | Ya |

---

### 5. utils.py — Formula Haversine

```python
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """
    Menghitung jarak great-circle antara dua titik koordinat geografis.
    Formula: a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)
             c = 2·arcsin(√a)
             d = R·c  (R = 6371 km)
    Mengembalikan: float (jarak dalam kilometer)
    """
```

---

### 6. geofence.py — Validasi Batas Wilayah

```python
# Definisi poligon wilayah operasional Natuna
NATUNA_GEOFENCE_COORDS = [
    (107.0, 3.0),   # Barat-Selatan
    (111.0, 3.0),   # Timur-Selatan
    (111.0, 7.0),   # Timur-Utara
    (107.0, 7.0)    # Barat-Utara
]
# Cakupan: Longitude 107°E - 111°E, Latitude 3°N - 7°N

def check_inside_geofence(lat, lon) -> bool:
    """Mengembalikan True jika koordinat berada dalam poligon Natuna."""
```

---

### 7. border_analysis.py — Analisis Jarak ke Batas

```python
SIMULATED_BORDER_LON = 111.0  # Batas disimulasikan pada Longitude 111°E

def calculate_distance_to_border(lat, lon) -> float:
    """Menghitung jarak (km) dari posisi kapal ke garis batas maritim."""
```

---

### 8. simulation.py — Generator Skenario Simulasi

| Fungsi | Skenario | Anomali yang Diinjeksi |
|--------|----------|------------------------|
| `generate_normal_route()` | Rute normal (baseline) | Tidak ada |
| `generate_sudden_jump_attack()` | Lompatan posisi tiba-tiba | +1° lat/lon pada step ke-50 |
| `generate_slow_drift_attack()` | Pergeseran arah bertahap | COG +2°/step mulai step ke-30 |
| `generate_geofence_escape()` | Pelarian dari zona Natuna | Dimulai dekat batas (6.9°N, 110.9°E) |

---

### 9. auth.py — Autentikasi & Manajemen Pengguna

Menggunakan hashing SHA-256 dengan random salt untuk keamanan password.

```python
# Mekanisme hashing:
salt   = os.urandom(32).hex()
hashed = SHA256(password + salt)

# Hierarki peran:
hierarchy = {'admin': 3, 'analyst': 2, 'user': 1}
```

| Fungsi | Deskripsi |
|--------|-----------|
| `authenticate(username, password)` | Verifikasi kredensial pengguna |
| `create_user(username, password, role)` | Buat akun baru |
| `has_permission(user, required_role)` | Cek otorisasi berdasarkan hierarki |
| `hash_password(password)` | Hash SHA-256 + salt |
| `toggle_user_active(user_id, active)` | Aktifkan/nonaktifkan akun |
| `update_user_role(user_id, role)` | Ubah peran pengguna |

---

## 📊 Dataset

**Format kolom CSV (semua file):**
```
timestamp,latitude,longitude,sog,cog
2026-01-01 10:00:00,4.1234,108.1234,12.3,90.5
```

---

### 📁 `datasets/` — Data Simulasi Utama (5 file)

| File | Skenario | Titik | Keterangan |
|------|----------|:-----:|------------|
| `normal_route.csv` | Rute normal | 100 | Baseline tanpa anomali |
| `sudden_jump.csv` | Lompatan koordinat | 100 | Anomali pada step ke-50 |
| `slow_drift.csv` | Pergeseran arah bertahap | 100 | Drift COG ab step ke-30 |
| `geofence_escape.csv` | Keluar zona Natuna | 100 | Keluar batas ~step ke-20 |
| `mixed_attack_spoofing.csv` | Serangan kombinasi | 100 | Multi-anomali |

---

### 📁 `datasets/testing/` — Data Pengujian Lengkap (20 file baru, 100 baris/file)

20 dataset varian risiko baru melengkapi 5 file utama (sehingga total 25 dataset). Setiap skenario memiliki **4 varian baru** berdasarkan target Risk Score (25, 50, 75, 100).

#### 🟢 Normal
| File | Risk Focus | Flag Aktif |
|------|:----------:|------------|
| `normal_route.csv` | Mixed | (Base di direktori utama) |
| `normal_r25.csv` | **25** | Speed (kecil) |
| `normal_r50.csv` | **50** | Speed + Course |
| `normal_r75.csv` | **75** | Speed + Course + Geofence |
| `normal_r100.csv` | **100** | Semua 4 flag |

#### ⚡ Sudden Jump
| File | Risk Focus | Flag Aktif |
|------|:----------:|------------|
| `sudden_jump.csv` | Mixed | (Base di direktori utama) |
| `sudden_jump_r25.csv` | **25** | Speed (loncatan posisi) |
| `sudden_jump_r50.csv` | **50** | Speed + Course |
| `sudden_jump_r75.csv` | **75** | Speed + Course + Geofence |
| `sudden_jump_r100.csv` | **100** | Semua 4 flag |

#### 🔄 Slow Drift
| File | Risk Focus | Flag Aktif |
|------|:----------:|------------|
| `slow_drift.csv` | Mixed | (Base di direktori utama) |
| `slow_drift_r25.csv` | **25** | Course (drift bertahap) |
| `slow_drift_r50.csv` | **50** | Course + Border |
| `slow_drift_r75.csv` | **75** | Speed + Course + Geofence |
| `slow_drift_r100.csv` | **100** | Semua 4 flag |

#### 🚧 Geofence Escape
| File | Risk Focus | Flag Aktif |
|------|:----------:|------------|
| `geofence_escape.csv` | Mixed | (Base di direktori utama) |
| `geofence_escape_r25.csv` | **25** | Geofence only |
| `geofence_escape_r50.csv` | **50** | Geofence + Border |
| `geofence_escape_r75.csv` | **75** | Speed + Geofence + Border |
| `geofence_escape_r100.csv` | **100** | Semua 4 flag |

#### 🌐 Mixed Attack
| File | Risk Focus | Flag Aktif |
|------|:----------:|------------|
| `mixed_attack_spoofing.csv` | Mixed | (Base di direktori utama) |
| `mixed_attack_r25.csv` | **25** | Speed only |
| `mixed_attack_r50.csv` | **50** | Speed + Course |
| `mixed_attack_r75.csv` | **75** | Speed + Course + Geofence |
| `mixed_attack_r100.csv` | **100** | Semua 4 flag |

**Ringkasan `datasets/testing/`:**

| Statistik | Nilai |
|-----------|-------|
| Total file tambahan | **20 file** (Total Keseluruhan = 25 dataset) |
| Baris per file | **100 baris** |
| Total baris (baru) | **2.000 baris** |

---

## 🗄️ Basis Data

File SQLite: `database/natuna_spoofing.db`

**Tabel-tabel utama:**

```sql
-- Hasil analisis tiap titik navigasi
vessel_data    (id, user_id, run_id, timestamp, latitude, longitude, speed,
                course, distance_travelled, distance_to_border, inside_geofence,
                risk_score, risk_level, speed_alert, course_alert,
                geofence_alert, border_alert, spoofing_detected)

-- Manajemen akun pengguna
users          (id, username, password_hash, salt, role, is_active, created_at, last_login)

-- Log deteksi anomali
system_logs    (id, user_id, timestamp, event_type, severity, description, risk_score)

-- Log aktivitas pengguna (audit trail)
audit_logs     (id, user_id, username, action, timestamp, status, metadata)

-- Hasil anotasi analyst
analysis_results (id, user_id, run_id, dataset_name, total_records,
                  spoofing_count, avg_risk_score, max_risk_score,
                  category, analyst_notes)

-- Riwayat skenario simulasi
simulation_runs  (id, run_name, dataset_name, total_records, normal_records,
                  alert_records, average_risk_score)
```

---

## 👥 Sistem Autentikasi & Peran Pengguna

| Peran | Username | Password | Akses |
|-------|----------|----------|-------|
| Admin | `admin` | `admin123` | Semua fitur + Panel Admin |
| Analyst | `analyst` | `analyst123` | Dashboard, Upload, Simulasi, Laporan |
| User | `user` | `user123` | Dashboard (read-only), Laporan |

> Ubah password default sebelum deployment ke lingkungan produksi.

---

## 🚀 Cara Menjalankan Sistem

```bash
# 1. Masuk ke direktori proyek
cd natuna

# 2. Aktifkan virtual environment
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Install dependensi
pip install streamlit pandas shapely folium streamlit-folium plotly openpyxl

# 4. Jalankan aplikasi
streamlit run app.py

# 5. Buka browser
# http://localhost:8501
```

---

## 📄 Format Data Input

| Kolom | Tipe | Rentang Valid | Contoh |
|-------|------|--------------|--------|
| `timestamp` | datetime | - | `2026-01-01 10:00:00` |
| `latitude` | float | -90.0 s/d 90.0 | `4.1234` |
| `longitude` | float | -180.0 s/d 180.0 | `108.1234` |
| `sog` | float | 0.0 s/d 100.0 knots | `12.5` |
| `cog` | float | 0.0 s/d 360.0 derajat | `90.0` |

---

## 📦 Dependensi

| Library | Fungsi |
|---------|--------|
| `streamlit` | Framework antarmuka pengguna web |
| `pandas` | Manipulasi dan analisis data tabular |
| `shapely` | Komputasi geometri (Point-in-Polygon) |
| `folium` | Visualisasi peta interaktif |
| `streamlit-folium` | Integrasi Folium ke Streamlit |
| `plotly` | Visualisasi gauge chart Risk Score |
| `openpyxl` | Pembaca file Excel (.xlsx) |

```bash
pip install streamlit pandas shapely folium streamlit-folium plotly openpyxl
```

---

## 📚 Referensi Teknis

- **Formula Haversine**: Perhitungan jarak antar koordinat geografis (radius bumi = 6.371 km)
- **Ray Casting Algorithm**: Validasi point-in-polygon via library Shapely
- **NMEA-0183 $GPRMC**: Standar protokol data navigasi GPS
- **Wilayah Geofence Natuna**: Poligon 107°E–111°E, 3°N–7°N

---

*Sistem Deteksi GPS Spoofing Perairan Natuna — Penelitian Kapita Selekta*
