<?php
session_start();
include "koneksi.php";

if (!isset($_SESSION['user_id'])) {
  header("Location: login.html");
  exit;
}

$userId = $_SESSION['user_id'];
$userRole = $_SESSION['user_role'] ?? '';
$isAdmin = $userRole === 'admin';

$queryUser = mysqli_query($conn, "SELECT * FROM users WHERE id = '$userId'");
$user = mysqli_fetch_assoc($queryUser);

$queryUlasan = mysqli_query($conn, "
  SELECT a.judul, r.rating, r.komentar, r.created_at
  FROM ulasan r
  JOIN artikel a ON r.slug = a.slug
  WHERE r.user_id = '$userId'
  ORDER BY r.created_at DESC
");
?>
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Profil & Ulasan Saya - Go-Planet Bekasi</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Poppins', sans-serif;
      background-color: #f8f9fa;
    }
    header {
      background-color: #0e4d92;
      color: white;
      padding: 1rem;
    }
    nav a {
      color: white;
      margin-left: 1rem;
      text-decoration: none;
      font-weight: 500;
    }
    nav a:hover {
      text-decoration: underline;
    }
    h1 a {
      color: white;
      text-decoration: none;
    }
    footer {
      background-color: #0e4d92;
      color: white;
      text-align: center;
      padding: 1rem;
      margin-top: 2rem;
    }
    .rating {
      font-weight: bold;
      color: #ffcc00;
    }
  </style>
</head>
<body>

<?php include 'navbar.php'; ?>

<div class="container py-5">
  <h2 class="mb-4">Profil Saya</h2>
  <div class="card p-4 mb-5 shadow-sm">
    <p><strong>Nama:</strong> <?= htmlspecialchars($user['nama']) ?></p>
    <p><strong>Email:</strong> <?= htmlspecialchars($user['email']) ?></p>
    <p><strong>Role:</strong> <?= htmlspecialchars($user['role']) ?></p>
  </div>

  <h2 class="mb-4">Ulasan Saya</h2>
  <?php if (mysqli_num_rows($queryUlasan) > 0): ?>
    <?php while ($row = mysqli_fetch_assoc($queryUlasan)): ?>
      <div class="card mb-3 p-3 shadow-sm">
        <h5><?= htmlspecialchars($row['judul']) ?></h5>
        <p class="rating"><?= str_repeat("⭐", $row['rating']) ?></p>
        <p><?= nl2br(htmlspecialchars($row['komentar'])) ?></p>
        <small class="text-muted"><?= $row['created_at'] ?></small>
      </div>
    <?php endwhile; ?>
  <?php else: ?>
    <p>Anda belum memberikan ulasan.</p>
  <?php endif; ?>
</div>

<footer>
  <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
