from django.http import HttpResponse 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from .forms import GroupCreationForm
from .models import Group, Comment
from .models import GroupJoinRequest
from .forms import CommentForm
from .models import Event
from .models import Lesson
from .forms import LessonForm
from .models import LessonResource
from .models import StudentSubmission
from .forms import StudentSubmissionForm
from .models import AssessmentSubmission
from .forms import AssessmentSubmissionForm
from .forms import AssessmentFeedbackForm
import urllib.parse
import os

@login_required
def home(request):
    user = request.user
    pending_invitations = user.pending_invitations.all() # Get pending group invitations for the current user
    user_groups = user.group_memberships.all()  # Get groups the user is a member of
    user_join_requests = GroupJoinRequest.objects.filter(user=user)  # Get join requests sent by the user
    available_groups = Group.objects.exclude(members=user).exclude(join_requests__user=user) # Get groups the user is not a member of and the user has not requested to join
    context = {
        'pending_invitations': pending_invitations,
        'user_groups': user_groups,
        'user_join_requests': user_join_requests,
        'available_groups': available_groups
    }
    return render(request, 'chipin/home.html', context)

@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupCreationForm(request.POST, user=request.user)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Group "{group.name}" created successfully!')
            return redirect('chipin:group_detail', group_id=group.id)
    else:
        form = GroupCreationForm(user=request.user)
    return render(request, 'chipin/create_group.html', {'form': form})

@login_required
def group_detail(request, group_id, edit_comment_id=None):
    group = get_object_or_404(Group, id=group_id)
    comments = group.comments.all().order_by('-created_at')  # Fetch all comments for the group
    events = group.events.all()  # Fetch all events associated with the group
    # Add a new comment or edit an existing comment
    if edit_comment_id: # Fetch the comment to edit, if edit_comment_id is provided
        comment_to_edit = get_object_or_404(Comment, id=edit_comment_id)
        if comment_to_edit.user != request.user:
            return redirect('chipin:group_detail', group_id=group.id)
    else:
        comment_to_edit = None
    if request.method == 'POST':
        if comment_to_edit: # Editing an existing comment
            form = CommentForm(request.POST, instance=comment_to_edit)
        else: # Adding a new comment
            form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.group = group
            comment.save()
            return redirect('chipin:group_detail', group_id=group.id)
    else:
        form = CommentForm(instance=comment_to_edit) if comment_to_edit else CommentForm()
    
        # return a response
    return render(request, 'chipin/group_detail.html', {
        'group': group,
        'comments': comments,
        'events': events,
        'form': form,
        'comment_to_edit': comment_to_edit,
    })

@login_required
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user == group.admin:
        group.delete()
        messages.success(request, f'Group "{group.name}" has been deleted.')
    else:
        messages.error(request, "You do not have permission to delete this group.")
    return redirect('chipin:home')

