from app import app, db, User

with app.app_context():
    username = 'seminar'
    password = 'tbjoktober'

    user = User.query.filter_by(username=username).first()

    if not user:

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        print(f"User '{username}' berhasil dibuat!")
    else:

        user.set_password(password)
        print(f"Password untuk '{username}' berhasil diperbarui!")

    db.session.commit()

    cek_user = User.query.filter_by(username=username).first()
    print("=== STATUS USER ===")
    print(f"Username: {cek_user.username}")
    print(f"Password Hash di DB: {cek_user.password_hash}")
    print(f"Tes Login 'tbjoktober': {cek_user.check_password('tbjoktober')}")
