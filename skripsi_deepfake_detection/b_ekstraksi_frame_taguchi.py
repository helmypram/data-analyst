# Ekstrasi_frame_single.py
# ------------------------------------------------------------
# Ekstraksi fitur wajah (single-process, internal batching)
# Pipeline:
#   MTCNN (deteksi wajah) -> Backbone CNN (ekstraksi fitur) -> simpan (T, D) ke .npy
# Backbone dipilih via ENV BACKBONE=b0|b1|b2|b3|resnet50|resnet101|xception|inceptionresnetv2
# Optimasi:
#   - Satu proses saja (GPU tunggal lebih stabil)
#   - Batching internal untuk inference CNN (lebih cepat)
# ------------------------------------------------------------

import os
import cv2
import numpy as np
from typing import List, Tuple, Dict
import traceback
import time
import tensorflow as tf

# =============== Import model Keras & detektor ===============
from mtcnn.mtcnn import MTCNN
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications import (
    EfficientNetB0, EfficientNetB1, EfficientNetB2, EfficientNetB3,
    ResNet50, ResNet101, Xception, InceptionResNetV2
)
from tensorflow.keras.applications.efficientnet import preprocess_input as eff_pre
from tensorflow.keras.applications.resnet import preprocess_input as res_pre
from tensorflow.keras.applications.xception import preprocess_input as xcep_pre
from tensorflow.keras.applications.inception_resnet_v2 import preprocess_input as incep_res_pre

# =============== Konfigurasi (ENV override) ===============
TOP_K_FACES   = int(os.getenv("TOP_K_FACES", 2))        # jumlah wajah per frame yang diambil
MIN_FACE_CONF = float(os.getenv("MIN_FACE_CONF", 0.0))  # filter wajah dengan confidence rendah
BBOX_EXPAND   = float(os.getenv("BBOX_EXPAND", 0.10))   # 10% pelebaran bbox
MIN_FACE_SIZE = int(os.getenv("MIN_FACE_SIZE", 20))     # ukuran minimum sisi bbox (px)
MAX_FRAMES_DF = int(os.getenv("MAX_FRAMES", 30))        # batas frame per video (yang punya wajah)
BATCH_SIZE    = int(os.getenv("BATCH_SIZE", 64))        # ukuran batch untuk CNN
USE_PILOT     = os.getenv("USE_PILOT", "0") == "1"      # jika 1 -> subset video
PILOT_RATIO   = float(os.getenv("PILOT_RATIO", 0.10))   # proporsi subset (0.10 = 10%)

ALLOWED_EXTS  = (".mp4", ".avi", ".mov", ".mkv")

# =============== Global singleton ===============
feature_extractor = None
detector = None
preprocess_input = None
FACE_INPUT_SZ = None  # dari backbone
FEAT_DIM = None       # dimensi fitur keluar backbone

# =============== Backbone factory ===============
def make_backbone():
    """
    Pilih backbone via ENV BACKBONE
    b0|b1|b2|b3|resnet50|resnet101|xception|inceptionresnetv2
    Return: (model, preprocess_func, input_size)
    """
    name = os.getenv("BACKBONE", "b0").strip().lower()
    if name == "b1":
        model = EfficientNetB1(weights="imagenet", include_top=False, pooling="avg")
        return model, eff_pre, 240, name
    elif name == "b2":
        model = EfficientNetB2(weights="imagenet", include_top=False, pooling="avg")
        return model, eff_pre, 260, name
    elif name == "b3":
        model = EfficientNetB3(weights="imagenet", include_top=False, pooling="avg")
        return model, eff_pre, 300, name
    elif name == "resnet50":
        model = ResNet50(weights="imagenet", include_top=False, pooling="avg")
        return model, res_pre, 224, name
    elif name == "resnet101":
        model = ResNet101(weights="imagenet", include_top=False, pooling="avg")
        return model, res_pre, 224, name
    elif name == "xception":
        model = Xception(weights="imagenet", include_top=False, pooling="avg")
        return model, xcep_pre, 299, name
    elif name in ["inceptionresnetv2", "inception-resnet-v2"]:
        model = InceptionResNetV2(weights="imagenet", include_top=False, pooling="avg")
        return model, incep_res_pre, 299, "inceptionresnetv2"
    else:
        # default b0
        model = EfficientNetB0(weights="imagenet", include_top=False, pooling="avg")
        return model, eff_pre, 224, "b0"

