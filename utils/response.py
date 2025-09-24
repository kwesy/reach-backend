from rest_framework.response import Response

def standard_response(data=None, message="Success", status=True, status_code=200):
    return Response({
        "status": status,
        "message": message,
        "data": data
    }, status=status_code)
