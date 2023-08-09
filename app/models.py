from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


parent_child_table = db.Table(
    'parent_child_table',
    db.Column('parent_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('child_id', db.Integer, db.ForeignKey('persons.id'))
)


student_subject_table = db.Table(
    'student_subject_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Person(db.Model):
    __tablename__ = 'persons'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50))
    patronym = db.Column(db.String(50))
    dob = db.Column(db.Date)
    person_type = db.Column(db.String(16))
    status = db.Column(db.String(50))
    teacher = db.Column(db.Boolean, default=False)
    leaving_reason = db.Column(db.String(120))
    pause_until = db.Column(db.Date)
    comment = db.Column(db.String(120))

    subjects = db.relationship('Subject', secondary=student_subject_table,
                               backref='students', lazy='dynamic')

    subscriptions = db.relationship('Subscription', backref='student', lazy='dynamic')

    parents = db.relationship('Person', secondary=parent_child_table,
                              primaryjoin=(parent_child_table.c.child_id == id),
                              secondaryjoin=(parent_child_table.c.parent_id == id),
                              backref=db.backref('children', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return f"<Person {self.id}: {self.last_name} {self.first_name}>"


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), unique=True)
    telegram = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    other_contacts = db.Column(db.String(64))

    person = db.relationship('Person', backref='contacts', uselist=False)


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __repr__(self):
        return f"<Subject {self.id}: {self.name}>"


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    lessons_left = db.Column(db.Integer, default=8)
    subscription_type = db.Column(db.String(50))

    subject = db.relationship('Subject', backref='subscription', uselist=False)

