def get_response():
    return {"result": 42}  # BUG: JS frontend expects key "data", not "result"
