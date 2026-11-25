from django import forms
from .models import Habit, Tag

class HabitForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        help_text="Enter up to 5 comma-separated tags (e.g. Health, Study)",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Health, Morning'})
    )

    class Meta:
        model = Habit
        fields = ['title', 'description', 'frequency', 'difficulty', 'reminder_time', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Read 15 mins'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'reminder_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tag_names'].initial = ", ".join([t.name for t in self.instance.tags.all()])

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        qs = Habit.objects.filter(user=self.user, title__iexact=title)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("You already have an active habit with this title.")
        return title

    def clean(self):
        cleaned_data = super().clean()
        if self.user:
            active_count = Habit.objects.filter(user=self.user, is_active=True)
            if self.instance and self.instance.pk:
                active_count = active_count.exclude(pk=self.instance.pk)
            if cleaned_data.get('is_active') and active_count.count() >= 20:
                raise forms.ValidationError("You cannot have more than 20 active habits at a time.")
        
        raw_tags = cleaned_data.get('tag_names', '')
        tag_list = [t.strip() for t in raw_tags.split(',') if t.strip()]
        if len(tag_list) > 5:
            raise forms.ValidationError("A habit can have at most 5 tags.")
        return cleaned_data