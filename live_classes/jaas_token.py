import jwt, time, uuid
from django.conf import settings

def generate_jaas_token(user, room_name, is_moderator=False):
    """Generate a JaaS JWT token for a user joining a room."""
    with open(settings.JAAS_KEY_FILE, 'r') as f:
        private_key = f.read()

    now = int(time.time())
    payload = {
        "iss":  "chat",
        "aud":  "jitsi",
        "iat":  now,
        "nbf":  now - 10,
        "exp":  now + 7200,  # 2 hours
        "sub":  settings.JAAS_APP_ID,
        "room": room_name,
        "context": {
            "features": {
                "livestreaming": False,
                "outbound-call": False,
                "sip-outbound-call": False,
                "transcription": False,
                "recording": is_moderator,
            },
            "user": {
                "id":         str(user.id),
                "name":       user.get_full_name() or user.username,
                "email":      user.email or "",
                "avatar":     "",
                "moderator":  "true" if is_moderator else "false",
            }
        }
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": settings.JAAS_KEY_ID}
    )
    return token
