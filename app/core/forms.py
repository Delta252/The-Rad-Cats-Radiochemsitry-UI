import sys
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField, validators

# Custom validator to check if password is part of the 100k pwned list
def PasswordNotExists(self, field):
    if getattr(sys, 'frozen', False):
            filePath = 'app/dependencies/100k-pswd.txt'
    elif __file__:
        filePath = 'dependencies/100k-pswd.txt'
        with open(filePath, encoding='utf-8') as myfile:
            if field.data in myfile.read():
                    raise validators.ValidationError('Password is too common.')

# Form class for registration
class RegisterForm(Form):
    user = StringField('Username', [validators.Length(min=1, max=255, message='Invalid username length.')], render_kw={"placeholder": "Username *"})
    pswd = PasswordField('Password', validators=[validators.DataRequired(), validators.Length(min=8, message='Password too short.'), PasswordNotExists], render_kw={"placeholder": "Password *"},)
    confirm = PasswordField('Confirm Password.', [validators.EqualTo('pswd', message='Passwords do not match.')], render_kw={"placeholder": "Confirm Password *"},)
