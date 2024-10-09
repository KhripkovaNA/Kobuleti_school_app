from flask_wtf import FlaskForm
from wtforms import Form, HiddenField, StringField, IntegerField, BooleanField, FieldList, FormField
from wtforms.validators import InputRequired, NumberRange
from app.school.forms import validate_date_format


class SubscriptionForm(Form):
    subscription_id = HiddenField()
    subject_name = StringField()
    lessons = IntegerField(validators=[InputRequired(message='Заполните это поле'),
                                       NumberRange(0, 20, message='Неправильный формат')])
    full_subscription = BooleanField()
    purchase_date = StringField(validators=[InputRequired(message='Заполните это поле'), validate_date_format])
    end_date = StringField(validators=[InputRequired(message='Заполните это поле'), validate_date_format])


class SubscriptionsEditForm(FlaskForm):
    subscriptions = FieldList(FormField(SubscriptionForm), min_entries=0, max_entries=20)