def initialize_model_and_detector():
    """Inisialisasi backbone & MTCNN (lazy singleton)."""
    global feature_extractor, detector, preprocess_input, FACE_INPUT_SZ, FEAT_DIM, backbone_name
    if feature_extractor is None or preprocess_input is None or FACE_INPUT_SZ is None:
        feature_extractor, preprocess_input, FACE_INPUT_SZ, backbone_name = make_backbone()
        # Tentukan dimensi fitur sekali (dummy forward 1 crop hitam)
        dummy = np.zeros((1, FACE_INPUT_SZ, FACE_INPUT_SZ, 3), dtype=np.float32)
        dummy = preprocess_input(dummy)
        out = feature_extractor.predict(dummy, verbose=0)
        FEAT_DIM = int(out.shape[-1])
    if detector is None:
        detector = MTCNN()

# =============== Utils bbox ===============
def _expand_and_clamp_bbox(x: int, y: int, w: int, h: int, W: int, H: int) -> Tuple[int, int, int, int]:
    """Perlebar bbox dan clamp ke dalam frame."""
    cx = x + w / 2.0
    cy = y + h / 2.0
    w2 = w * (1.0 + BBOX_EXPAND)
    h2 = h * (1.0 + BBOX_EXPAND)
    x1 = int(max(0, np.floor(cx - w2 / 2.0)))
    y1 = int(max(0, np.floor(cy - h2 / 2.0)))
    x2 = int(min(W, np.ceil(cx + w2 / 2.0)))
    y2 = int(min(H, np.ceil(cy + h2 / 2.0)))
    return x1, y1, x2, y2

# =============== Ekstraksi satu video (dengan batching) ===============
def extract_features_from_video(video_path: str, save_path: str, max_frames: int = None):
    try:
        initialize_model_and_detector()
        if max_frames is None:
            max_frames = MAX_FRAMES_DF

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[FAIL] Tidak bisa buka video: {os.path.basename(video_path)}")
            return

        batch_imgs: List[np.ndarray] = []
        batch_fidx: List[int] = []
        feats_by_frame: Dict[int, List[np.ndarray]] = {}

        processed_frames = 0
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            if processed_frames >= max_frames:
                break

            H, W = frame.shape[:2]
            if H == 0 or W == 0:
                frame_idx += 1
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                faces = detector.detect_faces(frame_rgb)
            except Exception:
                faces = []

            if not faces:
                frame_idx += 1
                continue

            faces = [f for f in faces if f.get("confidence", 0.0) >= MIN_FACE_CONF]
            if not faces:
                frame_idx += 1
                continue
            faces = sorted(faces, key=lambda f: f.get("confidence", 0.0), reverse=True)[:TOP_K_FACES]

            for f in faces:
                x, y, w, h = f.get("box", [0, 0, 0, 0])
                x1, y1, x2, y2 = _expand_and_clamp_bbox(int(x), int(y), int(w), int(h), W, H)
                if x2 <= x1 or y2 <= y1:
                    continue
                if (x2 - x1) < MIN_FACE_SIZE or (y2 - y1) < MIN_FACE_SIZE:
                    continue
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                im = cv2.resize(crop, (FACE_INPUT_SZ, FACE_INPUT_SZ))
                arr = img_to_array(im)
                batch_imgs.append(arr)
                batch_fidx.append(frame_idx)

                if len(batch_imgs) >= BATCH_SIZE:
                    _flush_batch_to_feats(batch_imgs, batch_fidx, feats_by_frame)
                    batch_imgs.clear()
                    batch_fidx.clear()

            processed_frames += 1
            frame_idx += 1

        if len(batch_imgs) > 0:
            _flush_batch_to_feats(batch_imgs, batch_fidx, feats_by_frame)
            batch_imgs.clear()
            batch_fidx.clear()

        cap.release()

        if not feats_by_frame:
            print(f"[WARN] No faces -> {os.path.basename(video_path)}")
            return

        frame_indices_sorted = sorted(feats_by_frame.keys())
        seq_feats = []
        for fi in frame_indices_sorted:
            vecs = feats_by_frame.get(fi, [])
            if not vecs:
                continue
            cat = np.concatenate(vecs, axis=0)
            mean_vec = np.mean(cat, axis=0, keepdims=True).astype(np.float32)
            seq_feats.append(mean_vec)
            if len(seq_feats) >= max_frames:
                break

        if not seq_feats:
            print(f"[WARN] No features -> {os.path.basename(video_path)}")
            return

        feats = np.concatenate(seq_feats, axis=0).astype(np.float32)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        np.save(save_path, feats)
        print(f"[OK] {os.path.basename(save_path)} | T={feats.shape[0]} | D={feats.shape[1]}")

    except Exception as e:
        print(f"[FAIL] {os.path.basename(video_path)}: {e}")
        traceback.print_exc()

