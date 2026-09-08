# balance_data_full.py
# ------------------------------------------------------------
# Menyeimbangkan dataset FULL dari folder:
#   new_output_features_mtcnn_v7_single_3_<BACKBONE>/
#     {video_real, video_synthesis, youtube-real, instagram-real, ...}/*.npy
# Output:
#   X_balanced_<BACKBONE>.npy, y_balanced_<BACKBONE>.npy
# ------------------------------------------------------------

import os
import glob
import numpy as np
from tqdm import tqdm
from tensorflow.keras.preprocessing.sequence import pad_sequences

# ====== Konfigurasi via ENV ======
BASE_DIR    = os.getenv("BASE_DIR",  r"D:\Semester 6\celeb-v2")
BACKBONE    = os.getenv("BACKBONE",  "xception").lower()     # b0|b2|resnet50|xception
MAX_FRAMES  = int(os.getenv("MAX_FRAMES", "30"))
INPUT_TAG   = os.getenv("INPUT_TAG", "new_output_features_mtcnn_v7_single_3")  # prefix folder input
SAVE_TAG    = os.getenv("SAVE_TAG",  "new_final_dataset_mtcnn_v7_single_3")    # folder output balanced
# Folder sumber (bisa tambah/kurangi; dipisahkan koma)
FOLDERS_REAL = os.getenv(
    "FOLDERS_REAL",
    "video_real,youtube-real"
).split(",")
FOLDERS_FAKE = os.getenv(
    "FOLDERS_FAKE",
    "video_synthesis"
).split(",")

# ====== Path ======
IN_DIR   = os.path.join(BASE_DIR, f"{INPUT_TAG}_{BACKBONE}")
SAVE_DIR = os.path.join(BASE_DIR, SAVE_TAG)
os.makedirs(SAVE_DIR, exist_ok=True)

print("====================================================")
print("Balance DATA (FULL MODE)")
print(f"Backbone       : {BACKBONE}")
print(f"Input dir      : {IN_DIR}")
print(f"Save dir       : {SAVE_DIR}")
print(f"MAX_FRAMES     : {MAX_FRAMES}")
print(f"REAL folders   : {FOLDERS_REAL}")
print(f"FAKE folders   : {FOLDERS_FAKE}")
print("====================================================")

def collect_files(root, subfolders):
    files = []
    for fld in subfolders:
        p = os.path.join(root, fld.strip())
        files += glob.glob(os.path.join(p, "*.npy"))
    return files

# ---- Kumpulkan file .npy ----
real_files = collect_files(IN_DIR, FOLDERS_REAL)
fake_files = collect_files(IN_DIR, FOLDERS_FAKE)

print(f"Ditemukan {len(real_files)} file REAL.")
print(f"Ditemukan {len(fake_files)} file FAKE.")
if len(real_files) == 0 or len(fake_files) == 0:
    raise RuntimeError("Folder FULL kosong atau struktur tidak sesuai. Cek nama folder input_tag & subfolder.")

# ---- Validasi file ----
valid_real, valid_fake = [], []
for fp in tqdm(real_files, desc="Validating REAL"):
    try:
        arr = np.load(fp, allow_pickle=False)
        if arr.ndim == 2 and arr.shape[0] > 0:
            valid_real.append(fp)
    except Exception as e:
        print(f"[BAD REAL] {fp} -> {e}")

for fp in tqdm(fake_files, desc="Validating FAKE"):
    try:
        arr = np.load(fp, allow_pickle=False)
        if arr.ndim == 2 and arr.shape[0] > 0:
            valid_fake.append(fp)
    except Exception as e:
        print(f"[BAD FAKE] {fp} -> {e}")

print(f"Valid REAL: {len(valid_real)} | Valid FAKE: {len(valid_fake)}")
if len(valid_real) == 0 or len(valid_fake) == 0:
    raise RuntimeError("Tidak ada file valid setelah validasi.")

# ---- Seimbangkan (undersample mayoritas) ----
np.random.seed(42)
n_real, n_fake = len(valid_real), len(valid_fake)
if n_fake > n_real:
    sampled_fake = list(np.random.choice(valid_fake, size=n_real, replace=False))
    sampled_real = valid_real
else:
    sampled_real = list(np.random.choice(valid_real, size=n_fake, replace=False))
    sampled_fake = valid_fake

print(f"Set seimbang -> REAL: {len(sampled_real)} | FAKE: {len(sampled_fake)}")

# ---- Shuffle gabungan ----
all_files = sampled_real + sampled_fake
labels = [0] * len(sampled_real) + [1] * len(sampled_fake) #label 0 real 1 fake
perm = np.random.permutation(len(all_files))
all_files = [all_files[i] for i in perm]
labels   = [labels[i] for i in perm]

# ---- Load & padding ----
X_list, y_list = [], []
for fp, y in tqdm(list(zip(all_files, labels)), total=len(all_files), desc="Loading features"):
    try:
        X_list.append(np.load(fp, allow_pickle=False))   # (T, D)
        y_list.append(y)
    except Exception as e:
        print(f"[LOAD FAIL] {fp} -> {e}")

X_padded = pad_sequences(X_list, maxlen=MAX_FRAMES, dtype="float32", padding="post", truncating="post")
y_arr    = np.array(y_list, dtype=np.int64)

print("\n--- Ringkasan ---")
print("X shape   :", X_padded.shape)   # (N, T, D)
print("y shape   :", y_arr.shape)
print("REAL/FAKE :", int(np.sum(y_arr==0)), "/", int(np.sum(y_arr==1)))
print("Dimensi D :", X_padded.shape[2])

# ---- Simpan ----
x_path = os.path.join(SAVE_DIR, f"X_balanced_{BACKBONE}.npy")
y_path = os.path.join(SAVE_DIR, f"y_balanced_{BACKBONE}.npy")
np.save(x_path, X_padded)
np.save(y_path, y_arr)

print(f"\n✅ Disimpan:")
print(f"   {x_path}")
print(f"   {y_path}")
