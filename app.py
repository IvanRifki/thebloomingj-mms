from datetime import date
from flask import Flask, Response, redirect, render_template, request, url_for, jsonify, send_file, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import request, jsonify
import uuid
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import io
import csv
import base64
import qrcode
import re

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

db_url = os.environ.get(
    'DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'tiket.db'))
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'the-blooming-journey-secret-key-2026')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"[WARNING] db.create_all() gagal: {e}")


supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

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
    jenis_tiket = db.Column(db.String(50))
    jumlah_peserta = db.Column(db.Integer, default=1)
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

# kuotanya


def get_kuota():
    setting = Setting.query.filter_by(key='kuota').first()
    return int(setting.value) if setting else 320


def set_kuota(kuota_baru):
    setting = Setting.query.filter_by(key='kuota').first()

    if setting:
        setting.value = str(kuota_baru)
    else:
        setting = Setting(
            key='kuota',
            value=str(kuota_baru)
        )
        db.session.add(setting)

    db.session.commit()


def get_limit_early_bird():
    setting = Setting.query.filter_by(key='limit_early_bird').first()
    return int(setting.value) if setting else 100


def get_limit_normal():
    setting = Setting.query.filter_by(key='limit_normal').first()
    return int(setting.value) if setting else 220


def generate_qr_base64(data):
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/daftar', methods=['GET', 'POST'])
def pendaftaran():

    kuota = get_kuota()

    total_terdaftar = db.session.query(
        db.func.sum(Tiket.jumlah_peserta)
    ).scalar() or 0

    if total_terdaftar >= kuota:
        return redirect('/habis')

    limit_early_bird = get_limit_early_bird()

    tiket_eb = Tiket.query.filter(
        Tiket.jenis_tiket.in_([
            'single_eb',
            'circle_eb',
            'squad_eb'
        ])
    ).all()

    total_early_bird = sum(
        t.jumlah_peserta for t in tiket_eb
    )

    if total_early_bird >= limit_early_bird:
        return redirect('/normal_daftar')

    if request.method == 'POST':

        total_terdaftar = db.session.query(
            db.func.sum(Tiket.jumlah_peserta)
        ).scalar() or 0

        if total_terdaftar >= kuota:
            return redirect('/habis')

        nama = sanitize_input(request.form.get('nama'))
        no_telp = sanitize_input(request.form.get('telp'))
        email = sanitize_input(request.form.get('email'))
        kode_referal = sanitize_input(request.form.get('ref'))

        if not nama:
            flash('Nama wajib diisi!', 'danger')
            return redirect('/daftar')

        jenis_tiket = request.form.get('paket_tiket')

        map_peserta = {
            'single_eb': 1,
            'circle_eb': 3,
            'squad_eb': 5
        }

        peserta_baru = map_peserta.get(jenis_tiket, 1)

        if total_terdaftar + peserta_baru > kuota:
            return redirect('/habis')

        if jenis_tiket in [
            'single_eb',
            'circle_eb',
            'squad_eb'
        ]:

            tiket_eb = Tiket.query.filter(
                Tiket.jenis_tiket.in_([
                    'single_eb',
                    'circle_eb',
                    'squad_eb'
                ])
            ).all()

            total_early_bird = sum(
                t.jumlah_peserta for t in tiket_eb
            )

            if total_early_bird + peserta_baru > limit_early_bird:
                flash(
                    'Mohon maaf, kuota khusus Early Bird sudah penuh! '
                    'Harga tiket kembali normal. Silahkan mengisi form kembali. '
                    'Gunakan kode referal untuk mendapatkan potongan harga (opsional).',
                    'eb-penuh'
                )
                return redirect('/normal_daftar?status=eb_penuh')

        kode = "MMS-" + str(uuid.uuid4()).upper()[:4]

        tiket_baru = Tiket(
            kode=kode,
            nama=nama,
            no_telp=no_telp,
            email=email,
            kode_referal=kode_referal,
            jenis_tiket=jenis_tiket,
            jumlah_peserta=peserta_baru,
            waktu_daftar=wib_now()
        )

        db.session.add(tiket_baru)
        db.session.commit()

        qr_base64 = generate_qr_base64(kode)

        return render_template(
            'sukses.html',
            nama=nama,
            kode=kode,
            angkatan=jenis_tiket,
            qr_base64=qr_base64,
            waktu_daftar=format_wib(wib_now())
        )

    return render_template(
        'daftar.html',
        tiket_terjual=total_early_bird
    )


