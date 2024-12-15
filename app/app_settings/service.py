from sqlalchemy import or_, and_
from app.app_settings.models import UserAction, SchoolSemester
from app import db


def user_action(user, action_description):
    new_action = UserAction(
        user_id=user.id,
        description=action_description
    )
    db.session.add(new_action)


def calculate_school_year(date):
    return date.year if 9 <= date.month <= 12 else date.year - 1


def validate_semester(start_date, end_date):
    conflicting_semesters = SchoolSemester.query.filter(
        or_(
            and_(
                SchoolSemester.start_date <= start_date,
                SchoolSemester.end_date >= start_date
            ),
            and_(
                SchoolSemester.start_date <= end_date,
                SchoolSemester.end_date >= end_date
            )
        )
    ).all()
    if start_date < end_date and not conflicting_semesters:
        return True
    else:
        return False
