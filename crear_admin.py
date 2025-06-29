from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def crear_admin():
    username = 'admin'
    password = 'admin123'

    if User.query.filter_by(username=username).first():
        print("⚠️ El usuario admin ya existe.")
        return

    hashed_password = generate_password_hash(password)
    admin_user = User(username=username, password=hashed_password)
    db.session.add(admin_user)
    db.session.commit()
    print(f"✅ Usuario '{username}' creado con contraseña '{password}'")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        crear_admin()
