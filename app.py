from datetime import date
from flask import Flask, redirect, render_template, request, url_for, jsonify, send_file, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import request, jsonify
import uuid
import os
from dotenv import load_dotenv
import io
import csv
import base64
import re

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'tiket.db'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'the-blooming-journey-secret-key-2026')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

WIB = ZoneInfo('Asia/Jakarta')


def wib_now():
    return datetime.now(WIB)


def format_wib(dt):
    if dt is None:
        return '-'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=WIB)
    else:
        dt = dt.astimezone(WIB)
    return dt.strftime('%d/%m/%Y %H:%M WIB')


@app.template_filter('wib')
def wib_filter(dt):
    return format_wib(dt)


def sanitize_input(text, max_length=100):
    if not text:
        return ''
    cleaned = re.sub(r'<[^>]+>', '', text)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)
    return cleaned.strip()[:max_length]


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login terlebih dahulu.'
login_manager.login_message_category = 'warning'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Tiket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(10), unique=True, nullable=False)
    nama = db.Column(db.String(100))
    no_telp = db.Column(db.String(20))
    email = db.Column(db.String(100))
    kode_referal = db.Column(db.String(50))
    jenis_tiket = db.Column(db.String(20))
    is_used = db.Column(db.Boolean, default=False)
    waktu_daftar = db.Column(db.DateTime, default=wib_now)
    waktu_scan = db.Column(db.DateTime, nullable=True)


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/daftar', methods=['GET', 'POST'])
def pendaftaran():
    if request.method == 'POST':
        nama = sanitize_input(request.form.get('nama'))
        no_telp = sanitize_input(request.form.get('telp'))
        email = sanitize_input(request.form.get('email'))
        kode_referal = sanitize_input(request.form.get('ref'))

        hari_ini = date.today()
        early_bird_mulai = date(2026, 7, 1)
        early_bird_selesai = date(2026, 8, 15)

        if early_bird_mulai <= hari_ini <= early_bird_selesai:
            jenis_tiket = 'early_bird'
        else:
            jenis_tiket = 'normal'

        kode = str(uuid.uuid4())[:8].upper()

        tiket_baru = Tiket(
            kode=kode,
            nama=nama,
            no_telp=no_telp,
            email=email,
            kode_referal=kode_referal,
            jenis_tiket=jenis_tiket,
            waktu_daftar=wib_now()
        )
        db.session.add(tiket_baru)
        db.session.commit()

        return render_template('sukses.html',
                               nama=nama,
                               kode=kode,
                               angkatan=jenis_tiket,
                               waktu_daftar=format_wib(wib_now())
                               )

    return render_template('daftar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin'))
        flash('Username atau password salah!', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Berhasil logout.', 'info')
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    tiket = Tiket.query.all()
    total = len(tiket)
    terpakai = sum(1 for t in tiket if t.is_used)
    sisa = total - terpakai
    kuota = 100

    return render_template('admin.html',
                           tiket=tiket,
                           total=total,
                           terpakai=terpakai,
                           sisa=sisa,
                           kuota=kuota
                           )


@app.route('/scan')
def scan():
    return render_template('scan.html', status=None)


@app.route('/scan/<kode_tiket>')
def scan_kode(kode_tiket):
    tiket = Tiket.query.filter_by(kode=kode_tiket).first()
    if not tiket:
        return render_template('scan.html', status='tidak ditemukan', kode=kode_tiket)
    if tiket.is_used:
        return render_template('scan.html', status='telah terpakai', kode=kode_tiket,
                               nama_peserta=tiket.nama, angkatan_peserta=tiket.jenis_tiket)
    else:
        tiket.is_used = True
        tiket.waktu_scan = wib_now()
        db.session.commit()
        return render_template('scan.html', status='berhasil', kode=kode_tiket,
                               nama_peserta=tiket.nama, angkatan_peserta=tiket.jenis_tiket)


if __name__ == '__main__':
    app.run(debug=True)
