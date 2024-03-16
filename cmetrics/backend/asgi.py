import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from cmetrics.backend import urls

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cmetrics.backend.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # "websocket": AllowedHostsOriginValidator(
        #     AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        # ),
        "websocket": URLRouter(urls.websocket_urlpatterns),
    }
)
