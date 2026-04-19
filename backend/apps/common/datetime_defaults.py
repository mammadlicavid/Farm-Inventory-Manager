from django.utils import timezone


def current_local_time():
    return timezone.localtime().time().replace(second=0, microsecond=0)
