# Rancangan Penelitian

## Judul Sementara

**Sistem Deteksi GPS Spoofing Berbasis Risk Scoring Menggunakan Analisis Kecepatan, Perubahan Arah, Geofence Operasional, dan Border Proximity pada Kapal di Laut Natuna Utara**

---

# Latar Belakang

Laut Natuna Utara merupakan wilayah strategis Indonesia yang berbatasan langsung dengan Zona Ekonomi Eksklusif (ZEE) negara lain. Aktivitas pelayaran pada wilayah ini sangat bergantung pada sistem navigasi berbasis Global Positioning System (GPS).

GPS sipil memiliki kelemahan mendasar karena tidak menyediakan mekanisme autentikasi bawaan sehingga rentan terhadap serangan GPS Spoofing. Dengan memanfaatkan perangkat murah berbasis Software Defined Radio (SDR) dan perangkat lunak open-source, penyerang dapat memalsukan posisi kapal tanpa terdeteksi oleh sistem navigasi konvensional.

Sebagian besar solusi deteksi GPS Spoofing memerlukan perangkat keras tambahan seperti antena khusus, multi-receiver GPS, sensor inersia, atau perangkat SDR. Pendekatan tersebut sulit diterapkan pada armada nelayan dan kapal patroli domestik karena keterbatasan biaya.

Penelitian ini mengusulkan pendekatan software-only yang memanfaatkan data navigasi standar NMEA-0183 untuk mendeteksi indikasi GPS Spoofing tanpa memerlukan perangkat keras tambahan.

---

# Permasalahan

Bagaimana membangun sistem deteksi GPS Spoofing yang:

1. Tidak membutuhkan perangkat keras tambahan.
2. Dapat bekerja menggunakan data GPS yang tersedia pada kapal.
3. Memiliki relevansi terhadap kondisi operasional Laut Natuna Utara.
4. Mampu memberikan tingkat risiko serangan, bukan hanya alarm biner.

---

# Tujuan Penelitian

Membangun prototipe sistem deteksi GPS Spoofing berbasis perangkat lunak menggunakan data NMEA-0183 dengan mengombinasikan beberapa indikator anomali navigasi untuk menghasilkan nilai risiko serangan.

---

# Ruang Lingkup

Penelitian ini:

- Berfokus pada GPS Spoofing.
- Tidak membahas GPS Jamming.
- Tidak melakukan analisis lapisan RF.
- Tidak menggunakan SDR, HackRF, atau perangkat radio lainnya.
- Menggunakan data navigasi berbasis NMEA-0183.
- Berfokus pada wilayah Laut Natuna Utara.

---

# Dasar Konsep

Penelitian ini terinspirasi dari framework MANA (Maritime Anomaly Detection Framework) yang melakukan deteksi GPS Spoofing berbasis data navigasi.

Namun penelitian ini tidak mengimplementasikan seluruh metode MANA, melainkan memilih metode yang realistis diterapkan pada kapal domestik tanpa sensor tambahan.

---

# Data yang Digunakan

Data berasal dari:

- Dataset MARSIM (Maritime GPS Spoofing Dataset)
- Dataset AIS publik (opsional)
- Simulasi data NMEA-0183

Format utama yang digunakan:

```text
$GPRMC
```

Parameter yang digunakan:

| Parameter | Fungsi |
|------------|------------|
| Timestamp | Perhitungan waktu |
| Latitude | Posisi kapal |
| Longitude | Posisi kapal |
| Speed Over Ground (SOG) | Kecepatan kapal |
| Course Over Ground (COG) | Arah pergerakan kapal |

---

# Arsitektur Sistem

```text
GPS Receiver
        │
        ▼
Data NMEA-0183
        │
        ▼
Parser NMEA
        │
        ▼
Mesin Deteksi
 ├─ Speed Check
 ├─ Rate of Turn Check
 ├─ Natuna Geofence Check
 └─ Border Proximity Check
        │
        ▼
Risk Scoring Engine
        │
        ▼
Normal / Low / Medium / High Risk
```

---

# Metode Deteksi

## 1. Speed Check

### Tujuan

Mendeteksi perpindahan posisi yang menghasilkan kecepatan tidak realistis.

### Input

- Latitude
- Longitude
- Timestamp

### Proses

Menghitung jarak menggunakan Haversine.

