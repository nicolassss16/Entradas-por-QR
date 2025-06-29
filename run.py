from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
import os

app = create_app()

def crear_admin():
    username = 'admin'
    password = 'admin123'  # ⚠️ Cambialo para producción

    if User.query.filter_by(username=username).first():
        print("✅ El usuario admin ya existe.")
        return

    hashed_password = generate_password_hash(password)
    admin_user = User(username=username, password=hashed_password)
    db.session.add(admin_user)
    db.session.commit()
    print(f"✅ Usuario '{username}' creado con contraseña '{password}'")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    with app.app_context():
        crear_admin()

    app.run(host='0.0.0.0', port=port)
