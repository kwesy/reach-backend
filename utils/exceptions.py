from rest_framework.views import exception_handler
from utils.response import standard_response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    print(f"Exception: {exc}, Context: {context}")

    if response is not None:
        data = response.data

        if isinstance(data, dict):
            # If 'detail' exists, use it directly
            if 'detail' in data:
                message = data['detail']
            else:
                # Flatten first error field into a readable message
                first_field = next(iter(data))
                errors = data[first_field]
                if isinstance(errors, list) and errors:
                    message = f"{first_field}: {errors[0]}"
                else:
                    message = str(errors)
        else:
            message = "An error occurred"

        return standard_response(
            data=None,
            message=message,
            status=False,
            status_code=response.status_code
        )

    # Unhandled exceptions (non-DRF)
    print(f"Unhandled exception: {exc}")
    return standard_response(
        data=None,
        message="Internal server error",
        status=False,
        status_code=500
    )
