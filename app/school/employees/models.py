from app import db


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    person = db.relationship('Person', backref='roles')


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    duty_type = db.Column(db.String(50))
    duty_hours = db.Column(db.Integer)

    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    person = db.relationship('Person', backref='reports')