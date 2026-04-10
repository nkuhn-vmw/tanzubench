def greet(request):
    # Bug: crashes if 'user' is missing from request.
    return f"Hello, {request['user'].upper()}!"
