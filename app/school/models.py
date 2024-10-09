from app import db

parent_child_table = db.Table(
    'parent_child_table',
    db.Column('parent_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('child_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('relation', db.String(50))
)

student_subject_table = db.Table(
    'student_subject_table',
    db.Column('student_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


teacher_subject_table = db.Table(
    'teacher_subject_table',
    db.Column('teacher_id', db.Integer, db.ForeignKey('persons.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


class Person(db.Model):
    __tablename__ = 'persons'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50))
    patronym = db.Column(db.String(50), default="")
    dob = db.Column(db.Date)
    person_type = db.Column(db.String(16))
    status = db.Column(db.String(50))
    teacher = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(16))
    leaving_reason = db.Column(db.String(120), default="")
    pause_until = db.Column(db.Date)
    comment = db.Column(db.String(120), default="")
    primary_contact = db.Column(db.Integer, db.ForeignKey('persons.id'))

    subjects = db.relationship('Subject', secondary=student_subject_table,
                               backref='students', lazy='dynamic')
    subjects_taught = db.relationship('Subject', secondary=teacher_subject_table,
                                      backref='teachers', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='student', lazy='dynamic')
    school_class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    parents = db.relationship('Person', secondary=parent_child_table,
                              primaryjoin=(parent_child_table.c.child_id == id),
                              secondaryjoin=(parent_child_table.c.parent_id == id),
                              backref=db.backref('children', lazy='dynamic'), lazy='dynamic')
    balance = db.Column(db.Numeric(8, 2), default=0)

    def __repr__(self):
        return f"<Person {self.id}: {self.last_name} {self.first_name}>"


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), unique=True)
    telegram = db.Column(db.String(50), default="")
    phone = db.Column(db.String(50), default="")
    other_contact = db.Column(db.String(64), default="")
    person = db.relationship('Person', backref='contacts', uselist=False)