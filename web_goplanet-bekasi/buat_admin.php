<?php
include "koneksi.php";

$nama = "admin";
$email = "admin@goplanetbekasi.com";
$password = password_hash("admin123", PASSWORD_DEFAULT); // Enkripsi
$role = "admin";

// Cek apakah sudah ada
$cek = mysqli_query($conn, "SELECT * FROM users WHERE email = '$email'");
if (mysqli_num_rows($cek) === 0) {
    $query = "INSERT INTO users (nama, email, password, role, created_at) VALUES 
              ('$nama', '$email', '$password', '$role', NOW())";

    if (mysqli_query($conn, $query)) {
        echo "Admin berhasil dibuat!";
    } else {
        echo "Gagal: " . mysqli_error($conn);
    }
} else {
    echo "Admin sudah ada.";
}
?>
