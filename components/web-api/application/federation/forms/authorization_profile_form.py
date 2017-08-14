from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from django.contrib.auth.forms import PasswordChangeForm

class AuthorizationProfileForm(PasswordChangeForm):

    def __init__(self, user, *args, **kwargs):
        super(AuthorizationProfileForm, self).__init__(user, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '/profile/#authorization_form'

        self.helper.layout = Layout(
            Div(
                Div (
                    Div(
                        Div(
                            HTML("""
                                <label class='control-label'>Ім'я користувача:</label>
                                <input class="textinput textInput form-control" type="text" readonly="readonly" value="{{ user.username }}" />
                            """),
                            css_class="col-md-12 form-group"
                        ),
                        Div(
                            Field('old_password'),
                            css_class="col-md-12 form-group"
                        ),
                        Div(
                            Field('new_password1'),
                            css_class="col-md-12 form-group"
                        ),
                        Div(
                            Field('new_password2'),
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    css_class="col-md-12"
                ),
                css_class="row"
            ),
            Div(
                css_class="clearfix"
            ),
            HTML('<hr />'),
            Div(
                Submit('submit', 'Зберігти', css_class='btn btn-success'),
                css_class="col-md-12 text-center form-group"
            )
        )

    class Meta:
        labels = {
            "old_password": "Поточний пароль",
            "new_password1": "Новий пароль",
            "new_password2": "Повторити новий пароль"
        }