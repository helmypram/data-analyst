<?php
session_start();
include "koneksi.php";

// Proses form jika disubmit
if ($_SERVER["REQUEST_METHOD"] == "POST") {
  if (isset($_POST['name'], $_POST['email'], $_POST['password'])) {
    $nama = mysqli_real_escape_string($conn, $_POST['name']);
    $email = mysqli_real_escape_string($conn, $_POST['email']);
    $password = password_hash($_POST['password'], PASSWORD_DEFAULT);

    // Cek apakah email sudah terdaftar
    $cek = mysqli_query($conn, "SELECT * FROM users WHERE email='$email'");
    if (mysqli_num_rows($cek) > 0) {
      echo "<script>
        alert('Email sudah terdaftar. Silakan login.');
        window.location.href = 'register.php';
      </script>";
      exit;
    }

    // Insert data
    $query = "INSERT INTO users (nama, email, password) VALUES ('$nama', '$email', '$password')";
    if (mysqli_query($conn, $query)) {
      echo "<script>
        alert('Pendaftaran berhasil! Silakan login.');
        window.location.href = 'login.php';
      </script>";
      exit;
    } else {
      echo "<script>
        alert('Gagal mendaftar: " . mysqli_error($conn) . "');
        window.location.href = 'register.php';
      </script>";
      exit;
    }
  } else {
    echo "<script>
      alert('Data tidak lengkap. Silakan isi semua field.');
      window.location.href = 'register.php';
    </script>";
    exit;
  }
}
?>

<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Register - Go-Planet Bekasi</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Poppins', sans-serif;
      background-color: #f8f9fa;
    }

        a {
      text-decoration: none;
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

    .register-container {
      max-width: 400px;
      margin: 4rem auto;
      background-color: white;
      padding: 2rem;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }
    .register-container h2 {
      text-align: center;
      margin-bottom: 1.5rem;
      color: #0e4d92;
    }
    .form-label {
      font-weight: 500;
    }
    footer {
      background-color: #0e4d92;
      color: white;
      text-align: center;
      padding: 1rem;
      margin-top: 4rem;
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
  </style>
</head>
<body>

<?php include 'navbar.php'; ?>

<div class="register-container">
  <h2>Daftar Akun</h2>
  <form action="register.php" method="POST">
    <div class="mb-3">
      <label for="name" class="form-label">Nama Lengkap</label>
      <input type="text" class="form-control" id="name" name="name" placeholder="Masukkan nama lengkap" required />
    </div>
    <div class="mb-3">
      <label for="email" class="form-label">Email</label>
      <input type="email" class="form-control" id="email" name="email" placeholder="Masukkan email" required />
    </div>
    <div class="mb-3">
      <label for="password" class="form-label">Password</label>
      <input type="password" class="form-control" id="password" name="password" placeholder="Buat password" required />
    </div>
    <button type="submit" class="btn btn-primary w-100">Register</button>
  </form>

  <div class="text-center mt-3">
    Sudah punya akun? <a href="login.php" class="fw-semibold text-decoration-none text-primary">Login di sini</a>
  </div>
</div>

<footer>
  <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
