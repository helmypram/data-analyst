<?php
session_start();
include "koneksi.php";

$isLogin = isset($_SESSION['user_id']);
$isAdmin = $isLogin && $_SESSION['user_role'] === 'admin';

$slug = $_GET['slug'] ?? '';
$query = mysqli_query($conn, "SELECT * FROM artikel WHERE slug='$slug'");
$data = mysqli_fetch_assoc($query);

if (!$data) {
  echo "Artikel tidak ditemukan.";
  exit;
}

$ulasan = [];
$res = mysqli_query($conn, "SELECT u.nama, r.rating, r.komentar, r.created_at 
                             FROM ulasan r 
                             JOIN users u ON r.user_id = u.id 
                             WHERE r.slug='$slug' 
                             ORDER BY r.created_at DESC");
while ($row = mysqli_fetch_assoc($res)) {
  $ulasan[] = $row;
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title><?= htmlspecialchars($data['judul']) ?> - Go-Planet Bekasi</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet" />
  <link href="https://unpkg.com/leaflet/dist/leaflet.css" rel="stylesheet" />
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet" />
  <style>
    body {
      font-family: 'Poppins', sans-serif;
      background-color: #f8f9fa;
    }

        a {
      text-decoration: none;
    }

    nav a {
      color: white;
      margin-left: 1rem;
      font-weight: 500;
      text-decoration: none !important;
    }

    nav a:hover {
      text-decoration: underline;
    }

    .dropdown-menu a {
      text-decoration: none !important;
      color: #000;
    }

    .dropdown-menu a:hover {
      text-decoration: underline;
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
    h1 a:hover {
      text-decoration: underline;
    }
    #mini-map {
      height: 300px;
      border-radius: 10px;
      margin-bottom: 1rem;
    }
    .rating-stars {
      direction: rtl;
      display: flex;
      gap: 5px;
    }
    .rating-stars input {
      display: none;
    }
    .rating-stars label {
      font-size: 1.8rem;
      color: #ccc;
      cursor: pointer;
    }
    .rating-stars input:checked ~ label,
    .rating-stars label:hover,
    .rating-stars label:hover ~ label {
      color: gold;
    }
    footer {
      background-color: #0e4d92;
      color: white;
      text-align: center;
      padding: 1rem;
      margin-top: 2rem;
    }
  </style>
</head>
<body>

<?php include "navbar.php"; ?>

<main class="container my-4">
  <div class="card">
    <div class="card-body">
      <h2 class="mb-3"><?= htmlspecialchars($data['judul']) ?></h2>
      <img src="<?= htmlspecialchars($data['gambar']) ?>" alt="<?= htmlspecialchars($data['judul']) ?>" class="img-fluid rounded mb-3">
      <p><?= nl2br(htmlspecialchars($data['deskripsi'])) ?></p>
      <p><strong>Lokasi:</strong> <?= $data['lat'] ?>, <?= $data['lon'] ?></p>
      <p><strong>Rute:</strong> <a href="https://www.google.com/maps/dir/?api=1&destination=<?= $data['lat'] ?>,<?= $data['lon'] ?>" target="_blank">📍 Buka Google Maps</a></p>

      <h5 class="mt-4">Peta Lokasi</h5>
      <div id="mini-map"></div>

      <h5 class="mt-4">Beri Ulasan</h5>
      <?php if ($isLogin): ?>
        <form action="simpan_ulasan.php" method="POST">
          <input type="hidden" name="slug" value="<?= $slug ?>">
          <div class="rating-stars mb-2">
            <input type="radio" id="star5" name="rating" value="5"><label for="star5">★</label>
            <input type="radio" id="star4" name="rating" value="4"><label for="star4">★</label>
            <input type="radio" id="star3" name="rating" value="3"><label for="star3">★</label>
            <input type="radio" id="star2" name="rating" value="2"><label for="star2">★</label>
            <input type="radio" id="star1" name="rating" value="1"><label for="star1">★</label>
          </div>
          <textarea name="komentar" class="form-control" placeholder="Tulis ulasan Anda..." required></textarea>
          <button type="submit" class="btn btn-primary mt-2">Kirim</button>
        </form>
      <?php else: ?>
        <p><a href="../login.php">Login</a> untuk memberikan ulasan dan rating.</p>
      <?php endif; ?>

      <h5 class="mt-4">Ulasan Pengunjung</h5>
      <?php foreach ($ulasan as $u): ?>
        <div class="border-top pt-2 mt-2">
          <strong><?= htmlspecialchars($u['nama']) ?></strong>
          <small class="text-muted">(<?= $u['created_at'] ?>)</small><br>
          <?= str_repeat("⭐", $u['rating']) ?><br>
          <?= nl2br(htmlspecialchars($u['komentar'])) ?>
        </div>
      <?php endforeach; ?>
    </div>
  </div>
</main>

<footer>
  <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
  const lat = <?= $data['lat'] ?>;
  const lon = <?= $data['lon'] ?>;
  const map = L.map('mini-map').setView([lat, lon], 15);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  L.marker([lat, lon]).addTo(map)
    .bindPopup("<?= htmlspecialchars($data['judul']) ?>")
    .openPopup();
</script>

</body>
</html>
