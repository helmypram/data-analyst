<?php
session_start();
include "koneksi.php";

// Cek status login
$isLogin = isset($_SESSION['user_id']);

// Proses login saat form disubmit
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST['email'], $_POST['password'])) {
    $email = $_POST['email'];
    $password = $_POST['password'];

    $query = mysqli_query($conn, "SELECT * FROM users WHERE email = '$email'");
    $user = mysqli_fetch_assoc($query);

    if ($user && password_verify($password, $user['password'])) {
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_nama'] = $user['nama'];
        $_SESSION['user_role'] = $user['role'];
        header("Location: index.php");
        exit;
    } else {
        $error = "Email atau password salah.";
    }
}
?>

<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Login - Go-Planet Bekasi</title>

  <!-- CDN CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet" />
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet" />

  <!-- Internal CSS -->
  <style>
    html, body {
      height: 100%;
      margin: 0;
      font-family: 'Poppins', sans-serif;
      background-color: #f4f4f4;
      display: flex;
      flex-direction: column;
    }

    header {
      background-color: #0e4d92;
      padding: 1rem 2rem;
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    header h1 {
      margin: 0;
      font-size: 1.5rem;
    }

    header h1 a {
      color: white;
      text-decoration: none;
    }

    nav {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    nav a {
      color: white;
      text-decoration: none;
      font-weight: 500;
    }

    nav a:hover {
      text-decoration: underline;
    }

    main.main {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 2rem;
    }

    .login-container {
      width: 100%;
      max-width: 400px;
      background-color: white;
      padding: 2rem;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }

    .login-container h2 {
      text-align: center;
      margin-bottom: 1.5rem;
      color: #0e4d92;
    }

    .login-container label {
      font-weight: 500;
      margin-top: 1rem;
      display: block;
    }

    .login-container input {
      width: 100%;
      padding: 0.75rem;
      margin-top: 0.5rem;
      border: 1px solid #ccc;
      border-radius: 5px;
      font-size: 1rem;
    }

    .login-container button {
      width: 100%;
      padding: 0.75rem;
      background-color: #0e4d92;
      color: white;
      border: none;
      border-radius: 5px;
      font-weight: bold;
      margin-top: 1.5rem;
      font-size: 1rem;
      cursor: pointer;
    }

    .login-container button:hover {
      background-color: #09376b;
    }

    .register-link {
      text-align: center;
      margin-top: 1rem;
      font-size: 0.95rem;
    }

    .register-link a {
      color: #0e4d92;
      text-decoration: none;
      font-weight: 600;
    }

    .register-link a:hover {
      text-decoration: underline;
    }

    footer {
      background-color: #0e4d92;
      color: white;
      text-align: center;
      padding: 1rem;
    }

    .dropdown .btn {
      padding: 0.375rem 0.75rem;
      font-size: 1rem;
      line-height: 1;
    }

    .alert-danger {
      margin-top: 1rem;
    }
  </style>
</head>
<body>
  <!-- pengganti Header -->
<?php include "navbar.php"; ?>

  <!-- Login Form -->
  <main class="main">
    <div class="login-container">
      <h2>Login</h2>

      <?php if (isset($error)): ?>
        <div class="alert alert-danger" role="alert">
          <?= $error ?>
        </div>
      <?php endif; ?>

      <form action="login.php" method="POST">
        <label for="email">Email</label>
        <input type="email" id="email" name="email" placeholder="Masukkan email" required />

        <label for="password">Password</label>
        <input type="password" id="password" name="password" placeholder="Masukkan password" required />

        <button type="submit">Login</button>
      </form>

      <div class="register-link">
        Belum punya akun? <a href="register.php">Daftar di sini</a>
      </div>
    </div>
  </main>

  <!-- Footer -->
  <footer>
    <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
  </footer>

  <!-- Bootstrap JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
