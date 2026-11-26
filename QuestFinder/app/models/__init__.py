"""Import every model so Flask-Migrate sees the whole schema."""
from app.models.user import User, ROLE_ADMIN, ROLE_MEMBER  # noqa: F401
from app.models.verification import VerificationRequest  # noqa: F401
from app.models.quest import Quest, QuestApplication  # noqa: F401
from app.models.wallet import Wallet, Transaction  # noqa: F401
from app.models.messaging import Conversation, Message  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.rating import Rating  # noqa: F401
