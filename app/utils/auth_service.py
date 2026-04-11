import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    prehashed = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(prehashed)


def verify_password(password: str, hashed: str) -> bool:
    prehashed = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.verify(prehashed, hashed)
