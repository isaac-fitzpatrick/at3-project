from django.db import models
from django.contrib.auth.models import User

class Group(models.Model):
    name = models.CharField(max_length=100)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_groups')
    members = models.ManyToManyField(User, related_name='group_memberships', blank=True)
    invited_users = models.ManyToManyField(User, related_name='pending_invitations', blank=True)
    
    def __str__(self):
        return self.name
    
class GroupJoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    is_approved = models.BooleanField(default=False)
    votes = models.ManyToManyField(User, related_name='votes', blank=True)  # Tracks users who voted
    created_at = models.DateTimeField(auto_now_add=True)
    
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # User who posted the comment
    group = models.ForeignKey(Group, related_name='comments', on_delete=models.CASCADE)  # Group associated with the comment
    content = models.TextField()  # The comment content
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the comment was posted
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for the latest update

    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}..."  # Show only first 20 chars for preview
    
class Event(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    status = models.CharField(max_length=20, default='Pending')  # Can be 'Pending' or 'Active'
    group = models.ForeignKey(Group, related_name='events', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='event_memberships', blank=True)  
    notification = models.FileField(upload_to='notifications/', blank=True, null=True)

class Lesson(models.Model):
    name = models.CharField(max_length=32)
    due_date = models.DateField()
    description = models.TextField() 
    file = models.FileField(upload_to='resources/', blank=True, null=True) # Uploaded resources by the teacher
    group = models.ForeignKey(Group, related_name='lessons', on_delete=models.CASCADE) # Parent
    response = models.ManyToManyField(User, related_name='responses', blank=True) # Tracks the amount of responses/content of responses
    
    def __str__(self):
        return self.name

class LessonResource(models.Model):
    file = models.FileField(upload_to='resources/')
    lesson = models.ForeignKey('Lesson', related_name='resources', on_delete=models.CASCADE)

    def __str__(self):
        return self.file.name
    
class StudentSubmission(models.Model):
    lesson = models.ForeignKey(Lesson, related_name='lesson_submissions', on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='student_submissions', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.lesson.name}"

class SubmissionFile(models.Model):
    submission = models.ForeignKey(StudentSubmission, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')

    def __str__(self):
        return self.file.name
    
class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey(Event, related_name='assessment_submissions', on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='student_assessment_submissions', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(blank=True, null=True)  # Feedback from the teacher
    marks = models.CharField(max_length=10, blank=True, null=True)  # Feedback in the form of a mark

    def __str__(self):
        return f"{self.student.username} - {self.lesson.name}"
    
class AssessmentSubmissionFile(models.Model):
    submission = models.ForeignKey(StudentSubmission, related_name='assessment_submission_files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')