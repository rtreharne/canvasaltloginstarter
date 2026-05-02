from django import forms


class LoginRequestForm(forms.Form):
    course_id = forms.CharField(max_length=64)
    login_id = forms.CharField(max_length=255)

    def clean_course_id(self):
        value = self.cleaned_data["course_id"].strip()
        if not value.isdigit():
            raise forms.ValidationError("Invalid request context.")
        return value

    def clean_login_id(self):
        value = self.cleaned_data["login_id"].strip()
        if len(value) < 3:
            raise forms.ValidationError("Please enter a valid login ID.")
        return value
