<?php
if (session_status() === PHP_SESSION_NONE) {
  session_start();
}
$isLogin = isset($_SESSION['user_id']);
$isAdmin = $isLogin && $_SESSION['user_role'] === 'admin';
?>
<style>
  header.sticky-navbar {
    background-color: #0e4d92;
    color: white;
    padding: 1rem;
    position: fixed;
    top: 0;
    width: 100%;
    z-index: 1030;
  }

  body {
    padding-top: 80px;
  }

  header h1 a {
    color: white;
    text-decoration: none;
  }

  nav a {
    color: white !important;
    margin-left: 1rem;
    font-weight: 500;
    text-decoration: none !important;
  }

  nav a:hover {
    color: #ffffff !important;
    text-decoration: none !important;
  }

  .dropdown-menu {
    z-index: 1031;
  }

  .dropdown-menu a {
    color: #212529 !important;
    font-weight: 500;
    text-decoration: none !important;
  }

  .dropdown-menu a:hover {
    color: #0d6efd !important;
    text-decoration: underline !important;
  }

  /* Tombol dropdown tetap outline-light, tapi tidak putih saat aktif */
  .btn-outline-light.dropdown-toggle:focus,
  .btn-outline-light.dropdown-toggle:active,
  .btn-outline-light.dropdown-toggle.show {
    background-color: #0e4d92 !important;
    color: white !important;
    border-color: #ffffff !important;
    box-shadow: none;
  }
</style>

<header class="sticky-navbar d-flex justify-content-between align-items-center px-4">
  <h1 class="h4 m-0">
    <a href="/index.php">Go-Planet Bekasi</a>
  </h1>
  <nav class="d-flex align-items-center">
    <a href="/index.php" class="me-3">Beranda</a>
    <a href="/tentang_kami.php" class="me-3">Tentang Kami</a>
    <?php if ($isLogin && $isAdmin): ?>
      <a href="/admin_tambah_artikel.php" class="me-3">Kelola Artikel</a>
    <?php endif; ?>
    <div class="dropdown">
      <a class="btn btn-outline-light dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
        <i class="bi bi-person-circle"></i>
      </a>
      <ul class="dropdown-menu dropdown-menu-end">
        <?php if ($isLogin): ?>
          <li><a class="dropdown-item" href="/profil_saya.php">Profil & Ulasan Saya</a></li>
          <li><hr class="dropdown-divider"></li>
          <li><a class="dropdown-item text-danger" href="/logout.php">Logout</a></li>
        <?php else: ?>
          <li><a class="dropdown-item" href="/login.php">Login</a></li>
          <li><a class="dropdown-item" href="/register.php">Register</a></li>
        <?php endif; ?>
      </ul>
    </div>
  </nav>
</header>
