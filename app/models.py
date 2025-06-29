from . import db
from flask_login import UserMixin
import uuid

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(128))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    qr_code = db.Column(db.Text, nullable=False)
    ticket_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    usado = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.String(50))        # <-- Agregado
    transaction_id = db.Column(db.String(36))        # <-- Agregado

    event = db.relationship('Event', backref=db.backref('tickets', lazy=True))
