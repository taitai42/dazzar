import re
import pytz

# Regex to validate a user nickname
valid_nick_re = re.compile('^(?=.{3,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$')


def validate_nickname(nickname):
    """Validate the nickname entered.

    Args:
        nickname: value to test
    Returns:
        None if validated, a string to describe the error otherwise.
    """

    if len(nickname) <= 2:
        return "Pseudo trop court."

    if len(nickname) >= 20:
        return "Pseudo trop long."

    if valid_nick_re.match(nickname):
        return None
    else:
        return "Pseudo non valide, seuls sont autorisés les caractères alphanumériques ainsi que '_' et '.'."


def _jinja2_filter_french_date(date, date_format='%d %B - %H:%M:%S'):
    """Helpers to format a date with the Paris timezone.

    Args:
        date: Date to format.
        date_format: Date format to use
    Returns:
        A string representing the date with Paris timezone.
    """
    tz = pytz.timezone('Europe/Paris')
    localized_date = pytz.timezone('UTC').localize(date).astimezone(tz)
    return localized_date.strftime(date_format)
