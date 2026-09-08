from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Inisialisasi objek database
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Tabel untuk menyimpan data pengguna (Admin & User)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False) 
    role = db.Column(db.String(20), default='user') # Pembeda antara 'admin' atau 'user'
    
    # Relasi: Satu user bisa memiliki banyak riwayat scan
    scans = db.relationship('ScanHistory', backref='owner', lazy=True)

class ScanHistory(db.Model):
    """Tabel untuk menyimpan riwayat hasil deteksi deepfake"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    prediction = db.Column(db.String(20), nullable=False) # Hasil: REAL atau FAKE
    confidence = db.Column(db.Float, nullable=False)     # Skor keyakinan (%)
    status = db.Column(db.String(50))                    # HIGH/LOW CONFIDENCE
    stored_name = db.Column(db.String(150))              # Nama berkas fisik di server (arsip video)
    timestamp = db.Column(db.DateTime, default=datetime.now) # Waktu analisis
    
    # Foreign Key untuk menghubungkan ke User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)