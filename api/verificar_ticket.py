@main.route('/api/verificar_ticket', methods=['POST'])
def api_verificar_ticket():
    data = request.get_json()
    qr_data = data.get('ticket_id')  # ahora será el ticket_code que está en el QR

    ticket = Ticket.query.filter_by(ticket_code=qr_data).first()

    if not ticket:
        return jsonify({'status': 'error', 'message': '❌ Ticket no encontrado'})

    if ticket.usado:
        return jsonify({'status': 'error', 'message': '⚠️ Ticket ya fue usado'})

    ticket.usado = True
    db.session.commit()

    return jsonify({'status': 'ok', 'message': f'✅ Ticket válido. Bienvenido {ticket.name}!'})
