from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import ChatMessage, ConnectionRequest
from user.models import Profile
from django.db.models import Q
from user.views import upload_to_supabase
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib import messages
from django.db import models
from django.template.loader import render_to_string
import os
# Custom User model
User = get_user_model()

MAX_FILE_SIZE_MB = 25
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}


def _validate_attachment(f):
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
def chat_view(request, chat_with=None):
    """
    Renders main chat UI. Loads sidebar + optionally the selected chat's recent messages.
    """
    # 1) active connections
    connections = ConnectionRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        is_accepted=True,
        connection_active=True
    )

    connected_user_ids = {
        (conn.receiver.id if conn.sender == request.user else conn.sender.id)
        for conn in connections
    }

    chat_users = User.objects.filter(id__in=connected_user_ids)

    selected_user = None
    messages = []

    if chat_with:
        selected_user = get_object_or_404(User, id=chat_with)
        if selected_user.id not in connected_user_ids:
            return render(request, 'user/chat/not_connected.html', {
                'selected_user': selected_user,
                'reason': "You must be connected to this user before chatting."
            })

        # Load last 100 messages for initial render (chronological)
        qs = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=selected_user) |
            Q(sender=selected_user, receiver=request.user)
        ).order_by('-id')[:100]
        messages = list(reversed(qs))

    # profiles for sidebar (get_or_create in case)
    user_profiles = {
        u.id: Profile.objects.get_or_create(user=u)[0]
        for u in chat_users
    }

    return render(request, 'user/chat/maininterface.html', {
        'chat_users': chat_users,
        'user_profiles': user_profiles,
        'selected_user': selected_user,
        'messages': messages,
        'selected_user_id': int(chat_with) if chat_with else None
    })


@login_required
def send_message(request):
    """
    POST receiver_id, message (optional), attachment (optional)
    Returns JSON { ok: True, id:..., html: "<rendered msg partial>" }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    receiver_id = request.POST.get("receiver_id")
    if not receiver_id:
        return HttpResponseBadRequest("Missing receiver_id")
    receiver = get_object_or_404(User, id=receiver_id)

    text = request.POST.get("message", "").strip()
    attachment = request.FILES.get("attachment")
    if attachment:
        attachment = upload_to_supabase(attachment)
        print(attachment)
    if not text and not attachment:
        return HttpResponseBadRequest("Empty message")

    ok, err = _validate_attachment(attachment)
    if not ok:
        return HttpResponseBadRequest(err)

    # If model has FileField 'attachment', store it directly; otherwise save to storage and use URL
    # Here we assume ChatMessage.attachment exists (recommended). If you kept file_url, see note below.
    msg = ChatMessage.objects.create(
        sender=request.user,
        receiver=receiver,
        message=text or None,
        file_url=attachment or None,
        timestamp=timezone.now()
    )

    html = render_to_string("user/partials/_message.html", {"msg": msg, "request": request})
    return JsonResponse({"ok": True, "id": msg.id, "html": html})

@login_required
def fetch_messages(request, user_id):
    """
    GET ?after=<last_id> → messages with id > last_id (new)
    GET ?before=<first_id> → previous messages with id < first_id (older)
    default (no param) → last 50 messages
    """
    other = get_object_or_404(User, id=user_id)

    try:
        after = int(request.GET.get("after", 0))
    except (ValueError, TypeError):
        after = 0
    try:
        before = int(request.GET.get("before", 0))
    except (ValueError, TypeError):
        before = 0

    base_q = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other) |
        Q(sender=other, receiver=request.user)
    )

    has_more = False  # default

    if after:
        qs = base_q.filter(id__gt=after).order_by("id")
    elif before:
        qs = base_q.filter(id__lt=before).order_by("-id")[:30]
        has_more = base_q.filter(id__lt=before).exists()  # ✅ check if there are older ones left
        qs = list(reversed(qs))
    else:
        qs = base_q.order_by("-id")[:50]
        has_more = base_q.count() > 50  # ✅ check if more history exists
        qs = list(reversed(qs))

    html = render_to_string("user/partials/_messages.html", {"messages": qs, "request": request})
    return JsonResponse({"ok": True, "html": html, "has_more": has_more})


@login_required
def mark_read(request):
    """
    POST: chat_with, last_id -> marks messages from chat_with -> request.user up to last_id as read
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")
    other_id = request.POST.get("chat_with")
    last_id = request.POST.get("last_id")
    if not other_id or not last_id:
        return HttpResponseBadRequest("Missing params")

    other = get_object_or_404(User, id=other_id)
    try:
        last_id = int(last_id)
    except ValueError:
        return HttpResponseBadRequest("Invalid last_id")

    # This requires ChatMessage.read_at field (see model recommendation)
    ChatMessage.objects.filter(
        sender=other,
        receiver=request.user,
        id__lte=last_id,
        read_at__isnull=True
    ).update(read_at=timezone.now())

    return JsonResponse({"ok": True})

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