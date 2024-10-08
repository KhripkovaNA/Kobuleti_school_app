from .models import UserAction
from app import db


def user_action(user, action_description):
    new_action = UserAction(
        user_id=user.id,
        description=action_description
    )
    db.session.add(new_action)
