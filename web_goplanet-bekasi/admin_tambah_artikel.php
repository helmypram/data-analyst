<?php
session_start();
include "koneksi.php";

// Cek admin
if (!isset($_SESSION['user_role']) || $_SESSION['user_role'] !== 'admin') {
    echo "Akses ditolak.";
    exit;
}

// Hapus artikel
if (isset($_GET['hapus'])) {
    $id = (int) $_GET['hapus'];
    mysqli_query($conn, "DELETE FROM artikel WHERE id=$id");
    header("Location: admin_tambah_artikel.php");
    exit;
}

// Hapus ulasan
if (isset($_GET['hapus_ulasan'])) {
    $id = (int) $_GET['hapus_ulasan'];
    mysqli_query($conn, "DELETE FROM ulasan WHERE id=$id");
    header("Location: admin_tambah_artikel.php");
    exit;
}

// Simpan data artikel
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $judul = $_POST['judul'];
    $deskripsi = $_POST['deskripsi'];
    $gambar = $_POST['gambar'];
    $lat = str_replace('−', '-', $_POST['lat']);
    $lon = str_replace('−', '-', $_POST['lon']);
    $kategori = $_POST['kategori'];

    function generate_slug($text) {
        $text = strtolower($text);
        $text = preg_replace('/[^a-z0-9]+/i', '-', $text);
        return trim($text, '-');
    }

    $slug = generate_slug($judul);

    if (isset($_POST['id_edit'])) {
        $id_edit = (int) $_POST['id_edit'];
        $stmt = mysqli_prepare($conn, "UPDATE artikel SET judul=?, deskripsi=?, gambar=?, lat=?, lon=?, kategori=?, slug=? WHERE id=?");
        mysqli_stmt_bind_param($stmt, "sssddssi", $judul, $deskripsi, $gambar, $lat, $lon, $kategori, $slug, $id_edit);
        mysqli_stmt_execute($stmt);
    } else {
        $stmt = mysqli_prepare($conn, "INSERT INTO artikel (judul, deskripsi, gambar, lat, lon, kategori, slug) VALUES (?, ?, ?, ?, ?, ?, ?)");
        mysqli_stmt_bind_param($stmt, "sssddss", $judul, $deskripsi, $gambar, $lat, $lon, $kategori, $slug);
        mysqli_stmt_execute($stmt);
    }

    if (mysqli_stmt_affected_rows($stmt) > 0) {
        echo "<script>alert('Artikel berhasil disimpan!'); window.location.href='admin_tambah_artikel.php';</script>";
        exit;
    } else {
        $error = "Gagal menyimpan artikel: " . mysqli_error($conn);
    }
}

// Ambil data artikel & ulasan
$editData = null;
if (isset($_GET['edit'])) {
    $id_edit = (int) $_GET['edit'];
    $res = mysqli_query($conn, "SELECT * FROM artikel WHERE id=$id_edit");
    $editData = mysqli_fetch_assoc($res);
}

$artikelList = [];
$all = mysqli_query($conn, "SELECT * FROM artikel ORDER BY id DESC");
while ($row = mysqli_fetch_assoc($all)) {
    $artikelList[] = $row;
}

