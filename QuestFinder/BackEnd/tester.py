from services.user_service import validate_registration

bad = {"name": "", "age": "abc", "password": "short"}
print(validate_registration(bad))

good = {
    "name": "Carl",
    "age": "San Vicente",
    "username": "carl",
    "email": "carl@test.com",
    "password": "secret123",
}
print(validate_registration(good))