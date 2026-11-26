from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(*a, **kw):
            if current_user.role not in roles:
                abort(403)
            return f(*a, **kw)

        return wrapper

    return deco
