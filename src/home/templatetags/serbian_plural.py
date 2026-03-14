from django import template

register = template.Library()


@register.filter
def sr_plural(n, forms):
    """
    Usage:
    {{ number|sr_plural:"korisnik,korisnika,korisnika" }}
    """

    n = int(n)
    form1, form2, form3 = forms.split(",")

    if n % 10 == 1 and n % 100 != 11:
        return form1
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return form2
    else:
        return form3
