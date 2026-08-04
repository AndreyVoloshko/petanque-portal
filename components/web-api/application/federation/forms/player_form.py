from django import forms
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from django.forms.widgets import ClearableFileInput
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class ImageThumbnailFileInput(ClearableFileInput):
    template = 'forms/profile/image_field.html'

class PlayerForm(forms.ModelForm):
    email = forms.EmailField(label=_("Email address"), required=True)

    def __init__(self, *args, **kwargs):
        super(PlayerForm, self).__init__(*args, **kwargs)
        
        self.fields['avatar'].widget = ImageThumbnailFileInput()

        try:
            self.fields['email'].initial = self.instance.user.email
        except User.DoesNotExist:
            pass

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '/profile/#profile'

        self.helper.layout = Layout(
            Div(
                Div(
                    Field('avatar', template="forms/profile/image_field.html",
                          avatar=self.instance.avatar,
                          attrs={'class': 'form-control', 'avatar': self.instance.avatar},
                          widget=ImageThumbnailFileInput()
                    ),
                    css_class="col-lg-2"
                ),
                Div(
                    Div(
                        Div('name', css_class="col-lg-4"),
                        Div('surname', css_class="col-lg-4"),
                        Div('second_name', css_class="col-lg-4"),
                        css_class="row"
                    ),
                    Div(
                        Div('email', css_class="col-lg-4"),
                        Div('gender', css_class="col-lg-4"),
                        Div('birth_date', css_class="col-lg-4"),
                        css_class="row"
                    ),
                    Div(
                        Div('current_club', css_class="col-lg-6"),
                        Div('country', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    Div(
                        Div('facebook', css_class="col-lg-6"),
                        Div('instagram', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    Div(
                        Div('twitter', css_class="col-lg-6"),
                        Div('website', css_class="col-lg-6"),
                        css_class="row"
                    ),
                    css_class="col-lg-10"
                ),
                css_class="row"
            ),
            Div(
                HTML('<hr class="my-2">'),
                Div(
                    Div('insurance_expiration_date', css_class="col-lg-4"),
                    css_class="row"
                ),
                css_class="col-lg-12"
            ),
            Div(
                Submit('submit', _('Save'), css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            )
        )

    def save(self, *args, **kwargs):
      """
      Update the primary email address on the related User object as well.
      """
      u = self.instance.user
      u.email = self.cleaned_data['email']
      u.save()
      profile = super(PlayerForm, self).save(*args,**kwargs)
      return profile


    class Meta:
        model = Player
        fields = ('avatar',
                  'name',
                  'surname',
                  'second_name',
                  'birth_date',
                  'current_club',
                  'country',
                  'gender',
                  'facebook',
                  'twitter',
                  'instagram',
                  'website',
                  'insurance_expiration_date')
        labels = {
            "email": _("Email address"),
            "avatar": _("Avatar"),
            "name": _("First name"),
            "surname": _("Last name"),
            "second_name": _("Middle name"),
            "birth_date": _("Date of birth (dd.mm.yyyy)"),
            "current_club": _("Club"),
            "country": _("Country"),
            "gender": _("Gender"),
            "facebook": _("Facebook page"),
            "twitter": _("Twitter page"),
            "instagram": _("Instagram page"),
            "website": _("Personal website"),
            "insurance_expiration_date": _("Insurance valid until"),
        }
        widgets = {
            'avatar': ImageThumbnailFileInput,
            'insurance_expiration_date': forms.DateInput(attrs={'type': 'date'}),
        }
