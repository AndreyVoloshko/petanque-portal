from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _

class AuthorizationProfileForm(PasswordChangeForm):

    def __init__(self, user, *args, **kwargs):
        super(AuthorizationProfileForm, self).__init__(user, *args, **kwargs)
        self.fields['old_password'].label = _("Current password")
        self.fields['new_password1'].label = _("New password")
        self.fields['new_password2'].label = _("Repeat new password")

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '/profile/#authorization_form'

        self.helper.layout = Layout(
            Div(
                Div (
                    Div(
                        Div(
                            HTML("""
                                <label class='control-label form-label'>""" + str(_("Username")) + """:</label>
                                <input class="textinput textInput form-control" type="text" readonly="readonly" value="{{ user.username }}" />
                            """),
                            css_class="col-lg-12 mb-3"
                        ),
                        Div(
                            Field('old_password'),
                            css_class="col-lg-12 mb-3"
                        ),
                        Div(
                            Field('new_password1'),
                            css_class="col-lg-12 mb-3"
                        ),
                        Div(
                            Field('new_password2'),
                            css_class="col-lg-12 mb-3"
                        ),
                        css_class="row"
                    ),
                    css_class="col-lg-12"
                ),
                css_class="row"
            ),
            Div(
                css_class="clearfix"
            ),
            Div(
                Submit('submit', _('Save'), css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            )
        )

    class Meta:
        labels = {
            "old_password": _("Current password"),
            "new_password1": _("New password"),
            "new_password2": _("Repeat new password")
        }
