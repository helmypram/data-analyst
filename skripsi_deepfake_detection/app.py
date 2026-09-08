import os
import json
import cv2
import uuid
import inspect
import numpy as np
import tensorflow as tf
from datetime import datetime, timedelta

from flask import (Flask, request, jsonify, render_template, redirect,
                   url_for, flash, abort, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, ScanHistory

# ─── KONFIGURASI AI & BACKBONE ───
from mtcnn.mtcnn import MTCNN
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.applications import EfficientNetB0, EfficientNetB2, ResNet50, Xception
from tensorflow.keras.applications.efficientnet import preprocess_input as eff_pre
from tensorflow.keras.applications.resnet import preprocess_input as res_pre
from tensorflow.keras.applications.xception import preprocess_input as xcep_pre

# ─── FLASK APP ───
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ueu-si-helmy-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///deepfake_skripsi.db'
#app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024 50mb
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024 #200mb
app.config['UPLOAD_FOLDER'] = os.path.join('arsip', 'videos')
# Berapa lama video diarsipkan sebelum dihapus otomatis (hari).
RETENSI_HARI = 30

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─── AI CONFIG ───
BASE_DIR  = os.getenv("BASE_DIR",  r"D:\Semester 6\celeb-v2")
BACKBONE  = os.getenv("BACKBONE",  "resnet50").lower()
MODEL_DIR = os.path.join(BASE_DIR, f"final_trained_model_mtcnn_v7_single_3_{BACKBONE}")
MODEL_PATH  = os.path.join(MODEL_DIR, "model_best.h5")
CONFIG_PATH = os.path.join(MODEL_DIR, "training_config.json")
ALLOWED_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

lstm_model = None
feature_extractor = None
preprocess_input = None
detector = None

BEST_THRESHOLD  = 0.59
GRAY_MARGIN     = 0.05
MAX_FRAMES      = 30      # panjang sekuens yang dipakai BiLSTM
PAD_LEN         = 30
FACE_INPUT_SZ   = 224
MIN_FACE_CONF   = 0.70
BBOX_EXPAND     = 0.05
MIN_FACE_SIZE   = 15

MAX_SCAN_FRAMES  = 60     # jumlah frame yang dipindai merata sepanjang video
MIN_FACE_FRAMES  = 5      # minimal frame berwajah agar analisis temporal bermakna
FEAT_BATCH_SIZE  = 8
UPSCALE_IF_SMALL = 720    # frame lebih sempit dari ini diperbesar sebelum deteksi

# Ruang warna crop wajah. HARUS SAMA dengan skrip ekstraksi fitur dataset.
#   Ubah lewat env bila perlu:  set FACE_COLOR=rgb
FACE_COLOR = os.getenv("FACE_COLOR", "bgr").lower()

# ─── PENANGAN GALAT ───
@app.errorhandler(413)
def berkas_terlalu_besar(e):
    return jsonify({
        "error": "BERKAS_TERLALU_BESAR",
        "message": "Ukuran video melebihi batas 200 MB."
    }), 413

# ─── AUTH ───
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            return redirect(url_for('home'))
        flash('Username atau Password salah!', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username sudah terdaftar!', 'warning')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── PROFILE ───
@app.route('/profile')
@login_required
def profile():
    scans = ScanHistory.query.filter_by(user_id=current_user.id).order_by(ScanHistory.timestamp.desc()).all()
    scan_count = len(scans)
    fake_count = sum(1 for s in scans if s.prediction == 'FAKE')
    real_count = scan_count - fake_count
    recent_scans = scans[:5]
    return render_template('profile.html',
        scan_count=scan_count,
        fake_count=fake_count,
        real_count=real_count,
        recent_scans=recent_scans
    )

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if current_user.password != current_pw:
        flash('Password saat ini tidak benar!', 'danger')
        return redirect(url_for('profile'))

    if len(new_pw) < 6:
        flash('Password baru minimal 6 karakter!', 'warning')
        return redirect(url_for('profile'))

    if new_pw != confirm_pw:
        flash('Konfirmasi password tidak cocok!', 'warning')
        return redirect(url_for('profile'))

    current_user.password = new_pw
    db.session.commit()
    flash('Password berhasil diperbarui!', 'success')
    return redirect(url_for('profile'))

# ─── AI FUNCTIONS ───
def build_backbone(name: str):
    name = name.lower().strip()
    if name == "b2":
        return EfficientNetB2(weights="imagenet", include_top=False, pooling="avg"), eff_pre, 260
    elif name == "resnet50":
        return ResNet50(weights="imagenet", include_top=False, pooling="avg"), res_pre, 224
    elif name == "xception":
        return Xception(weights="imagenet", include_top=False, pooling="avg"), xcep_pre, 299
    else:
        return EfficientNetB0(weights="imagenet", include_top=False, pooling="avg"), eff_pre, 224


def build_detector():
    """mtcnn 0.1.x menerima min_face_size; mtcnn 1.0.0 tidak.
    Cek signature dulu supaya tidak TypeError."""
    try:
        if "min_face_size" in inspect.signature(MTCNN.__init__).parameters:
            print(f"ℹ️  MTCNN lama — min_face_size={MIN_FACE_SIZE}")
            return MTCNN(min_face_size=MIN_FACE_SIZE)
    except (TypeError, ValueError):
        pass
    print("ℹ️  MTCNN baru — memakai parameter default")
    return MTCNN()


def load_all_models():
    global lstm_model, feature_extractor, preprocess_input, detector
    global BEST_THRESHOLD, PAD_LEN, FACE_INPUT_SZ
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model tidak ditemukan: {MODEL_PATH}")
        return
    lstm_model = load_model(MODEL_PATH, compile=False)
    feature_extractor, preprocess_input, FACE_INPUT_SZ = build_backbone(BACKBONE)
    detector = build_detector()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            BEST_THRESHOLD = float(cfg.get("best_threshold", BEST_THRESHOLD))
            PAD_LEN = int(cfg.get("pad_len", PAD_LEN))
    print(f"✅ Siap | backbone={BACKBONE} | threshold={BEST_THRESHOLD:.4f} | "
          f"pad_len={PAD_LEN} | face_color={FACE_COLOR.upper()}")


def _expand_and_clamp_bbox(x, y, w, h, W, H):
    cx, cy = x + w/2, y + h/2
    w2, h2 = w * (1 + BBOX_EXPAND), h * (1 + BBOX_EXPAND)
    x1, y1 = int(max(0, cx - w2/2)), int(max(0, cy - h2/2))
    x2, y2 = int(min(W, cx + w2/2)), int(min(H, cy + h2/2))
    return x1, y1, x2, y2


# ═══════════════════════════════════════════════════════════
# PENANGANAN ROTASI
# Video HP/WhatsApp menyimpan orientasi sebagai metadata, bukan
# dengan memutar piksel. Peramban menerapkannya, OpenCV sering
# tidak → MTCNN menerima frame miring dan gagal total.
# ═══════════════════════════════════════════════════════════
def _rotate(frame, rot):
    if rot == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rot == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rot == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


def _detect_faces(frame_bgr):
    """Deteksi wajah pada frame BGR. Frame sempit diperbesar dulu agar
    wajah kecil (25-30 px) tetap terjangkau, lalu bbox dikembalikan ke
    skala asli. MTCNN selalu menerima input RGB."""
    W = frame_bgr.shape[1]
    scale = 1.0
    work = frame_bgr
    if W < UPSCALE_IF_SMALL:
        scale = UPSCALE_IF_SMALL / W
        work = cv2.resize(frame_bgr, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    faces = detector.detect_faces(cv2.cvtColor(work, cv2.COLOR_BGR2RGB))
    faces = [f for f in faces if float(f.get("confidence", 0)) >= MIN_FACE_CONF]

    if scale != 1.0:
        for f in faces:
            f["box"] = [int(round(v / scale)) for v in f["box"]]
    return faces


def _resolve_orientation(cap):
    """Tentukan rotasi yang benar: baca metadata dulu, lalu verifikasi
    dengan mencoba deteksi wajah pada beberapa frame contoh."""
    try:
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    except Exception:
        pass

    try:
        meta_rot = int(cap.get(cv2.CAP_PROP_ORIENTATION_META) or 0) % 360
    except Exception:
        meta_rot = 0
    if meta_rot not in (0, 90, 180, 270):
        meta_rot = 0

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    probes = [int(total * p) for p in (0.15, 0.45, 0.75)] if total > 0 else [0, 5, 10]
    candidates = [meta_rot] + [r for r in (0, 90, 270, 180) if r != meta_rot]

    for rot in candidates:
        for idx in probes:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            if _detect_faces(_rotate(frame, rot)):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                if rot:
                    print(f"🔄 Frame diputar {rot}° agar wajah terdeteksi")
                return rot

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    return meta_rot


def process_video_for_prediction(video_path):
    """Mengembalikan (features, stats).
    features bernilai None HANYA jika tidak ada satu pun wajah terdeteksi.
    Kasus wajah terlalu sedikit diputuskan di predict()."""
    stats = {"frames_scanned": 0, "frames_with_face": 0, "rotation": 0}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, stats

    rot = _resolve_orientation(cap)
    stats["rotation"] = rot

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    idxs = (np.linspace(0, total - 1, min(MAX_SCAN_FRAMES, total), dtype=int)
            if total > 0 else np.arange(MAX_SCAN_FRAMES))

    crops = []
    for i in idxs:
        if len(crops) >= MAX_FRAMES:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if not ok:
            continue
        stats["frames_scanned"] += 1

        frame = _rotate(frame, rot)
        H, W = frame.shape[:2]          # dihitung SETELAH rotasi

        faces = _detect_faces(frame)
        if not faces:
            continue

        best = max(faces, key=lambda f: float(f.get("confidence", 0)))
        x, y, w, h = best["box"]
        x1, y1, x2, y2 = _expand_and_clamp_bbox(x, y, w, h, W, H)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        if FACE_COLOR == "rgb":
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        crops.append(cv2.resize(crop, (FACE_INPUT_SZ, FACE_INPUT_SZ)))
        stats["frames_with_face"] += 1

    cap.release()

    if not crops:
        return None, stats

    batch = preprocess_input(np.array(crops, dtype="float32"))
    feats = feature_extractor.predict(batch, batch_size=FEAT_BATCH_SIZE, verbose=0)
    seq = pad_sequences([feats], maxlen=PAD_LEN, dtype="float32", padding="post")
    return seq, stats


# ─── MAIN ROUTES ───
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/history")
@login_required
def history():
    if current_user.role == 'admin':
        scans = ScanHistory.query.order_by(ScanHistory.timestamp.desc()).all()
    else:
        scans = ScanHistory.query.filter_by(user_id=current_user.id).order_by(ScanHistory.timestamp.desc()).all()
    return render_template("history.html", scans=scans)

# ─── ADMIN ROUTES ───
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    total_scans = ScanHistory.query.count()
    total_fake = ScanHistory.query.filter_by(prediction='FAKE').count()
    total_real = ScanHistory.query.filter_by(prediction='REAL').count()
    total_users = User.query.count()
    fake_ratio = (total_fake / total_scans * 100) if total_scans > 0 else 0
    latest_activities = ScanHistory.query.order_by(ScanHistory.timestamp.desc()).limit(10).all()

    return render_template("admin_dashboard.html",
        total_scans=total_scans,
        total_fake=total_fake,
        total_real=total_real,
        total_users=total_users,
        fake_ratio=round(fake_ratio, 1),
        activities=latest_activities
    )

@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    users = User.query.order_by(User.id.asc()).all()
    for u in users:
        u.total_scans = ScanHistory.query.filter_by(user_id=u.id).count()
        u.fake_count  = ScanHistory.query.filter_by(user_id=u.id, prediction='FAKE').count()

    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/history")
@login_required
def admin_user_history(user_id):
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat mengakses halaman ini.', 'danger')
        return redirect(url_for('home'))

    target_user = User.query.get_or_404(user_id)
    scans = ScanHistory.query.filter_by(user_id=user_id) \
                             .order_by(ScanHistory.timestamp.desc()) \
                             .all()

    return render_template("admin_user_history.html",
        target_user=target_user,
        scans=scans
    )

# ─── ARSIP VIDEO ───
@app.route("/media/scan/<int:scan_id>")
@login_required
def scan_video(scan_id):
    """Melayani berkas video arsip untuk diputar di peramban.

    Gerbang akses: admin boleh membuka arsip milik siapa pun, sedangkan
    user biasa hanya boleh membuka arsip miliknya sendiri.
    """
    scan = ScanHistory.query.get_or_404(scan_id)

    if current_user.role != 'admin' and scan.user_id != current_user.id:
        abort(403)

    if not scan.stored_name:
        abort(404)

    folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(os.path.join(folder, scan.stored_name)):
        abort(404)

    # conditional=True mengaktifkan range request supaya video bisa di-seek.
    return send_from_directory(folder, scan.stored_name, conditional=True)


def bersihkan_arsip(hari=None):
    """Menghapus berkas video yang lebih tua dari batas retensi.

    Baris riwayat di basis data TIDAK dihapus; hanya berkas fisiknya yang
    dibuang dan kolom stored_name dikosongkan. Statistik dasbor tetap utuh.
    """
    hari = hari if hari is not None else RETENSI_HARI
    folder = app.config['UPLOAD_FOLDER']
    batas = datetime.now() - timedelta(days=hari)

    lama = ScanHistory.query.filter(
        ScanHistory.timestamp < batas,
        ScanHistory.stored_name.isnot(None)
    ).all()

    dihapus = 0
    for s in lama:
        path = os.path.join(folder, s.stored_name)
        if os.path.exists(path):
            try:
                os.remove(path)
                dihapus += 1
            except OSError:
                continue
        s.stored_name = None

    if lama:
        db.session.commit()
        print(f"[ARSIP] {dihapus} video lebih dari {hari} hari dihapus")
    return dihapus

# ─── PREDICT ───
@app.route("/predict", methods=["POST"])
@login_required
def predict():
    if lstm_model is None or detector is None:
        return jsonify({"error": "MODEL_BELUM_SIAP",
                        "message": "Model belum termuat di server."}), 503

    if "video" not in request.files:
        return jsonify({"error": "BERKAS_KOSONG",
                        "message": "Tidak ada berkas yang dikirim."}), 400

    f = request.files["video"]
    filename = secure_filename(f.filename)
    if not filename:
        return jsonify({"error": "NAMA_TIDAK_VALID",
                        "message": "Nama berkas tidak valid."}), 400

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        return jsonify({"error": "FORMAT_TIDAK_DIDUKUNG",
                        "message": f"Format {ext} tidak didukung. "
                                   f"Gunakan MP4, AVI, MOV, atau MKV."}), 400


    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Nama fisik dibuat acak agar dua user yang mengunggah berkas bernama
    # sama tidak saling menimpa. Nama asli tetap disimpan di kolom filename.
    stored_name = f"{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
    f.save(tmp_path)

    simpan_arsip = False   # baru bernilai True bila analisis berhasil

    try:
        feats, stats = process_video_for_prediction(tmp_path)
        scanned     = stats["frames_scanned"]
        face_frames = stats["frames_with_face"]

        # ★ GUARD A: benar-benar tidak ada wajah
        if feats is None:
            return jsonify({
                "error": "WAJAH_TIDAK_TERDETEKSI",
                "message": ("Tidak ada wajah manusia yang terdeteksi pada video ini. "
                            "Sistem hanya dapat menganalisis video yang menampilkan "
                            "wajah secara jelas."),
                "detail": {"frame_dipindai": scanned,
                           "frame_berwajah": 0,
                           "minimal_dibutuhkan": MIN_FACE_FRAMES}
            }), 422

        # ★ GUARD B: wajah ada tapi terlalu sedikit untuk analisis temporal
        if face_frames < MIN_FACE_FRAMES:
            return jsonify({
                "error": "WAJAH_TIDAK_MEMADAI",
                "message": (f"Wajah hanya terdeteksi pada {face_frames} dari "
                            f"{MIN_FACE_FRAMES} frame minimal yang dibutuhkan, sehingga "
                            f"video tidak dapat dianalisis secara andal. Gunakan video "
                            f"dengan wajah yang tampak jelas dan stabil."),
                "detail": {"frame_dipindai": scanned,
                           "frame_berwajah": face_frames,
                           "minimal_dibutuhkan": MIN_FACE_FRAMES}
            }), 422

        prob_fake = float(lstm_model.predict(feats, verbose=0)[0][0])
        label = "FAKE" if prob_fake > BEST_THRESHOLD else "REAL"
        confidence = prob_fake if label == "FAKE" else 1 - prob_fake
        status = ("HIGH_CONFIDENCE"
                  if abs(prob_fake - BEST_THRESHOLD) > GRAY_MARGIN
                  else "LOW_CONFIDENCE")
        coverage = (face_frames / scanned * 100) if scanned else 0.0


        new_scan = ScanHistory(
            user_id=current_user.id,
            filename=filename,
            stored_name=stored_name,
            prediction=label,
            confidence=confidence * 100,
            status=status,
            timestamp=datetime.now()
        )
        db.session.add(new_scan)
        db.session.commit()
        simpan_arsip = True   # riwayat tersimpan, berkas dipertahankan

        print(f"[SCAN] {filename} | rot={stats['rotation']}deg | "
              f"wajah {face_frames}/{scanned} | p_fake={prob_fake:.4f} | {label}")

        return jsonify({
            "prediksi": label,
            "skor_keyakinan": f"{confidence:.2%}",
            "prob_fake_raw": round(prob_fake, 4),
            "status": status,
            "frame_dipindai": scanned,
            "frame_berwajah": face_frames,
            "cakupan_wajah": f"{coverage:.1f}%",
            "rotasi": stats["rotation"],
            "ambang": round(BEST_THRESHOLD, 4)
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error /predict: {type(e).__name__}: {e}")
        return jsonify({"error": "GAGAL_PROSES",
                        "message": f"{type(e).__name__}: {e}"}), 500

    finally:
        # Video yang gagal dianalisis (tanpa wajah, error, format rusak)
        # tetap dibuang supaya tidak menumpuk tanpa riwayat pemiliknya.
        if not simpan_arsip and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ─── BOOTSTRAP ───
# Dipanggil di level modul agar tetap jalan lewat WSGI server
# (waitress/gunicorn), bukan hanya saat `python app.py`.

def bootstrap():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='123', role='admin'))
            db.session.commit()
            print("✅ Admin dibuat (admin/123)")
        print("✅ Database & tabel siap")
        bersihkan_arsip()   # retensi arsip video
    load_all_models()


bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
