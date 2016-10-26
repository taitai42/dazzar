import re

# Regex to validate a user nickname
valid_nick_re = re.compile('^(?=.{3,20}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$')


def validate_nickname(nickname):
    """ Validate the nickname entered.

    Arguments:
        nickname - value to test
    Return:
        None if validated, a string to describe the error otherwise
    """

    if len(nickname) <= 2:
        return "Pseudo trop court."

    if len(nickname) >= 20:
        return "Pseudo trop long."

    if valid_nick_re.match(nickname):
        return None
    else:
        return "Pseudo non valide, seuls sont autorisés les caractères alphanumériques ainsi que '_' et '.'."
