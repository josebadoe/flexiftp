from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, MultiField, Field
from crispy_forms.bootstrap import FormActions

class UploadForm(forms.Form):
    name = forms.CharField(min_length=3, max_length=40, strip=True,
                           label="Identificación")
    description = forms.CharField(max_length=1000, widget=forms.Textarea, strip=True,
                                  label="Descripción")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Field('name', css_class='form-control'),
                Field('description', css_class='form-control', rows=5),
                css_class='form-group'
            ),
            FormActions(
                Submit('submit', "Registrar", css_class='btn-default')
            )
        )
