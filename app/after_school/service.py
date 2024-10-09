from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, or_
from app.app_settings.models import SubscriptionType
from app.common_servicies.after_school_subject import after_school_subject
from app.common_servicies.service import (
    MONTHS, conjugate_hours, get_weekday_date, get_period, calc_month_index, get_today_date
)
from app.school.students.service import format_student_info
from app.school.subscriptions.models import Subscription


def get_after_school_prices():
    after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()
    price_types = []
    for price_type in after_school_prices:
        price_dict = {
            "id": price_type.id,
            "price": float(price_type.price)
        }
        if price_type.period == "месяц":
            price_dict["period"] = "month"
        elif price_type.period == "неделя":
            price_dict["period"] = "week"
        elif price_type.period == "день":
            price_dict["period"] = "day"
        else:
            price_dict["period"] = "hour"
        price_types.append(price_dict)

    return price_types


def get_day(day_index):
    result_date = get_today_date() + timedelta(days=day_index)
    return result_date


def calc_day_index(date):
    day_index = (date - get_today_date()).days
    return day_index


def get_after_school_students(period_index, period_type):
    current_period = get_period(0)
    after_school_id = after_school_subject().id
    if period_type == "month":
        date = get_today_date()
        period = get_period(period_index)
    else:
        date = get_day(period_index)
        period = get_period(calc_month_index(date))
    first_date = datetime(period[1], period[0], 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)
    if period_type == "month":
        after_school_subscriptions = Subscription.query.filter(
            Subscription.subject_id == after_school_id,
            or_(
                and_(
                    Subscription.period != "week",
                    Subscription.purchase_date >= first_date,
                    Subscription.purchase_date <= last_date
                ),
                and_(
                    Subscription.period == "week",
                    or_(
                        and_(
                            Subscription.purchase_date >= first_date,
                            Subscription.purchase_date <= last_date
                        ),
                        and_(
                            Subscription.end_date >= first_date,
                            Subscription.end_date <= last_date
                        )
                    )
                )
            )
        ).all()
    else:
        after_school_subscriptions = Subscription.query.filter(
            Subscription.subject_id == after_school_id,
            or_(
                and_(
                    Subscription.period == "month",
                    Subscription.purchase_date >= first_date,
                    Subscription.purchase_date <= last_date
                ),
                and_(
                    Subscription.period == "week",
                    Subscription.purchase_date <= date,
                    Subscription.end_date >= date
                ),
                and_(
                    ~Subscription.period.in_(["month", "week"]),
                    Subscription.purchase_date == date,
                )
            )
        ).all()
    after_school_students = []
    for subscription in after_school_subscriptions:
        after_school_student = subscription.student
        if after_school_student not in after_school_students:
            format_student_info(after_school_student)
            after_school_student.shift = subscription.shift if subscription.shift else 10
            if period == current_period:
                activities = sorted([subject.name for subject in after_school_student.subjects
                                     if subject.subject_type.name not in ["school", "after_school"]])
                after_school_student.activities = activities
            if subscription.period == "month":
                after_school_student.attendance = ["месяц"]
            elif subscription.period == "week":
                after_school_student.attendance = [
                    f"неделя ({subscription.purchase_date:%d.%m}-{subscription.end_date:%d.%m})"
                ]
            elif subscription.period == "day":
                after_school_student.attendance = [f"день ({subscription.purchase_date:%d.%m})"]
            else:
                after_school_student.attendance = [f"{subscription.period} ({subscription.purchase_date:%d.%m})"]
            after_school_students.append(after_school_student)
        else:
            student_ind = after_school_students.index(after_school_student)
            after_school_student = after_school_students[student_ind]
            if subscription.period == "week":
                after_school_student.attendance.append(
                    f"неделя ({subscription.purchase_date:%d.%m}-{subscription.end_date:%d.%m})"
                )
            elif subscription.period == "day":
                after_school_student.attendance.append(f"день ({subscription.purchase_date:%d.%m})")
            else:
                after_school_student.attendance.append(f"{subscription.period} ({subscription.purchase_date:%d.%m})")
    after_school_students = sorted(after_school_students, key=lambda x: (x.shift, x.last_name, x.first_name))

    return after_school_students, period, current_period, date


def handle_after_school_adding(student_id, form, period):
    term = form.get("term")
    shift = int(form.get("shift")) if term in ["month", "day", "week"] and form.get("shift") != "0" else None
    if term == "month":
        purchase_month, purchase_year = period.split("-")
        purchase_date = datetime(int(purchase_year), int(purchase_month), 1).date()
        end_date = purchase_date + relativedelta(months=+1, days=-1)
        period_text = f"{MONTHS[int(purchase_month) - 1]}"
    elif term == "week":
        selected_date = datetime.strptime(form.get("attendance_date"), '%d.%m.%Y').date()
        purchase_date = get_weekday_date(0, selected_date)
        end_date = get_weekday_date(6, selected_date)
        period_text = f"неделя {purchase_date:%d.%m}-{end_date:%d.%m.%Y}"
    else:
        purchase_date = datetime.strptime(form.get("attendance_date"), '%d.%m.%Y').date()
        end_date = purchase_date
        period_text = f"{purchase_date:%d.%m.%Y}"
        if term == "hour":
            hours = int(form.get("hours"))
            term = conjugate_hours(hours)
            period_text = f"{term} {period_text}"

    subscription_type_id = int(form.get("subscription_type"))

    check_after_school = Subscription.query.filter_by(
        subject_id=after_school_subject().id,
        student_id=student_id,
        purchase_date=purchase_date,
        end_date=end_date,
        period=term
    ).first()

    if check_after_school:
        return

    else:
        new_after_school_subscription = Subscription(
            subject_id=after_school_subject().id,
            student_id=student_id,
            subscription_type_id=subscription_type_id,
            purchase_date=purchase_date,
            end_date=end_date,
            shift=shift,
            period=term
        )

        return new_after_school_subscription, period_text
