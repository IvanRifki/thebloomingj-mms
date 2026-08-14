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
        # Paksa timpa password pakai method set_password() bawaan Model User
        user.set_password(password)
        print(f"Password '{username}' berhasil diperbarui ke 'tbjoktober'!")

    db.session.commit()