@app.route('/normal_daftar', methods=['GET', 'POST'])
def pendaftaran_normal():

    KODE_REFERAL_VALID = [
        'MMS2026',
        'SAHABATMMS',
        'BLOOMING01'
    ]

    kuota = get_kuota()

    total_terdaftar = db.session.query(
        db.func.sum(Tiket.jumlah_peserta)
    ).scalar() or 0

    if total_terdaftar >= kuota:
        return redirect('/habis')

    limit_normal = get_limit_normal()

    tiket_normal = Tiket.query.filter_by(
        jenis_tiket='normal'
    ).all()

    total_normal = sum(
        t.jumlah_peserta for t in tiket_normal
    )

    if total_normal >= limit_normal:
        return redirect('/habis')

    if request.method == 'POST':

        total_terdaftar = db.session.query(
            db.func.sum(Tiket.jumlah_peserta)
        ).scalar() or 0

        if total_terdaftar >= kuota:
            return redirect('/habis')

        nama = sanitize_input(request.form.get('nama'))
        no_telp = sanitize_input(request.form.get('telp'))
        email = sanitize_input(request.form.get('email'))
        kode_referal = sanitize_input(request.form.get('ref'))

        if not nama:
            flash('Nama wajib diisi!', 'danger')
            return redirect('/normal_daftar')

        jenis_tiket = 'normal'
        peserta_baru = 1

        if total_terdaftar + peserta_baru > kuota:
            return redirect('/habis')

        tiket_normal = Tiket.query.filter_by(
            jenis_tiket='normal'
        ).all()

        total_normal = sum(
            t.jumlah_peserta for t in tiket_normal
        )

        if total_normal + peserta_baru > limit_normal:
            return redirect('/habis')

        kode_ref_upper = (kode_referal or '').strip().upper()

        if kode_ref_upper in KODE_REFERAL_VALID:
            harga_final = 388000
            kode_referal_final = kode_ref_upper
        else:
            harga_final = 389000
            kode_referal_final = kode_referal or None

        kode = "MMS-" + str(uuid.uuid4()).upper()[:4]

        tiket_baru = Tiket(
            kode=kode,
            nama=nama,
            no_telp=no_telp,
            email=email,
            kode_referal=kode_referal_final,
            jenis_tiket='normal',
            jumlah_peserta=1,
            waktu_daftar=wib_now()
        )

        db.session.add(tiket_baru)
        db.session.commit()

        return redirect(
            url_for(
                'sukses',
                kode=kode
            )
        )

    return render_template('normal_daftar.html')


@app.route('/sukses')
def sukses():
    kode = request.args.get('kode')

    if not kode:
        flash('Data pendaftaran tidak ditemukan.', 'danger')
        return redirect('/normal_daftar')

    tiket = Tiket.query.filter_by(kode=kode).first()

    if not tiket:
        flash('Data tiket tidak ditemukan.', 'danger')
        return redirect('/normal_daftar')

    qr_base64 = generate_qr_base64(kode)

    return render_template(
        'sukses.html',
        nama=tiket.nama,
        kode=tiket.kode,
        angkatan=tiket.jenis_tiket,
        qr_base64=qr_base64,
        waktu_daftar=format_wib(tiket.waktu_daftar)
    )


@app.route('/hapus_tiket/<int:tiket_id>', methods=['POST'])
def hapus_tiket(tiket_id):
    tiket = Tiket.query.get(tiket_id)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not tiket:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Data tidak ditemukan'}), 404
        flash('Data tidak ditemukan', 'danger')
        return redirect('/admin')

    db.session.delete(tiket)
    db.session.commit()

    if is_ajax:
        return jsonify({'success': True})

    flash('Data berhasil dihapus', 'success')
    return redirect('/admin')


@app.route('/hapus_semua_peserta', methods=['POST'])
def hapus_semua_peserta():
    Tiket.query.delete()
    db.session.commit()
    flash('Semua data peserta berhasil dihapus', 'success')
    return redirect('/admin')


@app.route('/reset_semua', methods=['POST'])
def reset_semua():
    Tiket.query.update({
        Tiket.is_used: False})
    db.session.commit()
    flash('Semua status kehadiran berhasil direset menjadi Belum Hadir.', 'success')
    return redirect('/admin')


@app.route('/export/csv')
def export_csv():

    tiket = Tiket.query.order_by(Tiket.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'No',
        'Kode Tiket',
        'Nama Lengkap',
        'No Telp',
        'Email',
        'Kode Referal',
        'Jenis Tiket',
        'Jumlah Peserta',
        'Status',
        'Waktu Daftar',
        'Waktu Scan'
    ])

    # Data
    for no, t in enumerate(tiket, start=1):

        writer.writerow([
            no,
            t.kode or '-',
            t.nama or '-',
            t.no_telp or '-',
            t.email or '-',
            t.kode_referal or '-',
            t.jenis_tiket or '-',
            t.jumlah_peserta or 0,
            'Hadir' if t.is_used else 'Belum Hadir',
            format_wib(t.waktu_daftar) if t.waktu_daftar else '-',
            format_wib(t.waktu_scan) if t.waktu_scan else '-'
        ])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition':
                'attachment; filename=data_peserta_mms.csv'
        }
    )


@app.route('/admin/kuota', methods=['POST'])
def admin_kuota():
    try:
        kuota_baru = int(request.form.get('kuota', 0))

        if kuota_baru < 1:
            flash('Kuota minimal 1.', 'danger')
            return redirect(url_for('admin'))

        set_kuota(kuota_baru)

        flash(f'Kuota berhasil diubah menjadi {kuota_baru}.', 'success')

    except (ValueError, TypeError):
        flash('Nilai kuota tidak valid.', 'danger')

    return redirect(url_for('admin.html'))


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
    try:
        tiket = Tiket.query.all()
        total = len(tiket)
        terpakai = sum(1 for t in tiket if t.is_used)
        sisa = total - terpakai
        kuota = get_kuota()

        return render_template('admin.html',
                               tiket=tiket,
                               total=total,
                               terpakai=terpakai,
                               sisa=sisa,
                               kuota=kuota
                               )
    except Exception as e:
        # SEMENTARA buat debug, hapus lagi kalau udah ketemu akar masalahnya
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>", 500


@app.route('/habis')
def habis():
    kuota = get_kuota()

    total_terdaftar = db.session.query(
        db.func.sum(Tiket.jumlah_peserta)
    ).scalar() or 0

    return render_template(
        'habis.html',
        kuota=kuota,
        total=total_terdaftar
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
