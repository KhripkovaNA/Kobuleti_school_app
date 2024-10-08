from app import db
from datetime import datetime
from ..common_servicies.service import LOCAL_TZ


class Finance(db.Model):
    __tablename__ = 'finance'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    person = db.relationship('Person', backref='finance')
    date = db.Column(db.Date, default=lambda: datetime.now(LOCAL_TZ).date())
    amount = db.Column(db.Numeric(8, 2))
    operation_type = db.Column(db.String(50))
    student_balance = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(120))
    service = db.Column(db.String(16))
    service_id = db.Column(db.Integer)
    balance_state = db.Column(db.Numeric(8, 2))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    subject = db.relationship('Subject', backref='purchases')