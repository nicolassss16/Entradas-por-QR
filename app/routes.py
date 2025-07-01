from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, Event, Ticket, User
from . import login_manager
import qrcode
from io import BytesIO
import base64
from uuid import uuid4

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Públicas: index, registro, login/logout ---
@main.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('main.register'))
        if User.query.filter_by(username=username).first():
            flash('Este usuario ya está registrado.', 'error')
            return redirect(url_for('main.register'))
        hashed = generate_password_hash(password)
        user = User(username=username, password=hashed)
        db.session.add(user); db.session.commit()
        flash('✅ Registro exitoso. Ahora podés iniciar sesión.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']; p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            login_user(user)
            flash('Sesión iniciada', 'success')
            return redirect(url_for('main.index'))
        flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('main.index'))

# --- Compra de tickets ---
@main.route('/purchase', methods=['POST'])
def purchase_ticket():
    name = request.form['name']; event_id = request.form['event']; quantity = request.form['quantity']
    if not name or not event_id or not quantity:
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('main.index'))
    return redirect(url_for('main.checkout', name=name, event_id=event_id, quantity=quantity))

@main.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['name']; event_id = request.form['event_id']; quantity = request.form['quantity']
        event = Event.query.get(event_id)
        try:
            quantity = int(quantity)
            assert quantity > 0 and event
        except:
            flash('Datos inválidos.', 'error')
            return redirect(url_for('main.index'))
        return render_template('checkout.html', name=name, event=event, quantity=quantity)
    return redirect(url_for('main.index'))

@main.route('/pago_confirmado', methods=['POST'])
def pago_confirmado():
    name = request.form['name']
    event_id = request.form['event_id']
    quantity = int(request.form['quantity'])
    payment_method = request.form['payment_method']
    event = Event.query.get(event_id)
    if not event or quantity <= 0:
        flash('Error en la compra.', 'error')
        return redirect(url_for('main.index'))
    tx = str(uuid4())
    for _ in range(quantity):
        code = str(uuid4())
        img = qrcode.make(code)
        buf = BytesIO(); img.save(buf, format="PNG")
        qr = base64.b64encode(buf.getvalue()).decode()
        ticket = Ticket(name=name, event_id=event.id, quantity=1,
                        qr_code=qr, ticket_code=code, transaction_id=tx,
                        payment_method=payment_method,
                        user_id=current_user.id if current_user.is_authenticated else None)
        db.session.add(ticket)
    db.session.commit()
    flash(f'Pago éxitoso por {payment_method}', 'success')
    return redirect(url_for('main.confirmacion_compra', transaction_id=tx))

@main.route('/confirmacion_compra/<string:transaction_id>')
def confirmacion_compra(transaction_id):
    tickets = Ticket.query.filter_by(transaction_id=transaction_id).all()
    if not tickets:
        flash('No se encontraron tickets.', 'error')
        return redirect(url_for('main.index'))
    return render_template('ticket_multiple.html', tickets=tickets)

@main.route('/ticket/<ticket_code>')
def ticket(ticket_code):
    t = Ticket.query.filter_by(ticket_code=ticket_code).first_or_404()
    return render_template('ticket.html', ticket=t)

# API verificación QR
@main.route('/verificar')
def verificar_qr():
    return render_template('verificar.html')

@main.route('/api/verificar_ticket', methods=['POST'])
def api_verificar_ticket():
    qr = request.get_json().get('ticket_id')
    t = Ticket.query.filter_by(ticket_code=qr).first()
    if not t:
        return jsonify({'status':'error','message':'❌ Ticket no encontrado'})
    info = {'ticket_code':t.ticket_code,'buyer_name':t.name,'event_name':t.event.name,'usado':t.usado}
    if t.usado:
        return jsonify({'status':'warning','message':'⚠️ Ticket ya fue usado','ticket_info':info})
    t.usado = True
    db.session.commit()
    return jsonify({'status':'ok','message':f'✅ Bienvenido {t.name}','ticket_info':info})

# --- Administración ---
@main.route('/admin')
@login_required
def admin():
    events = Event.query.all()
    tickets = Ticket.query.order_by(Ticket.id.desc()).all()
    return render_template('admin.html', events=events, tickets=tickets)

@main.route('/admin/add_event', methods=['POST'])
@login_required
def add_event():
    name = request.form['name']
    if name:
        e = Event(name=name); db.session.add(e); db.session.commit()
        flash('Evento agregado', 'success')
    else:
        flash('Nombre requerido', 'error')
    return redirect(url_for('main.admin'))

