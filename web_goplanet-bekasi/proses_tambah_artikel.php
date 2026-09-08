<?php
session_start();
include "koneksi.php";

// Cek apakah user adalah admin
if (!isset($_SESSION['user_role']) || $_SESSION['user_role'] !== 'admin') {
    exit("Unauthorized.");
}

// Ambil data dari form
$judul = $_POST['judul'];
$deskripsi = $_POST['deskripsi'];
$gambar = $_POST['gambar'];
$lat = $_POST['lat'];
$lon = $_POST['lon'];
$kategori = $_POST['kategori'];

// Gunakan prepared statement untuk keamanan
$stmt = $conn->prepare("INSERT INTO artikel (judul, deskripsi, gambar, lat, lon, kategori) VALUES (?, ?, ?, ?, ?, ?)");
$stmt->bind_param("ssssss", $judul, $deskripsi, $gambar, $lat, $lon, $kategori);

if ($stmt->execute()) {
    echo "<script>alert('Artikel berhasil ditambahkan!'); window.location.href='admin_tambah_artikel.php';</script>";
} else {
    echo "Gagal menambahkan artikel: " . htmlspecialchars($stmt->error);
}

$stmt->close();
$conn->close();
?>
