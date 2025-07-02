from django import forms
from .models import Group
from .models import Comment
from .models import Lesson
from .models import LessonResource

class GroupCreationForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        group = super().save(commit=False)
        group.admin = self.user  # Assign the logged-in user as the admin
        if commit:
            group.save()
            group.members.add(self.user)  # Add the admin to the members list
        return group
    
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your comment...'})
        }

    # Clean the content to sanitise input
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if "<script>" in content.lower():  # Prevent XSS by checking for script tags
            raise forms.ValidationError("Invalid content.")
        return content
    
class LessonForm(forms.ModelForm):
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        required=False,
        label="Additional Resources"
    )

    class Meta:
        model = Lesson
        fields = ['name', 'due_date', 'description']

    def save(self, commit=True):
        lesson = super().save(commit=commit)
        files = self.files.getlist('files')
        for file in files:
            LessonResource.objects.create(lesson=lesson, file=file)
        return lesson
    
class StudentSubmissionForm(forms.ModelForm):
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        required=True,
        label="Upload Files"
    )

    class Meta:
        model = StudentSubmission
        fields = []

    def save(self, commit=True):
        submission = super().save(commit=commit)
        files = self.files.getlist('files')
        for file in files:
            SubmissionFile.objects.create(submission=submission, file=file)
        return submission