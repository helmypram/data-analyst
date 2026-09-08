<?php
// File ini berfungsi sebagai endpoint API untuk filter AJAX
header('Content-Type: application/json');
include "koneksi.php";

// Ambil parameter dari request GET
$kategori = isset($_GET['kategori']) ? $_GET['kategori'] : '';
$search = isset($_GET['search']) ? $_GET['search'] : '';

// Bangun query SQL secara dinamis dan aman
$sql = "
    SELECT a.*, 
           COALESCE(AVG(u.rating), 0) AS avg_rating, 
           COUNT(u.id) AS jumlah_ulasan
    FROM artikel a
    LEFT JOIN ulasan u ON u.slug = a.slug
";

$whereClauses = [];
$params = [];
$types = '';

if (!empty($kategori)) {
    $whereClauses[] = "a.kategori = ?";
    $params[] = $kategori;
    $types .= 's';
}

if (!empty($search)) {
    $whereClauses[] = "a.judul LIKE ?";
    $params[] = '%' . $search . '%';
    $types .= 's';
}

if (!empty($whereClauses)) {
    $sql .= " WHERE " . implode(" AND ", $whereClauses);
}

$sql .= " GROUP BY a.id ORDER BY a.id DESC";

// Gunakan prepared statement untuk keamanan dari SQL Injection
$stmt = mysqli_prepare($conn, $sql);

if (!empty($params)) {
    $bind_args = [$types];
    for ($i = 0; $i < count($params); $i++) {
        $bind_args[] = &$params[$i];
    }
    call_user_func_array([$stmt, 'bind_param'], $bind_args);
}

mysqli_stmt_execute($stmt);
$result = mysqli_stmt_get_result($stmt);

$artikelList = [];
while ($a = mysqli_fetch_assoc($result)) {
    // [SOLUSI] Membersihkan setiap kolom data untuk mencegah error JSON dari karakter tidak valid
    foreach ($a as $key => $value) {
        if (is_string($value)) {
            // Konversi paksa ke UTF-8, memperbaiki karakter yang rusak
            $a[$key] = mb_convert_encoding($value, 'UTF-8', 'UTF-8');
        }
    }
    $artikelList[] = $a;
}

mysqli_stmt_close($stmt);
mysqli_close($conn);

// Kembalikan hasil dalam format JSON
// Menambahkan flag JSON_INVALID_UTF8_SUBSTITUTE sebagai lapisan pertahanan ekstra (memerlukan PHP 7.2+)
echo json_encode($artikelList, JSON_INVALID_UTF8_SUBSTITUTE);

?>