Kemudian:

```text
Speed = Distance / Time
```

### Contoh

```text
Jarak = 5 km
Waktu = 1 detik

Speed = 18.000 km/jam
```

### Hasil

```text
Abnormal Speed Detected
```

---

## 2. Rate of Turn Check

### Tujuan

Mendeteksi perubahan arah pelayaran yang tidak masuk akal.

### Input

- Course Over Ground (COG)

### Proses

Menghitung perubahan arah antar pembacaan GPS.

```text
ΔCOG = COG(t) - COG(t-1)
```

### Contoh Normal

```text
89°
90°
91°
90°
```

### Contoh Spoofing

```text
90°
91°
88°
250°
```

### Hasil

```text
Abnormal Course Change Detected
```

---

## 3. Natuna Operational Geofence Check

### Tujuan

Memastikan posisi kapal masih berada dalam area operasi yang telah ditentukan.

### Dasar Keterbaruan

MANA hanya melakukan pemeriksaan lingkungan secara umum (laut atau daratan).

Penelitian ini mengembangkan konsep geofence khusus untuk wilayah operasional Laut Natuna Utara.

### Proses

Sistem memeriksa apakah koordinat kapal berada di dalam batas wilayah penelitian.

### Hasil

```text
Inside Operational Area
```

atau

```text
Geofence Violation
```

---

## 4. Border Proximity Check

### Tujuan

Mendeteksi perubahan jarak terhadap batas wilayah operasi yang tidak realistis.

### Dasar Keterbaruan

Metode ini dirancang khusus untuk konteks Laut Natuna Utara yang memiliki kedekatan dengan wilayah perbatasan.

### Input

- Latitude
- Longitude

### Proses

Menghitung jarak kapal terhadap garis batas yang telah ditentukan.

### Contoh

```text
Posisi Asli

Distance to Border = 5 km
```

Setelah spoofing:

```text
Distance to Border = 60 km
```

Dalam waktu singkat.

### Hasil

```text
Border Proximity Anomaly
```

---

# Risk Scoring Engine

## Tujuan

Mengubah hasil deteksi dari sistem biner menjadi sistem berbasis tingkat risiko.

### Pembobotan Awal

| Parameter | Bobot |
|------------|------------|
| Speed Check | 25 |
| Rate of Turn Check | 25 |
| Geofence Check | 25 |
| Border Proximity Check | 25 |

### Perhitungan

```text
Risk Score
=
Σ Bobot Anomali
```

### Kategori Risiko

| Nilai | Status |
|---------|---------|
| 0–25 | Normal |
| 26–50 | Low Risk |
| 51–75 | Medium Risk |
| 76–100 | High Risk |

---

# Skenario Pengujian

## Skenario 1

Data GPS Normal

Expected Result:

```text
Risk Score Rendah
```

---

## Skenario 2

Sudden Jump Attack

Expected Result:

```text
Speed Anomaly
High Risk
```

---

## Skenario 3

Slow-Onset Drift Attack

Expected Result:

```text
Course Anomaly
Border Proximity Anomaly
Medium / High Risk
```

---

## Skenario 4

Geofence Manipulation Attack

Expected Result:

```text
Geofence Violation
High Risk
```

---

# Keterbaruan (Novelty)

## 1. Natuna Operational Geofence

Mengembangkan konsep geofence yang spesifik terhadap wilayah operasi Laut Natuna Utara.

## 2. Border Proximity Analysis

Menambahkan analisis jarak terhadap batas wilayah operasi yang belum menjadi fokus utama pada penelitian sebelumnya.

## 3. Risk Scoring-Based Detection

Mengubah mekanisme deteksi dari alert biner menjadi penilaian risiko bertingkat sehingga lebih informatif bagi operator kapal.

---

# Kontribusi Penelitian

1. Menyediakan solusi deteksi GPS Spoofing tanpa perangkat keras tambahan.
2. Menggunakan data NMEA-0183 yang tersedia pada GPS kapal nyata.
3. Mengadaptasi konsep MANA menjadi sistem yang lebih sederhana dan realistis untuk armada domestik.
4. Mengintegrasikan konteks operasional Laut Natuna Utara ke dalam mekanisme deteksi.
5. Menghasilkan sistem berbasis risk scoring yang dapat membantu pengambilan keputusan operator kapal.