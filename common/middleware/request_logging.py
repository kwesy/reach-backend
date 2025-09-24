import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import QueryDict

logger = logging.getLogger("request_logger")

REDACT_HEADERS = {'authorization', 'cookie', 'set-cookie'}
REDACT_FIELDS = {'password', 'token', 'secret', 'file'}

def flatten_querydict(qdict):
    return {
        k: v[0] if isinstance(v, list) and len(v) == 1 else v
        for k, v in qdict.lists()
    }

class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()
        request._logged_data = {}

        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ""
            request._logged_data['content_type'] = content_type

            try:
                if 'application/json' in content_type:
                    request._logged_data['body'] = json.loads(request.body)
                elif 'application/x-www-form-urlencoded' in content_type:
                    request._logged_data['body'] = flatten_querydict(request.POST)
                elif 'multipart/form-data' in content_type:
                    form = flatten_querydict(request.POST)
                    for k in request.FILES:
                        form[k] = '[Uploaded File]'
                    request._logged_data['body'] = form
            except Exception:
                request._logged_data['body'] = '[Unreadable]'

    
    def process_response(self, request, response):
        duration = time.time() - getattr(request, '_start_time', time.time())
        user = getattr(request, 'user', None)
        ip = self.get_client_ip(request)

        log_parts = [
            f"{request.method} {request.get_full_path()}",
            f"Status: {response.status_code}",
            f"User: {user if user and user.is_authenticated else 'Anonymous'}",
            f"IP: {ip}",
            f"Duration: {duration:.3f}s",
        ]

        # Add headers
        headers = {}
        for k, v in request.headers.items():
            headers[k] = "[REDACTED]" if k.lower() in REDACT_HEADERS else v
        log_parts.append(f"Headers: {json.dumps(headers)}")

        # Add body
        if hasattr(request, "_logged_data"):
            body = request._logged_data.get('body')
            if isinstance(body, dict):
                safe_body = {
                    k: ("[REDACTED]" if k.lower() in REDACT_FIELDS else v)
                    for k, v in body.items()
                }
                log_parts.append(f"Body: {json.dumps(safe_body, default=str)}")
            else:
                log_parts.append(f"Body: {body}")

        logger.info(" | ".join(log_parts))
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
