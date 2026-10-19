"""
Middleware: устанавливает язык из User.preferred_language.
Должен идти ПОСЛЕ LocaleMiddleware, чтобы переопределить его.
"""
from django.utils import translation


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            lang = getattr(request.user, "preferred_language", None)
            if lang:
                translation.activate(lang)
                request.LANGUAGE_CODE = lang
        return self.get_response(request)