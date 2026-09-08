<?php 
session_start();
include "koneksi.php";

if (!isset($_SESSION['user_id'])) {
  echo "<script>alert('Anda harus login untuk memberi ulasan.'); window.location.href='login.html';</script>";
  exit;
}

if ($_SERVER["REQUEST_METHOD"] == "POST") {
  $user_id = $_SESSION['user_id'];
  $wisata = mysqli_real_escape_string($conn, $_POST['wisata']);
  $slug = mysqli_real_escape_string($conn, $_POST['slug']);
  $rating = (int) $_POST['rating'];
  $komentar = mysqli_real_escape_string($conn, $_POST['komentar']);

  if ($rating < 1 || $rating > 5 || empty($komentar)) {
    echo "<script>alert('Rating dan komentar wajib diisi.'); history.back();</script>";
    exit;
  }

  $query = "INSERT INTO ulasan (user_id, wisata, slug, rating, komentar) 
            VALUES ('$user_id', '$wisata', '$slug', '$rating', '$komentar')";

  if (mysqli_query($conn, $query)) {
    echo "<script>alert('Ulasan berhasil dikirim!'); window.location.href='detail-artikel.php?slug=$slug';</script>";
  } else {
    echo "<script>alert('Gagal menyimpan ulasan: " . mysqli_error($conn) . "'); history.back();</script>";
  }
} else {
  echo "<script>alert('Akses tidak valid.'); window.location.href='index.php';</script>";
}
?>
