from rest_framework.views import APIView
from rest_framework.response import Response

class StandardResponseView(APIView):
    default_success_messages = {
        "GET": "Fetched successfully",
        "POST": "Created successfully",
        "PUT": "Updated successfully",
        "PATCH": "Updated successfully",
        "DELETE": "Deleted successfully",
    }

    def get_success_message(self, request):
        return getattr(self, "success_message", self.default_success_messages.get(request.method, "Success"))

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(response.data, dict) and {"status", "message", "data"} <= response.data.keys():
            return super().finalize_response(request, response, *args, **kwargs)

        # message = self.get_success_message(request) if response.status_code < 400 else response.data.get("detail","Error")
        message = self.get_success_message(request) if response.status_code < 400 else None
        print(message)
        response.data = {
            "status": response.status_code < 400,
            "message": message,
            "data": response.data,
        }

        return super().finalize_response(request, response, *args, **kwargs)
