<?php
session_start();
$isLogin = isset($_SESSION['user_id']);
$isAdmin = $isLogin && $_SESSION['user_role'] === 'admin';
?>
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Tentang Kami - Go-Planet Bekasi</title>
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
    header .logo a {
      color: white;
      text-decoration: none;
      font-weight: bold;
      font-size: 1.5rem;
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
    footer {
      background-color: #0e4d92;
      color: white;
      text-align: center;
      padding: 1rem;
      margin-top: 2rem;
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

  </style>
</head>
<body>

<?php include "navbar.php"; ?>


<section class="bg-light py-5">
  <div class="container text-start" style="max-width: 800px;">
    
    <h2 class="text-center mb-4">Misi Kami: Menyinari Setiap Sudut Berharga di Bekasi</h2>
    
    <p class="lead text-muted">
      Go-Planet Bekasi lahir dari sebuah semangat sederhana: kecintaan pada kota kami dan keyakinan bahwa setiap sudutnya menyimpan cerita yang layak untuk dibagikan.
    </p>
    
    <p>
      Kami adalah tim pengembang web, desainer, dan analis data muda yang tergerak untuk menjawab tantangan: bagaimana kita bisa memajukan pariwisata lokal melalui kekuatan teknologi informasi?
    </p>
    
    <p>
      Dengan latar belakang di bidang sistem informasi, desain antarmuka (UI/UX), dan pemetaan geospasial, kami tidak hanya membangun sebuah website. Kami merancang sebuah <strong>jembatan digital</strong>.
    </p>
    
    <p>
      Sebuah jembatan yang menghubungkan rasa penasaran Anda dengan permata-permata tersembunyi di Kota Bekasi—mulai dari taman kota yang meneduhkan, cagar budaya yang sarat sejarah, hingga pusat kuliner yang menggugah selera. Kami berupaya keras agar platform ini ramah pengguna, kaya informasi, dan memikat secara visual.
    </p>

    <p>
      Kami percaya teknologi bisa mengubah cara kita memandang "rumah" kita sendiri. Go-Planet Bekasi adalah wujud dari mimpi tersebut; menjadi etalase digital bagi kekayaan budaya dan alam daerah ini untuk semua orang—baik Anda penduduk asli Bekasi, maupun wisatawan yang datang dengan semangat eksplorasi.
    </p>
    
    <p class="mt-4">
      Perjalanan ini tidak akan lengkap <strong>tanpa Anda</strong>. Setiap ulasan, rating, dan rekomendasi yang Anda bagikan adalah bahan bakar yang membuat ekosistem ini terus tumbuh. Mari bersama-sama kita bangun peta wisata lokal yang lebih hidup, kuat, dan dikenal luas, demi masa depan pariwisata Bekasi yang gemilang!
    </p>

  </div>
</section>

<footer>
  <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