def _flush_batch_to_feats(batch_imgs: List[np.ndarray], batch_fidx: List[int], feats_by_frame: Dict[int, List[np.ndarray]]):
    global feature_extractor, preprocess_input
    X = np.stack(batch_imgs, axis=0).astype(np.float32)
    X = preprocess_input(X)
    feats = feature_extractor.predict(X, verbose=0)
    for vec, fi in zip(feats, batch_fidx):
        vec2 = vec.reshape(1, -1).astype(np.float32)
        if fi not in feats_by_frame:
            feats_by_frame[fi] = [vec2]
        else:
            feats_by_frame[fi].append(vec2)

# =============== Batch runner ===============
def main():
    base_dir   = os.getenv("BASE_DIR", r"D:\Semester 6\celeb-v2")
    out_root   = os.getenv("OUT_ROOT", "new_output_features_mtcnn_v7_single_3")

    initialize_model_and_detector()
    output_dir = os.path.join(base_dir, f"{out_root}_{backbone_name}")

    folders    = os.getenv("FOLDERS", "video_real,video_synthesis,youtube-real").split(",")

    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(e)

    print("====================================================")
    print(f"Backbone name   : {backbone_name}")
    print(f"Backbone aktif  : {type(feature_extractor).__name__}")
    print(f"Input size      : {FACE_INPUT_SZ}")
    print(f"Feat dim (D)    : {FEAT_DIM}")
    print(f"Output dir      : {output_dir}")
    print(f"TOP_K_FACES     : {TOP_K_FACES}")
    print(f"MAX_FRAMES      : {MAX_FRAMES_DF}")
    print(f"BATCH_SIZE      : {BATCH_SIZE}")
    print(f"USE_PILOT       : {USE_PILOT} (ratio={PILOT_RATIO})")
    print("====================================================")

    os.makedirs(output_dir, exist_ok=True)

    tasks = []
    for folder in folders:
        folder = folder.strip()
        if not folder:
            continue
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            print(f"[WARN] Directory not found: {folder_path}")
            continue

        save_subdir = os.path.join(output_dir, folder)
        os.makedirs(save_subdir, exist_ok=True)

        all_files = [fn for fn in os.listdir(folder_path) if fn.lower().endswith(ALLOWED_EXTS)]
        all_files.sort()

        if USE_PILOT and len(all_files) > 0:
            n_keep = max(1, int(len(all_files) * PILOT_RATIO))
            sel = all_files[:n_keep]
            print(f"[PILOT] {folder}: {n_keep}/{len(all_files)} files")
        else:
            sel = all_files

        for video_file in sel:
            in_fp  = os.path.join(folder_path, video_file)
            out_fp = os.path.join(save_subdir, os.path.splitext(video_file)[0] + ".npy")
            tasks.append((in_fp, out_fp))

    print(f"Total video: {len(tasks)}")

    t0 = time.time()
    done, fail = 0, 0
    for i, (video_path, save_path) in enumerate(tasks, start=1):
        print(f"[{i}/{len(tasks)}] {os.path.basename(video_path)}")
        try:
            extract_features_from_video(video_path, save_path, max_frames=MAX_FRAMES_DF)
            done += 1
        except Exception as e:
            print(f"[ERR] {os.path.basename(video_path)}: {e}")
            fail += 1
    dt = time.time() - t0

    print("====================================================")
    print(f"Selesai. OK={done} | FAIL={fail} | Waktu={dt/3600:.2f} jam")
    print("Output dir:", output_dir)
    print("====================================================")

# Entrypoint
if __name__ == "__main__":
    main()
