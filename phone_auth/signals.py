from django.dispatch import Signal

user_avatar_changed = Signal(providing_args=["user"])
