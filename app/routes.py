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

# --------------------------
# Rutas públicas y usuario
# --------------------------

@main.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Sesión iniciada correctamente', 'success')
            return redirect(url_for('main.admin'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('main.index'))

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

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('✅ Registro exitoso. Ahora podés iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

# --------------------------
# Compra de tickets
# --------------------------

@main.route('/purchase', methods=['POST'])
def purchase_ticket():
    name = request.form['name']
    event_id = request.form['event']
    quantity = request.form['quantity']

    if not name or not event_id or not quantity:
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('main.index'))

    return redirect(url_for('main.checkout_simulado', name=name, event_id=event_id, quantity=quantity))

@main.route('/checkout_simulado', methods=['GET', 'POST'])
def checkout_simulado():
    if request.method == 'POST':
        name = request.form.get('name')
        event_id = request.form.get('event')
        quantity = request.form.get('quantity')
    else:
        name = request.args.get('name')
        event_id = request.args.get('event_id')
        quantity = request.args.get('quantity')

    if not name or not event_id or not quantity:
        flash('Datos incompletos para el checkout.', 'error')
        return redirect(url_for('main.index'))

    event = Event.query.get(event_id)
    return render_template('checkout.html', name=name, event=event, quantity=quantity)

@main.route('/pago_confirmado', methods=['POST'])
def pago_confirmado():
    name = request.form['name']
    event_id = request.form['event_id']
    quantity = request.form['quantity']
    payment_method = request.form['payment_method']

    try:
        quantity = int(quantity)
    except ValueError:
        flash('Cantidad inválida.', 'error')
        return redirect(url_for('main.index'))

    transaction_id = str(uuid4())
    for _ in range(quantity):
        ticket_code = str(uuid4())
        qr = qrcode.QRCode()
        qr.add_data(ticket_code)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        ticket = Ticket(
            name=name,
            event_id=event_id,
            quantity=1,
            qr_code=qr_code_base64,
            ticket_code=ticket_code,
            transaction_id=transaction_id,
            payment_method=payment_method,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(ticket)

    db.session.commit()
    flash(f'Pago realizado correctamente con método: {payment_method}', 'success')
    return redirect(url_for('main.confirmacion_compra', transaction_id=transaction_id))

@main.route('/confirmacion_compra/<string:transaction_id>')
def confirmacion_compra(transaction_id):
    tickets = Ticket.query.filter_by(transaction_id=transaction_id).all()
    if not tickets:
        flash('No se encontraron tickets para esta transacción.', 'error')
        return redirect(url_for('main.index'))
    return render_template('ticket_multiple.html', tickets=tickets)

@main.route('/ticket/<ticket_code>')
def ticket(ticket_code):
    ticket = Ticket.query.filter_by(ticket_code=ticket_code).first_or_404()
    return render_template('ticket.html', ticket=ticket)

# --------------------------
# Administración y staff
# --------------------------

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
        event = Event(name=name)
        db.session.add(event)
        db.session.commit()
        flash('Evento agregado correctamente!', 'success')
    else:
        flash('El nombre del evento es obligatorio', 'error')
    return redirect(url_for('main.admin'))

# --------------------------
# Verificación de tickets
# --------------------------

@main.route('/verificar')
def verificar_qr():
    return render_template('verificar.html')

@main.route('/api/verificar_ticket', methods=['POST'])
def api_verificar_ticket():
    data = request.get_json()
    qr_data = data.get('ticket_id')
    ticket = Ticket.query.filter_by(ticket_code=qr_data).first()

    if not ticket:
        return jsonify({'status': 'error', 'message': '❌ Ticket no encontrado'})

    ticket_details = {
        'ticket_code': ticket.ticket_code,
        'buyer_name': ticket.name,
        'event_name': ticket.event.name,
        'usado': ticket.usado
    }

    if ticket.usado:
        return jsonify({
            'status': 'warning',
            'message': '⚠️ Ticket ya fue usado',
            'ticket_info': ticket_details
        })

    ticket.usado = True
    db.session.commit()
    return jsonify({
        'status': 'ok',
        'message': f'✅ Ticket válido. Bienvenido {ticket.name}!',
        'ticket_info': ticket_details
    })

# --------------------------
# Tickets personales
# --------------------------

@main.route('/mis_tickets')
@login_required
def mis_tickets():
    tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    return render_template('mis_tickets.html', tickets=tickets)

