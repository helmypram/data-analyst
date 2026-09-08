<?php
session_start();
include "koneksi.php";

$isLogin = isset($_SESSION['user_id']);
$isAdmin = $isLogin && $_SESSION['user_role'] === 'admin';

// --- PENGATURAN PAGINATION ---
$limit = 6;
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
$offset = ($page - 1) * $limit;

// --- Hitung total artikel untuk pagination ---
$totalResult = mysqli_query($conn, "SELECT COUNT(id) AS total FROM artikel");
$totalRow = mysqli_fetch_assoc($totalResult);
$totalArticles = $totalRow['total'];
$totalPages = ceil($totalArticles / $limit);

// --- Ambil data artikel untuk tampilan awal ---
$artikelList = [];
$sql = mysqli_query($conn, "
    SELECT a.*, COALESCE(AVG(u.rating), 0) AS avg_rating, COUNT(u.id) AS jumlah_ulasan
    FROM artikel a LEFT JOIN ulasan u ON u.slug = a.slug
    GROUP BY a.id ORDER BY a.id DESC LIMIT $limit OFFSET $offset
");
while ($a = mysqli_fetch_assoc($sql)) {
    $artikelList[] = $a;
}

// --- Favorit 4 destinasi dengan rating tertinggi [DIUBAH DARI 3 MENJADI 4] ---
$favoritList = [];
$favSQL = mysqli_query($conn, "
    SELECT a.*, COALESCE(AVG(u.rating), 0) AS avg_rating, COUNT(u.id) AS jumlah_ulasan
    FROM artikel a LEFT JOIN ulasan u ON u.slug = a.slug
    GROUP BY a.id ORDER BY avg_rating DESC, jumlah_ulasan DESC LIMIT 4
");
while ($f = mysqli_fetch_assoc($favSQL)) {
    $favoritList[] = $f;
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Go-Planet Bekasi</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
    <link rel="manifest" href="/site.webmanifest">
    <style>

        .page-item .page-link {
            color: #0d47a1;
            background-color: #fff;
            border: 1px solid #dee2e6;
        }

        .page-item .page-link:hover,
        .page-item .page-link:focus {
            background-color: #e3f2fd; /* Biru muda saat hover */
            color: #0d47a1;
            border-color: #0d47a1;
        }

        .page-item.active .page-link {
            background-color: #0d47a1;
            border-color: #0d47a1;
            color: white;
        }
        
            .page-item:not(.active) .page-link {
            background-color: #e3f2fd;
            color: #0d47a1;
            border: 1px solid #0d47a1;
        }


        body { font-family: 'Poppins', sans-serif; background-color: #f8f9fa; }
        .navbar { background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .navbar .navbar-brand, .navbar .nav-link { color: #0d47a1; font-weight: 600; }
        footer { background-color: #0d47a1; color: white; }
        
        .welcome-section { background-color: #e3f2fd; padding: 2rem 0; }
        .welcome-section h1 { font-size: 2.5rem; } /* Ukuran font H1 untuk desktop */

        #mapid { height: 445px; width: 100%; border-radius: 10px; z-index: 1; }
        
        .card { border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s; height: 100%; border: none; }
        .card:hover { transform: translateY(-5px); }
        .card-img-top { height: 200px; object-fit: cover; border-top-left-radius: 10px; border-top-right-radius: 10px;}
        .card-body { display: flex; flex-direction: column; }
        .card-title a { text-decoration: none; color: inherit; } /* Agar link di judul kartu tidak merusak style */
        .card-title a:hover { color: #0d47a1; } /* Warna saat hover di judul kartu */
        .card-text { color: #6c757d; font-size: 0.9rem; flex-grow: 1; margin-bottom: 1rem; }
        .rating-stars { color: #ffc107; }
        .rating-text { color: #6c757d; font-size: 0.9rem; margin-left: 0.5rem; }

        .favorit-list .card-header { background-color: #0d47a1; color: white; font-weight: 600; }
        .favorit-item { display: flex; align-items: center; gap: 15px; padding: 10px 0; border-bottom: 1px solid #eee; }
        .favorit-item:last-child { border-bottom: none; }
        .favorit-item img { width: 80px; height: 60px; object-fit: cover; border-radius: 8px; }
        .favorit-info a { text-decoration: none; } /* [DIUBAH] Menghilangkan garis bawah dari semua link di info favorit */
        .favorit-info .title-link { color: #212529; font-weight: 600; font-size: 0.95rem; }
        .favorit-info .title-link:hover { color: #0d47a1; }
        .favorit-info .detail-link { color: #1976d2; font-weight: 500; font-size: 0.9rem; }
        .favorit-info .rating { font-size: 0.85rem; }

        .page-item.active .page-link { background-color: #0d47a1; border-color: #0d47a1; }
        
        
        .page-link { 
            color: #0d47a1; 
        }
        /* Memastikan semua status link (hover, focus) juga berwarna biru */
        .page-link:hover, .page-link:focus {
            color: #0d47a1;
        }
        /* --- AKHIR DARI KODE YANG DIPERBAIKI --- */


        /* [RESPONSIVE CSS] Style khusus untuk layar kecil (smartphone) */
        @media (max-width: 767.98px) {
            .welcome-section h1 {
                font-size: 1.8rem; /* Perkecil ukuran judul utama di HP */
            }
            .welcome-section p {
                font-size: 0.95rem; /* Perkecil sedikit teks deskripsi */
            }
            #mapid {
                height: 300px; /* Kurangi tinggi peta di HP agar tidak memakan layar */
            }
            .favorit-list, #mapid {
                margin-bottom: 1.5rem !important; /* Tambah jarak bawah favorit & peta di HP */
            }
            .card-title {
                font-size: 1.1rem; /* Sesuaikan ukuran judul kartu */
            }
            .rating-text {
                display: block; /* Buat teks rating turun ke bawah jika tidak cukup ruang /
                margin-left: 0;
                margin-top: 5px;
            }
        }
    </style>
</head>
<body>

<?php include "navbar.php"; ?>

<section class="welcome-section">
    <div class="container text-center">
        <h1>Selamat Datang di Go-Planet Bekasi 🌏</h1>
        <p class="lead text-muted">
            Temukan dan jelajahi berbagai destinasi wisata menarik di Bekasi, mulai dari wisata alam, taman kota, pusat belanja, hingga tempat bersejarah.
        </p>
    </div>
</section>

<main class="container my-4">
    <div class="row g-3 mb-4 p-3 bg-white rounded shadow-sm align-items-center">
        <div class="col-md-4">
            <select id="kategori" class="form-select">
                <option value="">Semua Kategori</option>
                <option value="alam">Alam dan Ekowisata</option>
                <option value="edukasi">Edukasi</option>
                <option value="kuliner">Kuliner</option>
                <option value="olahraga dan rekreasi">Olahraga dan Rekreasi</option>
                <option value="belanja">Pusat Perbelanjaan</option>
                <option value="sejarah dan budaya">Sejarah dan Budaya</option>
                <option value="taman">Taman</option>
                <option value="wahana air">Wahana Air</option>
            </select>
        </div>
        <div class="col-md-8">
            <input type="text" id="search" class="form-control" placeholder="Cari nama wisata...">
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-lg-4">
            <div class="card favorit-list">
                <div class="card-header">Destinasi Terfavorit</div>
                <div class="card-body p-3">
                    <?php if (empty($favoritList)): ?>
                        <p class="text-muted text-center m-0">Belum ada destinasi favorit.</p>
                    <?php else: ?>
                        <?php foreach ($favoritList as $fav): ?>
                        <div class="favorit-item">
                            <img src="<?= htmlspecialchars($fav['gambar']) ?>" alt="<?= htmlspecialchars($fav['judul']) ?>">
                            <div class="favorit-info">
                                <a href="detail-artikel.php?slug=<?= $fav['slug'] ?>" class="title-link"><?= htmlspecialchars($fav['judul']) ?></a><br>
                                <span class="rating text-warning"><i class="bi bi-star-fill"></i> <?= number_format($fav['avg_rating'], 1) ?></span>
                                <span class="text-muted rating">(<?= $fav['jumlah_ulasan'] ?> ulasan)</span><br>
                                <a href="detail-artikel.php?slug=<?= $fav['slug'] ?>" class="detail-link">Lihat Detail</a>
                            </div>
                        </div>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>
        </div>
        <div class="col-lg-8">
            <div id="mapid"></div>
        </div>
    </div>
    
    <div class="row g-4" id="wisataList">
        <?php if (empty($artikelList)): ?>
            <div class="col-12"><p class="text-center text-muted">Tidak ada destinasi yang ditemukan.</p></div>
        <?php else: ?>
            <?php foreach ($artikelList as $item): ?>
            <div class="col-12 col-md-6 col-lg-4 d-flex align-items-stretch">
                <div class="card w-100">
                    <img src="<?= htmlspecialchars($item['gambar']) ?>" class="card-img-top" alt="<?= htmlspecialchars($item['judul']) ?>">
                    <div class="card-body p-3">
                        <h5 class="card-title">
                            <a href="detail-artikel.php?slug=<?= $item['slug'] ?>"><?= htmlspecialchars($item['judul']) ?></a>
                        </h5>
                        <p class="card-text"><?= htmlspecialchars(substr($item['deskripsi'], 0, 120)) ?>...</p>
                        <div class="mt-auto">
                            <div>
                                <span class="rating-stars">
                                    <?php 
                                    $rating = round($item['avg_rating']);
                                    for ($i = 0; $i < 5; $i++):
                                        echo $i < $rating ? '<i class="bi bi-star-fill"></i>' : '<i class="bi bi-star"></i>';
                                    endfor;
                                    ?>
                                </span>
                                <span class="rating-text">(<?= number_format($item['avg_rating'], 1) ?> dari <?= $item['jumlah_ulasan'] ?> ulasan)</span>
                            </div>
                            <a href="detail-artikel.php?slug=<?= $item['slug'] ?>" class="btn btn-primary w-100 mt-2">Lihat Detail</a>
                        </div>
                    </div>
                </div>
            </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>

    <nav class="mt-5" id="paginationContainer">
        <ul class="pagination justify-content-center">
            <?php if ($page > 1): ?><li class="page-item"><a class="page-link" href="?page=<?= $page - 1 ?>">«</a></li><?php endif; ?>
            <?php for ($i = 1; $i <= $totalPages; $i++): ?><li class="page-item<?= $i === $page ? ' active' : '' ?>"><a class="page-link" href="?page=<?= $i ?>"><?= $i ?></a></li><?php endfor; ?>
            <?php if ($page < $totalPages): ?><li class="page-item"><a class="page-link" href="?page=<?= $page + 1 ?>">»</a></li><?php endif; ?>
        </ul>
    </nav>
</main>

<footer class="mt-5 py-4 text-center text-white"><p class="mb-0">© <?= date('Y') ?> Go-Planet Bekasi. All rights reserved.</p></footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
// Kode JavaScript 
document.addEventListener('DOMContentLoaded', function () {
    const map = L.map('mapid').setView([-6.241586, 106.992416], 11);
    let markers = [];

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap'
    }).addTo(map);

    const wisataListContainer = document.getElementById('wisataList');
    const paginationContainer = document.getElementById('paginationContainer');
    const kategoriSelect = document.getElementById('kategori');
    const searchInput = document.getElementById('search');

    function renderCards(data) {
        wisataListContainer.innerHTML = '';
        if (data.length === 0) {
            wisataListContainer.innerHTML = '<div class="col-12"><p class="text-center text-muted">Tidak ada destinasi yang cocok dengan filter Anda.</p></div>';
            return;
        }
        data.forEach(item => {
            let stars = '';
            let rating = Math.round(item.avg_rating);
            for (let i = 0; i < 5; i++) {
                stars += i < rating ? '<i class="bi bi-star-fill"></i>' : '<i class="bi bi-star"></i>';
            }
            
            // Judul kartu pada hasil filter (JavaScript) bisa diklik
            const cardHtml = `
            <div class="col-12 col-md-6 col-lg-4 d-flex align-items-stretch">
                <div class="card w-100">
                    <img src="${item.gambar}" class="card-img-top" alt="${item.judul}">
                    <div class="card-body p-3">
                        <h5 class="card-title">
                            <a href="detail-artikel.php?slug=${item.slug}">${item.judul}</a>
                        </h5>
                        <p class="card-text">${item.deskripsi.substring(0, 120)}...</p>
                        <div class="mt-auto">
                           <div>
                                <span class="rating-stars">${stars}</span>
                                <span class="rating-text">(${parseFloat(item.avg_rating).toFixed(1)} dari ${item.jumlah_ulasan} ulasan)</span>
                           </div>
                            <a href="detail-artikel.php?slug=${item.slug}" class="btn btn-primary w-100 mt-2">Lihat Detail</a>
                        </div>
                    </div>
                </div>
            </div>`;
            wisataListContainer.innerHTML += cardHtml;
        });
    }

    function updateMap(data) {
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];
        if (data.length === 0) return;
        const bounds = [];
        data.forEach(item => {
            if (item.lat && item.lon) {
                const latLng = [item.lat, item.lon];
                const marker = L.marker(latLng)
                    .addTo(map)
                    .bindPopup(`<b>${item.judul}</b><br><a href="detail-artikel.php?slug=${item.slug}">Lihat Detail</a>`);
                markers.push(marker);
                bounds.push(latLng);
            }
        });

        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    async function filterData() {
        const kategori = kategoriSelect.value;
        const search = searchInput.value;

        if (kategori === '' && search === '') {
            window.location.href = window.location.pathname;
            return;
        }

        try {
            wisataListContainer.innerHTML = '<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            const response = await fetch(`api_filter_wisata.php?kategori=${kategori}&search=${search}`);
            const data = await response.json();
            
            renderCards(data);
            updateMap(data);
            paginationContainer.style.display = 'none';

        } catch (error) {
            console.error('Error fetching data:', error);
            wisataListContainer.innerHTML = '<div class="col-12"><p class="text-center text-danger">Terjadi kesalahan saat memuat data.</p></div>';
        }
    }

    kategoriSelect.addEventListener('change', filterData);
    searchInput.addEventListener('keyup', filterData);
    
    updateMap(<?= json_encode($artikelList) ?>);
});
</script>
</body>
</html>
