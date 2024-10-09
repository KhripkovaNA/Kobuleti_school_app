from app import db
from datetime import datetime
from app.common_servicies.service import LOCAL_TZ


subscription_types_table = db.Table(
    'subscription_types_table',
    db.Column('subscription_types_id', db.Integer, db.ForeignKey('subscription_types.id')),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'))
)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    subscription_type_id = db.Column(db.Integer, db.ForeignKey('subscription_types.id'))
    lessons_left = db.Column(db.Integer)
    purchase_date = db.Column(db.Date, default=lambda: datetime.now(LOCAL_TZ).date())
    end_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=False)
    shift = db.Column(db.Integer)
    period = db.Column(db.String(50))