@login_required
def invite_users(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    users_not_in_group = User.objects.exclude(id__in=group.members.values_list('id', flat=True))
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        invited_user = get_object_or_404(User, id=user_id)      
        if invited_user in group.invited_users.all():
            messages.info(request, f'{invited_user.profile.nickname} has already been invited.')
        else:
            group.invited_users.add(invited_user)
            messages.success(request, f'Invitation sent to {invited_user.profile.nickname}.')
        return redirect('chipin:group_detail', group_id=group.id)  
    return render(request, 'chipin/invite_users.html', {
        'group': group,
        'users_not_in_group': users_not_in_group
    })

@login_required
def accept_invite(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    user_id = request.GET.get('user_id')
    if user_id:
        invited_user = get_object_or_404(User, id=user_id)
        if invited_user in group.members.all():
            messages.info(request, f'{invited_user.profile.nickname} is already a member of the group "{group.name}".')
        elif invited_user in group.invited_users.all():
            group.members.add(invited_user)
            group.invited_users.remove(invited_user)  # Remove from invited list
            messages.success(request, f'{invited_user.profile.nickname} has successfully joined the group "{group.name}".')
        else:
            messages.error(request, "You are not invited to join this group.")
    else:
        messages.error(request, "Invalid invitation link.")  
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def request_to_join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if the user is already a member
    if request.user in group.members.all():
        messages.info(request, "You are already a member of this group.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Check if the user has already submitted a join request
    join_request, created = GroupJoinRequest.objects.get_or_create(user=request.user, group=group)
    if created:
        messages.success(request, "Your request to join the group has been submitted.")
    else:
        messages.info(request, "You have already requested to join this group.")
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def delete_join_request(request, request_id):
    join_request = get_object_or_404(GroupJoinRequest, id=request_id, user=request.user)
    # Ensure the logged-in user can only delete their own join requests
    if join_request.user == request.user:
        join_request.delete()
        messages.success(request, "Your join request has been successfully deleted.")
    else:
        messages.error(request, "You are not authorised to delete this join request.")
    return redirect('chipin:home')  
    
@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if the user is a member of the group
    if request.user in group.members.all():
        group.members.remove(request.user)  # Remove the user from the group
        messages.success(request, f'You have left the group {group.name}.')
    else:
        messages.error(request, 'You are not a member of this group.') 
    return redirect('chipin:home')

@login_required
def vote_on_join_request(request, group_id, request_id, vote):
    group = get_object_or_404(Group, id=group_id)
    join_request = get_object_or_404(GroupJoinRequest, id=request_id) 
    if request.user not in group.members.all():
        messages.error(request, "You must be a member of the group to vote.")
        return redirect('chipin:group_detail', group_id=group.id)  
    if request.user in join_request.votes.all():
        messages.info(request, "You have already voted.")
        return redirect('chipin:group_detail', group_id=group.id)
        
    # Register the user's vote
    join_request.votes.add(request.user)
    
    # Calculate if more than 60% of members have approved
    total_members = group.members.count()
    total_votes = join_request.votes.count() 
    if total_votes / total_members >= 0.6:
        join_request.is_approved = True
        group.members.add(join_request.user)  # Add the user to the group
        join_request.save()
        messages.success(request, f"{join_request.user.profile.nickname} has been approved to join the group!") 
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:  # Ensure only the comment author can edit
        return redirect('chipin:group_detail', group_id=comment.group.id)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('chipin:group_detail', group_id=comment.group.id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'chipin/edit_comment.html', {'form': form, 'comment': comment})

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user == request.user or request.user == comment.group.admin:  # Allow author or group admin to delete
        comment.delete()
    return redirect('chipin:group_detail', group_id=comment.group.id)

@login_required
def create_event(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.admin:
        messages.error(request, "Only the teacher can create assessments.")
        return redirect('chipin:group_detail', group_id=group.id)
    if request.method == 'POST':
        event_name = request.POST.get('name')
        event_date = request.POST.get('date')
        event_notification = request.FILES.get('notification', None)
        event = Event.objects.create(
            name=event_name,
            date=event_date,
            notification=event_notification,  # Django handles saving the file
            group=group
        )
        messages.success(request, f'Assessment "{event_name}" created successfully!')
        return redirect('chipin:group_detail', group_id=group.id)
    return render(request, 'chipin/create_event.html', {'group': group})

@login_required
def uploadfile(file, name):
    notifications_dir = os.path.join(settings.MEDIA_ROOT, "notifications")
    os.makedirs(notifications_dir, exist_ok=True)  # Ensure the directory exists

    # Build the full file path
    file_path = os.path.join(notifications_dir, name)

    # Save the uploaded file
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    return file_path
    

@login_required
def join_event(request, group_id, event_id):
    group = get_object_or_404(Group, id=group_id)
    event = get_object_or_404(Event, id=event_id, group=group)
    event_share = event.calculate_share()  
    # Check if the user is eligible to join based on their max spend
    if request.user.profile.max_spend < event_share:
        messages.error(request, f"Your max spend of ${request.user.profile.max_spend} is too low to join this event.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Check if the user has already joined the event
    if request.user in event.members.all():
        messages.info(request, "You have already joined this event.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Add the user to the event
    event.members.add(request.user)   
    messages.success(request, f"You have successfully joined the event '{event.name}'.")  
    # Optionally, update the event status if needed
    event.check_status()
    event.save()
    return redirect('chipin:group_detail', group_id=group.id)


@login_required
def update_event_status(request, group_id, event_id):
    group = get_object_or_404(Group, id=group_id)
    event = get_object_or_404(Event, id=event_id, group=group)
    # Ensure that only the group admin can update the event status
    if request.user != group.admin:
        messages.error(request, "Only the group administrator can update the event status.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Calculate the share per member
    event_share = event.calculate_share()
    # Check if all members can afford the event share
    sufficient_funds = True
    for member in group.members.all():
        if member.profile.max_spend < event_share:
            sufficient_funds = False
            break
    # Update the event status based on the members' ability to cover the share
    if sufficient_funds:
        event.status = "Active"
        messages.success(request, f"The event '{event.name}' is now Active. All members can cover the cost.")
    else:
        event.status = "Pending"
        messages.warning(request, f"The event '{event.name}' remains Pending. Some members cannot cover the cost.")
    # Save the updated event status
    event.save()
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def leave_event(request, group_id, event_id):
    group = get_object_or_404(Group, id=group_id)
    event = get_object_or_404(Event, id=event_id, group=group)
    # Check if the user is part of the event
    if request.user not in event.members.all():
        messages.error(request, "You are not a member of this event.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Remove the user from the event
    event.members.remove(request.user)
    messages.success(request, f"You have successfully left the event '{event.name}'.")
    # Optionally, check if the event status should be updated
    event.check_status()
    event.save()
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def delete_event(request, group_id, event_id):
    group = get_object_or_404(Group, id=group_id)
    event = get_object_or_404(Event, id=event_id, group=group)
    # Ensure only the group admin can delete the event
    if request.user != group.admin:
        messages.error(request, "Only the group administrator can delete events.")
        return redirect('chipin:group_detail', group_id=group.id)
    # Delete the event
    event.delete()
    messages.success(request, f"The event '{event.name}' has been deleted.")
    return redirect('chipin:group_detail', group_id=group.id)

@login_required
def create_lesson(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.admin:
        messages.error(request, "Only the teacher can create lessons.")
        return redirect('chipin:group_detail', group_id=group.id)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.group = group
            lesson.save()
            form.save_m2m()  # Save the many-to-many relationships
            messages.success(request, f'Lesson "{lesson.name}" created successfully!')
            return redirect('chipin:group_detail', group_id=group.id)
    else:
        form = LessonForm()

    return render(request, 'chipin/create_lesson.html', {'group': group})

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    submissions = lesson.submissions.all()

    if request.method == 'POST' and request.user != lesson.group.admin:
        form = StudentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.lesson = lesson
            submission.student = request.user
            submission.save()
            form.save_m2m()
            messages.success(request, "Your files have been uploaded successfully!")
            return redirect('chipin:lesson_detail', lesson_id=lesson.id)
    else:
        form = StudentSubmissionForm()

    return render(request, 'chipin/lesson_detail.html', {
        'lesson': lesson,
        'form': form,
        'submissions': submissions,
    })

@login_required
def submit_assessment(request, group_id, assessment_id):
    group = get_object_or_404(Group, id=group_id)
    assessment = get_object_or_404(Event, id=assessment_id, group=group)
    submissions = assessment.submissions.filter(assessment=assessment)

    if request.method == 'POST' and request.user != group.admin:
        form = AssessmentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assessment = assessment
            submission.student = request.user
            submission.save()
            form.save_m2m()
            messages.success(request, "Your assessment has been submitted successfully!")
            return redirect('chipin:submit_assessment', group_id=group.id, assessment_id=assessment.id)
    else:
        form = AssessmentSubmissionForm()

    return render(request, 'chipin/submit_assessment.html', {
        'group': group,
        'assessment': assessment,
        'form': form,
        'submissions': submissions,
    })

@login_required
def assessment_detail(request, group_id, assessment_id):
    group = get_object_or_404(Group, id=group_id)
    assessment = get_object_or_404(Event, id=assessment_id, group=group)
    submissions = assessment.submissions.all()

    if request.method == 'POST' and request.user == group.admin:
        submission_id = request.POST.get('submission_id')
        submission = get_object_or_404(AssessmentSubmission, id=submission_id)
        feedback_form = AssessmentFeedbackForm(request.POST, instance=submission)
        if feedback_form.is_valid():
            feedback_form.save()
            messages.success(request, "Feedback has been saved successfully!")
            return redirect('chipin:assessment_detail', group_id=group.id, assessment_id=assessment.id)
    else:
        feedback_form = AssessmentFeedbackForm()

    return render(request, 'chipin/assessment_detail.html', {
        'group': group,
        'assessment': assessment,
        'submissions': submissions,
        'feedback_form': feedback_form,
    })