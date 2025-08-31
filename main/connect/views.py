from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import ChatMessage as Message, ConnectionRequest
from user.models import Profile
from django.db.models import Q
from user.views import upload_to_supabase
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib import messages
from django.db import models
from django.template.loader import render_to_string
# Custom User model
User = get_user_model()

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import ChatMessage, ConnectionRequest
from user.models import User, Profile  # Assuming Profile is here

@login_required
def chat_view(request, chat_with=None):
    # ✅ 1. Get all actively connected users (either sender or receiver)
    connections = ConnectionRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        is_accepted=True,
        connection_active=True
    )

    connected_user_ids = set()
    for conn in connections:
        if conn.sender == request.user:
            connected_user_ids.add(conn.receiver.id)
        else:
            connected_user_ids.add(conn.sender.id)

    chat_users = User.objects.filter(id__in=connected_user_ids)

    # 🧠 Initialize variables
    selected_user = None
    selected_user_profile = None
    messages = []

    # ✅ 2. If user selects someone to chat with
    if chat_with:
        selected_user = get_object_or_404(User, id=chat_with)

        # 🔒 Check that selected_user is actually connected
        if selected_user.id not in connected_user_ids:
            return render(request, 'user/chat/not_connected.html', {
                'selected_user': selected_user,
                'reason': "You must be connected to this user before chatting."
            })

        # 📨 Fetch messages between the two users
        messages = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=selected_user) |
            Q(sender=selected_user, receiver=request.user)
        ).order_by('timestamp')

        selected_user_profile = selected_user.profile  # Assuming related_name='profile'

    # ✅ 3. Get profiles for chat user sidebar
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




MAX_FILE_SIZE_MB = 25
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}


def _validate_attachment(f):
    import os
    if not f:
        return True, None
    name = f.name.lower()
    ext = os.path.splitext(name)[1]
    if ext not in ALLOWED_EXT:
        return False, "Unsupported file type"
    if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, "File too large"
    return True, None


@login_required
def send_message(request):
    """
    Accepts POST with receiver_id, message (optional), attachment (optional).
    If request is AJAX (fetch), return JSON: { ok: True, id: <id>, html: "<rendered partial>" }
    Otherwise return rendered partial for HTMX.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    receiver_id = request.POST.get("receiver_id")
    if not receiver_id:
        return HttpResponseBadRequest("Missing receiver_id")

    receiver = get_object_or_404(User, id=receiver_id)
    text = request.POST.get("message", "").strip()
    attachment = request.FILES.get("attachment")

    # ensure not empty
    if not text and not attachment:
        return HttpResponseBadRequest("Empty message")

    # validate file
    ok, err = _validate_attachment(attachment)
    if not ok:
        return HttpResponseBadRequest(err)

    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        message=text if text else None,
        file_url=attachment if attachment else None,
        timestamp=timezone.now()
    )

    # render partial
    html = render_to_string("user/partials/_message.html", {"msg": msg, "request": request})

    # If this is an HTMX request, return the partial directly
    if request.headers.get("HX-Request") == "true":
        return render(request, "user/partials/_message.html", {"msg": msg})

    # else return JSON (for our fetch flow)
    return JsonResponse({"ok": True, "id": msg.id, "html": html})


@login_required
def fetch_messages(request, user_id):
    """
    Expects GET param last_id (int). Returns only messages with id > last_id
    Renders _messages.html which loops through messages partials
    """
    try:
        last_id = int(request.GET.get("last_id", 0))
    except (ValueError, TypeError):
        last_id = 0

    other = get_object_or_404(User, id=user_id)

    msgs = Message.objects.filter(
        Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user),
        id__gt=last_id
    ).order_by("id")

    # If AJAX/JSON wanted:
    if request.headers.get("HX-Request") != "true" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string("user/partials/_messages.html", {"messages": msgs, "request": request})
        return JsonResponse({"ok": True, "html": html})

    # Default: return HTMX partial (works if you keep hx-get)
    return render(request, "user/partials/_messages.html", {"messages": msgs})
def are_connected(user1, user2):
    return ConnectionRequest.objects.filter(
        ((models.Q(sender=user1) & models.Q(receiver=user2)) |
         (models.Q(sender=user2) & models.Q(receiver=user1))),
        is_accepted=True
    ).exists()


@login_required
def connections_page(request):
    received_requests = ConnectionRequest.objects.filter(receiver=request.user, is_accepted=False)
    sent_requests = ConnectionRequest.objects.filter(sender=request.user)
    return render(request, 'user/connections.html', {'received_requests': received_requests, 'sent_requests': sent_requests})

@require_POST
@login_required
def accept_request(request, request_id):
    conn_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)

    if conn_request.is_accepted:
        return JsonResponse({'error': 'Already accepted'}, status=400)

    conn_request.is_accepted = True
    conn_request.connection_active = True
    conn_request.save()

    # Real-time notify the sender
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{conn_request.sender.id}',
        {
            'type': 'send_notification',
            'content': {
                'type': 'connection_accepted',
                'request_id': conn_request.id,
                'receiver_id': request.user.id,
                'receiver_name': request.user.get_full_name(),
                'chat_url': reverse('chat', args=[request.user.id]),
            }
        }
    )

    return JsonResponse({'success': True})

@require_POST
@login_required
def cancel_request(request, request_id):
    connection_request = get_object_or_404(ConnectionRequest, id=request_id)

    if connection_request.sender != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if connection_request.is_accepted:
        return JsonResponse({'error': 'Request already accepted'}, status=400)

    connection_request.delete()
    return JsonResponse({'success': True, 'message': 'Request canceled'})

def send_request(request, receiver_id):
    receiver = get_object_or_404(User, id=receiver_id)

    if receiver == request.user:
        messages.error(request, "You cannot send a request to yourself.")
        return redirect('dashboard')

    connection_request, created = ConnectionRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver
    )

    if created:
        messages.success(request, f"Connection request sent to {receiver.username}!")
    else:
        messages.warning(request, f"You have already sent a connection request to {receiver.username}.")

    return redirect('user_dashboard')

# def block_user(request, user_id):
#     user = request.user
#     to_block_user = get_object_or_404(User, id=user_id)
#     connection = get_object_or_404(ConnectionRequest, q(receiver == user and sender == to_block_user) )