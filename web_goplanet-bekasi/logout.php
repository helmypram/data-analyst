<?php
session_start();
session_unset();
session_destroy();
header("Location: index.php"); // atau ke halaman home lain seperti dashboard.php jika perlu
exit;
?>
