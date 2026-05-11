from django import template

register = template.Library()


@register.filter
def get_notif(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    return False