$ulasanList = [];
$ulasanQuery = mysqli_query($conn, "
  SELECT r.id, u.nama, r.slug, r.rating, r.komentar, r.created_at 
  FROM ulasan r 
  JOIN users u ON r.user_id = u.id 
  ORDER BY r.created_at DESC
");
while ($row = mysqli_fetch_assoc($ulasanQuery)) {
    $ulasanList[] = $row;
}
?>

<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Kelola Artikel - Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet" />
    <style>
        body {
            background: #f4f4f4;
            font-family: 'Poppins', sans-serif;
            padding-bottom: 2rem;
        }
        .container {
            max-width: 900px;
            margin: 2rem auto;
            background: #fff;
            padding: 2rem;
            border-radius: 10px;
        }
        h2 {
            color: #0e4d92;
        }
        input, textarea, select {
            margin-bottom: 1rem;
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
<?php include 'navbar.php'; ?>

<div class="container">
    <h2><?= $editData ? "Edit" : "Tambah" ?> Artikel</h2>

    <?php if (isset($error)): ?>
        <div class="alert alert-danger"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <form method="POST">
        <?php if ($editData): ?><input type="hidden" name="id_edit" value="<?= $editData['id'] ?>"><?php endif; ?>
        <label>Judul</label>
        <input class="form-control" type="text" name="judul" required value="<?= $editData['judul'] ?? '' ?>">
        <label>Deskripsi</label>
        <textarea class="form-control" name="deskripsi" rows="4" required><?= $editData['deskripsi'] ?? '' ?></textarea>
        <label>Link Gambar</label>
        <input class="form-control" type="text" name="gambar" required value="<?= $editData['gambar'] ?? '' ?>">
        <label>Latitude</label>
        <input class="form-control" type="text" name="lat" required value="<?= $editData['lat'] ?? '' ?>">
        <label>Longitude</label>
        <input class="form-control" type="text" name="lon" required value="<?= $editData['lon'] ?? '' ?>">
        <label>Kategori</label>
        <select class="form-select" name="kategori" required>
            <?php
            $kategoriList = [
                "alam" => "Alam dan Ekowisata",
                "edukasi" => "Edukasi",
                "kuliner" => "Kuliner",
                "olahraga dan rekreasi" => "Olahraga dan Rekreasi",
                "belanja" => "Pusat Perbelanjaan",
                "sejarah dan budaya" => "Sejarah dan Budaya",
                "taman" => "Taman",
                "wahana air" => "Wahana Air"
            ];
            foreach ($kategoriList as $key => $label):
                $selected = ($editData['kategori'] ?? '') === $key ? 'selected' : '';
                echo "<option value='$key' $selected>$label</option>";
            endforeach;
            ?>
        </select>
        <button class="btn btn-primary mt-2" type="submit">Simpan Artikel</button>
    </form>

    <h2 class="mt-5">Daftar Artikel</h2>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>No</th>
                <th>Judul</th>
                <th>Kategori</th>
                <th>Lat</th>
                <th>Lon</th>
                <th>Aksi</th>
            </tr>
        </thead>
        <tbody>
        <?php 
        $no_artikel = 1; // Inisialisasi nomor untuk artikel
        foreach ($artikelList as $a): ?>
            <tr>
                <td><?= $no_artikel++ ?></td> <td><?= htmlspecialchars($a['judul']) ?></td>
                <td><?= htmlspecialchars($a['kategori']) ?></td>
                <td><?= rtrim(rtrim($a['lat'], '0'), '.') ?></td>
                <td><?= rtrim(rtrim($a['lon'], '0'), '.') ?></td>
                <td>
                    <a href="?edit=<?= $a['id'] ?>" class="btn btn-sm btn-warning">Edit</a>
                    <a href="?hapus=<?= $a['id'] ?>" onclick="return confirm('Hapus artikel ini?')" class="btn btn-sm btn-danger">Hapus</a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>

    <h2 class="mt-5">Daftar Ulasan</h2>
    <table class="table table-bordered">
        <thead>
            <tr>
                <th>No</th>
                <th>Nama</th>
                <th>Slug</th>
                <th>Rating</th>
                <th>Komentar</th>
                <th>Tanggal</th>
                <th>Aksi</th>
            </tr>
        </thead>
        <tbody>
        <?php 
        $no_ulasan = 1; // Inisialisasi nomor untuk ulasan
        foreach ($ulasanList as $u): ?>
            <tr>
                <td><?= $no_ulasan++ ?></td> <td><?= htmlspecialchars($u['nama']) ?></td>
                <td><?= htmlspecialchars($u['slug']) ?></td>
                <td><?= $u['rating'] ?></td>
                <td><?= htmlspecialchars($u['komentar']) ?></td>
                <td><?= $u['created_at'] ?></td>
                <td><a href="?hapus_ulasan=<?= $u['id'] ?>" onclick="return confirm('Hapus ulasan ini?')" class="btn btn-sm btn-danger">Hapus</a></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<footer>
    <p class="mb-0">&copy; 2025 Go-Planet Bekasi. All rights reserved.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>