# tests/test_ipblocker.py
import pytest
from django.urls import path
from rest_framework.test import APIClient
import logging

logger = logging.getLogger("error")

# View
# main/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from common.mixins.ip_blocker import IPBlockerMixin

class ProtectedViewExample(IPBlockerMixin, APIView):
    WHITELIST_IPS = ["192.168.1.100"]
    BLACKLIST_IPS = ["10.0.0.5"]

    def get(self, request):
        return Response({"status": "ok"})

# =================================================================

urlpatterns = [
    path("protected/", ProtectedViewExample.as_view(), name="protected"),
]

@pytest.fixture(autouse=True)
def override_urls(settings):
    """Temporarily register test route for our view."""
    settings.ROOT_URLCONF = __name__

@pytest.fixture
def client():
    return APIClient()

def test_whitelisted_ip_allowed(client):
    """Should allow access from whitelisted IP."""
    response = client.get("/protected/", REMOTE_ADDR="192.168.1.100")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_blacklisted_ip_denied(client):
    """Should deny access from explicitly blacklisted IP."""
    response = client.get("/protected/", REMOTE_ADDR="10.0.0.5")
    logger.info(response.json())
    assert response.status_code == 403
    assert "unathorized" in response.json()["message"].lower()

def test_non_whitelisted_ip_denied(client):
    """Should deny non-whitelisted IPs when enforcement is on."""
    response = client.get("/protected/", REMOTE_ADDR="203.0.113.10")
    assert response.status_code == 403
    assert "unathorized" in response.json()["message"].lower()

def test_missing_ip_denied(client, monkeypatch):
    """Should deny if IP cannot be determined."""
    import common.mixins.ip_blocker as ipblockermixin

    monkeypatch.setattr(ipblockermixin, "get_client_ip", lambda request: (None, False)) # it replaces the get_client_ip() function inside common.mixins with a fake lambda that always returns (None, False).
    response = client.get("/protected/")
    assert response.status_code == 403
    assert "unathorized" in response.json()["message"].lower()
