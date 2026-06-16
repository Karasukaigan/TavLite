import os
import time
from dotenv import set_key
import trustme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS_DIR = os.path.join(BASE_DIR, "keys")
ENV_PATH = os.path.join(BASE_DIR, ".env")
CERT_PATH = os.path.join(KEYS_DIR, "cert.pem")
KEY_PATH = os.path.join(KEYS_DIR, "key.pem")
RENEW_DAYS = 30


def ensure_cert():
    os.makedirs(KEYS_DIR, exist_ok=True)

    created_at = os.getenv("CERT_CREATED_AT")
    needs_renew = False
    if created_at:
        try:
            if time.time() - float(created_at) > RENEW_DAYS * 86400:
                needs_renew = True
        except (ValueError, TypeError):
            needs_renew = True
    else:
        needs_renew = True

    if needs_renew or not (os.path.exists(CERT_PATH) and os.path.exists(KEY_PATH)):
        ca = trustme.CA()
        cert = ca.issue_cert("127.0.0.1", "localhost", "tavlite.local")
        chain = b"\n".join(b.bytes() for b in cert.cert_chain_pems)
        with open(CERT_PATH, "wb") as f:
            f.write(chain)
        cert.private_key_pem.write_to_path(KEY_PATH)
        now = str(int(time.time()))
        set_key(ENV_PATH, "CERT_CREATED_AT", now)
        os.environ["CERT_CREATED_AT"] = now

    return CERT_PATH, KEY_PATH
