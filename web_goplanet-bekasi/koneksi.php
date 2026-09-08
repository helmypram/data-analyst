<?php
$host = "sql108.infinityfree.com";
$user = "if0_39311646";
$pass = "Pramudita13";
$db = "if0_39311646_goplanetbekasi";

$conn = mysqli_connect($host, $user, $pass, $db);

if (!$conn) {
  die("Koneksi gagal: " . mysqli_connect_error());
}
?>
