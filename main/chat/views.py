from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import ChatMessage, ConnectionRequest
from user.models import Profile
from django.db.models import Q
from django.views.decorators.http import require_POST

# Custom User model
User = get_user_model()


@login_required
def chat_view(request, chat_with=None):
    chat_users_ids = ChatMessage.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values_list('sender', 'receiver')

    user_ids = set()
    for sender_id, receiver_id in chat_users_ids:
        if sender_id != request.user.id:
            user_ids.add(sender_id)
        if receiver_id != request.user.id:
            user_ids.add(receiver_id)

    chat_users = User.objects.filter(id__in=user_ids)

    selected_user = None
    selected_user_profile = None
    messages = []

    if chat_with:
        selected_user = get_object_or_404(User, id=chat_with)

        # 🔒 Block chat unless connected
        if not are_connected(request.user, selected_user):
            return render(request, 'user/chat/not_connected.html', {
                'selected_user': selected_user,
                'reason': "You must be connected to this user before chatting."
            })

        selected_user_profile = selected_user.profile
        messages = ChatMessage.objects.filter(
            sender__in=[request.user, selected_user],
            receiver__in=[request.user, selected_user]
        ).order_by('timestamp')

    user_profiles = {
        user.id: Profile.objects.get_or_create(user=user)[0]
        for user in chat_users
    }

    context = {
        'chat_users': chat_users,
        'user_profiles': user_profiles,
        'selected_user': selected_user,
        'selected_user_profile': selected_user_profile,
        'messages': messages,
        'selected_user_id': int(chat_with) if chat_with else None
    }

    return render(request, 'user/chat/maininterface.html', context)


@login_required
def send_message(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        receiver_id = request.POST.get('receiver_id')
        receiver = get_object_or_404(User, id=receiver_id)

        if message and receiver:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                message=message,
                timestamp=timezone.now()
            )
            return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def fetch_messages(request):
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        receiver = get_object_or_404(User, id=receiver_id)

        messages = ChatMessage.objects.filter(
            sender__in=[request.user, receiver],
            receiver__in=[request.user, receiver]
        ).order_by('timestamp')

        html = ''
        for msg in messages:
            css_class = 'sent' if msg.sender == request.user else 'received'
            html += f'<div class="message {css_class}">{msg.message.replace(chr(10), "<br>")}</div>'

        return JsonResponse(html, safe=False)

    return JsonResponse({'status': 'error'}, status=400)

def are_connected(user1, user2):
    return ConnectionRequest.objects.filter(
        ((models.Q(from_user=user1) & models.Q(to_user=user2)) |
         (models.Q(from_user=user2) & models.Q(to_user=user1))),
        is_accepted=True
    ).exists()


@login_required
def connections_page(request):
    received_requests = ConnectionRequest.objects.filter(to_user=request.user, is_accepted=False)
    sent_requests = ConnectionRequest.objects.filter(from_user=request.user)
    return render(request, 'user/connections.html', {'received_requests': received_requests, 'sent_requests': sent_requests})

@require_POST
@login_required
def accept_request(request, request_id):
    conn_request = get_object_or_404(ConnectionRequest, id=request_id, to_user=request.user)

    if conn_request.is_accepted:
        return JsonResponse({'error': 'This request has already been accepted.'}, status=400)

    conn_request.is_accepted = True
    conn_request.save()

    return JsonResponse({'success': True, 'message': 'Request accepted.'})

@require_POST
@login_required
def cancel_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id)

    if connection_request.from_user != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if connection_request.is_accepted:
        return JsonResponse({'error': 'Request already accepted'}, status=400)

    connection_request.delete()
    return JsonResponse({'success': True, 'message': 'Request canceled'})