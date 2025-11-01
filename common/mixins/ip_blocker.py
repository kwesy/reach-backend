from rest_framework.exceptions import PermissionDenied
from ipware import get_client_ip

class IPBlockerMixin:
    """
    A DRF mixin for IP whitelisting and blacklisting.
    Add this mixin to any APIView or ViewSet to restrict access based on client IP.
    """

    # Optional: set these in your subclass or from settings
    WHITELIST_IPS = []  # e.g., ["192.168.1.10", "10.0.0.0/24"]
    BLACKLIST_IPS = []  # e.g., ["203.0.113.15"]
    ENFORCE_WHITELIST = True  # If True, only allow IPs in whitelist

    def initial(self, request, *args, **kwargs):
        client_ip, is_routable = get_client_ip(request)

        if not client_ip:
            raise PermissionDenied({"detail":"Unathorized"})

        # --- Blacklist logic ---
        if client_ip in self.BLACKLIST_IPS:
            raise PermissionDenied({"detail":"Unathorized"})

        # --- Whitelist logic ---
        if self.ENFORCE_WHITELIST and self.WHITELIST_IPS:
            if client_ip not in self.WHITELIST_IPS:
                raise PermissionDenied({"detail":"Unathorized"})

        # Proceed normally
        return super().initial(request, *args, **kwargs)
