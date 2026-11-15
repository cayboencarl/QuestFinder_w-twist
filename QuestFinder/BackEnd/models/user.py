#Imports the SqlAlchemy from database.py
from database import db
#Imports current Date and provide timestamp
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

class User (db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    age = db.Column(db.Integer, nullable = False)
    address = db.Column(db.String(255), nullable = False)
    username = db.Column(db.String(255), unique = True, nullable = False)
    email = db.Column(db.String(100), unique=True, nullable = False)
    password_hash = db.Column(db.String(255), nullable = False)
    is_client = db.Column(db.Boolean, nullable = False, default = False)
    is_worker = db.Column(db.Boolean, nullable = False, default = False)
    is_admin = db.Column(db.Boolean, nullable = False, default = False)

    # verification_status (unverified / approved / rejected)
    verification_status = db.Column(
        db.String(30), 
        nullable = False, 
        default = 'unverified')
    
    created_at = db.Column(
        db.DateTime(timezone = True),
        nullable = False, 
        default = lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return{
        "id": self.id,
        "name": self.name,
        "age": self.age,
        "address": self.address,
        "username": self.username,
        "email": self.email,
        "is_client": self.is_client,
        "is_worker": self.is_worker,
        "is_admin": self.is_admin,
        "verification_status": self.verification_status,
        "created_at": self.created_at.isoformat()

    }


"""
Next is the registration route, POST /api/users. It is the first place the new set_password gets used, and Aldous’s register screen depends on it.

Before writing it, check that the model is fixed: python run.py starts without errors, and pgAdmin shows password_hash, is_client, is_worker and is_admin on the users table.

What the route must do

Read the JSON body.
Validate: name, age, address, username, email, password are present. age is a whole number. password is at least 8 characters. At least one of is_client or is_worker is true.
Check username and email aren’t already taken.
Create the User, call set_password, save.
Return 201 with to_dict(), or 400 with a clear message.

Never read is_admin from the request.

Files

services/user_service.py: validation and creation logic.
routes/users.py: the HTTP part only. It calls the service and returns JSON.

Write the service first. Start with the validation function, which returns a list of error messages. An empty list means valid.

python
def validate_registration(data):
    errors = []
    # Write one check per rule above.
    # Hint: data.get("name") returns None if the key is missing.
    return errors

Two things to think about before you write it:

What should age be if someone sends "abc"? How do you check that it’s a whole number?
Why check username and email in the service, when the database already has unique=True? Think about what the user sees in each case.

Write validate_registration, paste it here, and I’ll review it before we go on to the route.
    
    """
