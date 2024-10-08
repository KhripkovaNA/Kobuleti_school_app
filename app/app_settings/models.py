from app import db
from datetime import datetime
from ..common_servicies.service import LOCAL_TZ


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    color = db.Column(db.String(16))

    def __repr__(self):
        return f"<Room {self.id}: {self.name}>"


class SubscriptionType(db.Model):
    __tablename__ = 'subscription_types'

    id = db.Column(db.Integer, primary_key=True)
    lessons = db.Column(db.Integer)
    period = db.Column(db.String(50), default="")
    duration = db.Column(db.Integer)
    price = db.Column(db.Numeric(8, 2))
    subscriptions = db.relationship('Subscription', backref='subscription_type')

    def __repr__(self):
        if self.lessons:
            return f"<SubscriptionType {self.id}: lessons {self.lessons}, price {self.price}>"

        elif self.duration:
            return f"<SubscriptionType {self.id}: duration {self.duration}, price {self.price}>"

        else:
            return f"<SubscriptionType {self.id}: price {self.price}>"


class UserAction(db.Model):
    __tablename__ = 'user_actions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='actions')
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(LOCAL_TZ))
    description = db.Column(db.String(120))
