from app import app, db, User

with app.app_context():
    username = 'seminar'
    password = 'tbjoktober'

    existing = User.query.filter_by(username=username).first()
    if not existing:
        u = User(username=username)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print('Admin berhasil dibuat!')
    else:
        print('Admin sudah ada.')
