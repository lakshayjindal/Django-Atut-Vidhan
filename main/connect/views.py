from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib import messages
from django.template.loader import render_to_string
import os

from .models import ChatMessage, ConnectionRequest
from user.models import Profile
from user.views import upload_to_supabase

User = get_user_model()

MAX_FILE_SIZE_MB = 25
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}


def _validate_attachment(f):
    """
    Validate uploaded attachment.

    Args:
        f (UploadedFile): The file object.

    Returns:
        tuple[bool, str | None]: (True, None) if valid, 
                                 (False, "reason") if invalid.
    """
    if not f:
        return True, None

    ext = os.path.splitext(f.name.lower())[1]
    if ext not in ALLOWED_EXT:
        return False, "Unsupported file type"
    if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, "File too large"

    return True, None


@login_required
def chat_view(request, chat_with=None):
    """
    Render main chat interface with sidebar and (optionally) a selected chat.

    Args:
        request (HttpRequest): Current request object.
        chat_with (int, optional): ID of the user to chat with.

    Returns:
        HttpResponse: Rendered chat page.
    """
    # Active connections for sidebar
    connections = ConnectionRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        is_accepted=True,
        connection_active=True
    )

    connected_user_ids = {
        conn.receiver_id if conn.sender == request.user else conn.sender_id
        for conn in connections
    }
    chat_users = User.objects.filter(id__in=connected_user_ids)

    selected_user, messages = None, []

    if chat_with:
        selected_user = get_object_or_404(User, id=chat_with)
        if selected_user.id not in connected_user_ids:
            return render(request, "user/chat/not_connected.html", {
                "selected_user": selected_user,
                "reason": "You must be connected to this user before chatting."
            })

        # Last 100 messages, chronological
        qs = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=selected_user) |
            Q(sender=selected_user, receiver=request.user)
        ).order_by("-id")[:100]
        messages = list(reversed(qs))

    # Sidebar profiles (get_or_create for safety)
    user_profiles = {
        u.id: Profile.objects.get_or_create(user=u)[0] for u in chat_users
    }

    return render(request, "user/chat/maininterface.html", {
        "chat_users": chat_users,
        "user_profiles": user_profiles,
        "selected_user": selected_user,
        "messages": messages,
        "selected_user_id": int(chat_with) if chat_with else None
    })


@login_required
def send_message(request):
    """
    Send a new chat message with optional attachment.

    POST Params:
        - receiver_id (int)
        - message (str, optional)
        - attachment (file, optional)

    Returns:
        JsonResponse: { ok: True, id: int, html: str }
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

    if not text and not attachment:
        return HttpResponseBadRequest("Empty message")

    ok, err = _validate_attachment(attachment)
    if not ok:
        return HttpResponseBadRequest(err)

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
    Fetch chat messages with pagination.

    GET Params:
        - after (int, optional): Get messages with id > after.
        - before (int, optional): Get messages with id < before.
        - none: Last 50 messages.

    Returns:
        JsonResponse: { ok: True, html: str, has_more: bool }
    """
    other = get_object_or_404(User, id=user_id)

    after = request.GET.get("after")
    before = request.GET.get("before")

    try:
        after = int(after) if after else 0
    except ValueError:
        after = 0
    try:
        before = int(before) if before else 0
    except ValueError:
        before = 0

    base_q = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other) |
        Q(sender=other, receiver=request.user)
    )

    has_more, qs = False, []

    if after:
        qs = base_q.filter(id__gt=after).order_by("id")
    elif before:
        qs = base_q.filter(id__lt=before).order_by("-id")[:30]
        has_more = base_q.filter(id__lt=before).exists()
        qs = list(reversed(qs))
    else:
        qs = base_q.order_by("-id")[:50]
        has_more = base_q.count() > 50
        qs = list(reversed(qs))

    html = render_to_string("user/partials/_messages.html", {"messages": qs, "request": request})
    return JsonResponse({"ok": True, "html": html, "has_more": has_more})


@login_required
def mark_read(request):
    """
    Mark messages from a specific user as read.

    POST Params:
        - chat_with (int): ID of the user whose messages to mark as read.
        - last_id (int): Mark all messages up to this ID as read.

    Returns:
        JsonResponse: { ok: True }
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

    ChatMessage.objects.filter(
        sender=other,
        receiver=request.user,
        id__lte=last_id,
        read_at__isnull=True
    ).update(read_at=timezone.now())

    return JsonResponse({"ok": True})


def are_connected(user1, user2):
    """
    Check if two users are connected.

    Args:
        user1 (User): First user.
        user2 (User): Second user.

    Returns:
        bool: True if connected, else False.
    """
    return ConnectionRequest.objects.filter(
        (Q(sender=user1, receiver=user2) | Q(sender=user2, receiver=user1)),
        is_accepted=True
    ).exists()


@login_required
def connections_page(request):
    """
    Display all connection requests.

    Args:
        request (HttpRequest): Current request.

    Returns:
        HttpResponse: Rendered connections page.
    """
    received_requests = ConnectionRequest.objects.filter(receiver=request.user, is_accepted=False)
    sent_requests = ConnectionRequest.objects.filter(sender=request.user)

    return render(request, "user/connections.html", {
        "received_requests": received_requests,
        "sent_requests": sent_requests
    })


@require_POST
@login_required
def accept_request(request, request_id):
    """
    Accept a pending connection request.

    Args:
        request (HttpRequest): Current request.
        request_id (int): ID of the request to accept.

    Returns:
        JsonResponse: { success: True } on success.
    """
    conn_request = get_object_or_404(ConnectionRequest, id=request_id, receiver=request.user)

    if conn_request.is_accepted:
        return JsonResponse({"error": "Already accepted"}, status=400)

    conn_request.is_accepted = True
    conn_request.connection_active = True
    conn_request.save()

    # Real-time notification to sender
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{conn_request.sender.id}",
        {
            "type": "send_notification",
            "content": {
                "type": "connection_accepted",
                "request_id": conn_request.id,
                "receiver_id": request.user.id,
                "receiver_name": request.user.get_full_name(),
                "chat_url": reverse("chat", args=[request.user.id]),
            }
        }
    )
    return JsonResponse({"success": True})


@require_POST
@login_required
def cancel_request(request, request_id):
    """
    Cancel a sent connection request.

    Args:
        request (HttpRequest): Current request.
        request_id (int): ID of the request to cancel.

    Returns:
        JsonResponse: { success: True, message: str } on success.
    """
    connection_request = get_object_or_404(ConnectionRequest, id=request_id)

    if connection_request.sender != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if connection_request.is_accepted:
        return JsonResponse({"error": "Request already accepted"}, status=400)

    connection_request.delete()
    return JsonResponse({"success": True, "message": "Request canceled"})


@login_required
def send_request(request, receiver_id):
    """
    Send a new connection request to another user.

    Args:
        request (HttpRequest): Current request.
        receiver_id (int): ID of the target user.

    Returns:
        HttpResponseRedirect: Redirect to dashboard with messages.
    """
    receiver = get_object_or_404(User, id=receiver_id)

    if receiver == request.user:
        messages.error(request, "You cannot send a request to yourself.")
        return redirect("dashboard")

    connection_request, created = ConnectionRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver
    )

    if created:
        messages.success(request, f"Connection request sent to {receiver.username}!")
    else:
        messages.warning(request, f"You have already sent a connection request to {receiver.username}.")

    return redirect("user_dashboard")
