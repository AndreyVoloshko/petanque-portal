from django import forms
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML, Field
from django.forms.widgets import ClearableFileInput
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import User


class ImageThumbnailFileInput(ClearableFileInput):
    template = 'forms/profile/image_field.html'

class PlayerForm(forms.ModelForm):
    email = forms.EmailField(label="Email адреса", required=True)

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
                Submit('submit', 'Зберегти', css_class='btn btn-success'),
                css_class="col-lg-12 text-center mb-3"
            )
        )

    def clean_content(self):
        content = self.cleaned_data['content']
        content_type = content.content_type.split('/')[0]
        if content_type in settings.CONTENT_TYPES:
            if content._size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (
                filesizeformat(settings.MAX_UPLOAD_SIZE), filesizeformat(content._size)))
        else:
            raise forms.ValidationError(_('File type is not supported'))
        return content


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
                  'licence_number',
                  'gender',
                  'facebook',
                  'twitter',
                  'instagram',
                  'website',
                  'prefred_position')
        labels = {
            "email": "Email адреса",
            "avatar": "Аватар",
            "name": "Iм'я",
            "surname": "Прiзвище",
            "second_name": "По батькові",
            "birth_date": "Дата народження (дд.мм.рррр)",
            "current_club": "Клуб",
            "country": "Країна",
            "licence_number": "Номер ліцензії",
            "gender": "Стать",
            "facebook": "Сторінка Facebook",
            "twitter": "Сторінка Twitter",
            "instagram": "Сторінка Instagram",
            "website": "Пенсональна Web-сторінка",
            "prefred_position": "Позиція"
        }
        widgets = {
            'avatar': ImageThumbnailFileInput,
        }