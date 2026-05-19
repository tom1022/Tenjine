import logging
from functools import wraps
from flask import abort
from flask_login import current_user

logger = logging.getLogger(__name__)


def owner_or_admin_required(param='id'):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            study_id = kwargs.get(param)
            if study_id not in [x.id for x in current_user.studies] \
                    and not current_user.has_role('Admin'):
                logger.warning("Access denied: user %s → study %s", current_user.id, study_id)
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
