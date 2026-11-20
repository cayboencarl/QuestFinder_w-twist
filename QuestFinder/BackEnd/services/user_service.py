def validate_registration(data):
    errors = []

    for field in ["name", "address", "username", "email", "password"]:
        if not data.get(field):
            errors.append(f"{field} is required")

    try:
        age = int(data.get("age"))
    except(TypeError, ValueError):
            errors.append("age must be a whole number")
    else:
        if age < 0 or age > 120:
            errors.append("age must be between 0 and 120")

    if data.get("password") and len(data["password"]) < 8:
        errors.append("password must be at least 8 characters")
    

    if not (data.get("is_client") or data.get("is_worker")):
        errors.append("account must be a client, a worker, or both")

    if data.get("email") and ("@" not in data["email"] or "." not in data["email"].split("@")[-1]):
        errors.append("email must be a valid address, like name@example.com")






    return errors