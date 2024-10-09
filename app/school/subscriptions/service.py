from app import db
from app.common_servicies.after_school_subject import after_school_subject
from app.common_servicies.service import conjugate_lessons, get_today_date
from .models import Subscription


def format_subscription_type(subscription_type):
    type_of_subscription = f"{conjugate_lessons(subscription_type.lessons)} за {subscription_type.price:.0f} " \
                           f"({subscription_type.duration} дней)"
    return type_of_subscription


def check_subscription(student, lesson, subject_id):
    after_school = after_school_subject()
    cond = lesson == 0
    if cond:
        date = get_today_date()
    else:
        date = lesson.date
    if subject_id == 0:
        subscriptions = student.subscriptions
    else:
        subscriptions = Subscription.query.filter(Subscription.subject_id.in_([subject_id, after_school.id]),
                                                  Subscription.student_id == student.id).all()
    for subscription in subscriptions:
        if subscription.subject == after_school:
            cond11 = subscription.purchase_date.month == date.month
            cond12 = subscription.period == "month"
            if subscription.period == "week":
                cond2 = subscription.purchase_date <= date <= subscription.end_date
            else:
                cond2 = False
            cond31 = subscription.purchase_date > date
            cond32 = subscription.period in ["month", "week"]
            subscription.active = True if (
                    ((cond11 and cond12) or cond2)
                    or (cond31 and cond32 and cond)
            ) else False
            db.session.commit()
        else:
            cond1 = subscription.purchase_date <= date <= subscription.end_date
            cond2 = subscription.lessons_left > 0
            cond3 = subscription.purchase_date > date
            subscription.active = True if (
                    (cond1 and cond2)
                    or (cond3 and cond)
            ) else False
            db.session.commit()


def check_subscriptions(subscriptions):
    date = get_today_date()
    for subscription in subscriptions:
        cond1 = subscription.purchase_date <= date <= subscription.end_date
        cond2 = subscription.lessons_left > 0
        subscription.active = True if cond1 and cond2 else False
        db.session.commit()
        subscription.type_of_subscription = format_subscription_type(subscription.subscription_type)


def format_subscription_types(subscription_types):
    types_of_subscription = []
    for subscription_type in subscription_types:
        if subscription_type.lessons:
            types_of_subscription.append((subscription_type.id, format_subscription_type(subscription_type)))

    return types_of_subscription
