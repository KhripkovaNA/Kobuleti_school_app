from app import db
from app.school.subscriptions.models import subscription_types_table


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    short_name = db.Column(db.String(50))
    description = db.Column(db.String(120), default="")
    one_time_price = db.Column(db.Numeric(8, 2))
    school_price = db.Column(db.Numeric(8, 2))
    subscription_types = db.relationship('SubscriptionType', secondary=subscription_types_table,
                                         backref='subjects', lazy='dynamic')
    subject_type_id = db.Column(db.Integer, db.ForeignKey('subject_types.id'))
    subject_type = db.relationship('SubjectType', backref='subjects')
    subscriptions = db.relationship('Subscription', backref='subject')

    def __repr__(self):
        return f"<Subject {self.id}: {self.name}>"


class SubjectType(db.Model):
    __tablename__ = 'subject_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(50))
