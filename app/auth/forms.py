from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, DataRequired


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(message='Заполните это поле')])
    password = PasswordField(validators=[DataRequired(message='Заполните это поле')])