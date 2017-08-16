from django import forms
from federation.models.player import Player
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML
from floppyforms import ClearableFileInput
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.conf import settings


class ImageThumbnailFileInput(ClearableFileInput):
    template_name = 'forms/profile/image_field.html'


class PlayerForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PlayerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '/profile/#profile'

        self.helper.layout = Layout(
            Div(
                Div(
                    'avatar',
                    css_class="col-md-2"
                ),
                Div(
                    Div(
                        Div(
                            'name',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'surname',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'licence_number',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'current_club',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    HTML('<hr />'),
                    Div(
                        Div(
                            'instagram',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'website',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    css_class="col-md-5"
                ),
                Div (
                    Div(
                        Div(
                            'gender',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'birth_date',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'country',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'prefred_position',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    HTML('<hr />'),
                    Div(
                        Div(
                            'facebook',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    Div(
                        Div(
                            'twitter',
                            css_class="col-md-12 form-group"
                        ),
                        css_class="row"
                    ),
                    css_class="col-md-5"
                ),
                css_class="row"
            ),
            HTML('<hr />'),
            Div(
                Submit('submit', 'Зберігти', css_class='btn btn-success'),
                css_class="col-md-12 text-center form-group"
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

    class Meta:
        model = Player
        fields = ('avatar',
                  'name',
                  'surname',
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
            "avatar": "Аватар",
            "name": "Iм'я",
            "surname": "Прiзвище",
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
            'avatar': ImageThumbnailFileInput
        }