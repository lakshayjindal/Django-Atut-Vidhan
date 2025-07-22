from django.db import models
from user.models import User

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'From {self.sender} to {self.receiver}: {self.message[:20]}...'

class ConnectionRequest(models.Model):
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ('from_user', 'to_user')
    def __str__(self):
        return f"{self.to_user} to {self.from_user}: {self.timestamp[:20]}..."