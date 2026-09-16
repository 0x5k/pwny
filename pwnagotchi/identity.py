try:
    # Upstream 1.5.5 uses pycryptodome's historical ``Crypto`` namespace.
    from Crypto.Signature import PKCS1_PSS
    from Crypto.PublicKey import RSA
    import Crypto.Hash.SHA256 as SHA256
except ImportError:
    # Debian's python3-pycryptodome package exposes the collision-safe
    # ``Cryptodome`` namespace instead. Keep the OG identity implementation
    # unchanged while supporting the packaged Trixie runtime.
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Hash import SHA256

    class _PSSCompat:
        @staticmethod
        def new(key, saltLen=16):
            from Cryptodome.Signature import pss
            return pss.new(key, salt_bytes=saltLen)

    PKCS1_PSS = _PSSCompat
import base64
import hashlib
import os
import logging
import shutil
import tempfile

DefaultPath = "/etc/pwnagotchi/"


def _write_key(path, data, mode):
    """Atomically write a generated identity key with private-file perms."""
    fd, temporary = tempfile.mkstemp(prefix=".pwnagotchi-key-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as fp:
            fp.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _generate_identity(path):
    """Generate keys with pwngrid when present, otherwise use PyCryptodome."""
    pwngrid = shutil.which("pwngrid")
    if pwngrid:
        return os.system("%s -generate -keys '%s'" % (pwngrid, path))

    logging.warning("pwngrid is unavailable; generating the identity with PyCryptodome")
    key = RSA.generate(2048)
    _write_key(os.path.join(path, "id_rsa"), key.export_key("PEM"), 0o600)
    _write_key(
        os.path.join(path, "id_rsa.pub"),
        key.publickey().export_key("PEM", pkcs=1),
        0o644,
    )
    return 0


class KeyPair(object):
    def __init__(self, path=DefaultPath, view=None):
        self.path = path
        self.priv_path = os.path.join(path, "id_rsa")
        self.priv_key = None
        self.pub_path = "%s.pub" % self.priv_path
        self.pub_key = None
        self.fingerprint_path = os.path.join(path, "fingerprint")
        self._view = view

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        while True:
            # first time, generate new keys
            if not os.path.exists(self.priv_path) or not os.path.exists(self.pub_path):
                self._view.on_keys_generation()
                logging.info("generating %s ..." % self.priv_path)
                _generate_identity(self.path)

            # load keys: they might be corrupted if the unit has been turned off during the generation, in this case
            # the exception will remove the files and go back at the beginning of this loop.
            try:
                with open(self.priv_path) as fp:
                    self.priv_key = RSA.importKey(fp.read())

                with open(self.pub_path) as fp:
                    self.pub_key = RSA.importKey(fp.read())
                    self.pub_key_pem = self.pub_key.exportKey('PEM').decode("ascii")
                    # python is special
                    if 'RSA PUBLIC KEY' not in self.pub_key_pem:
                        self.pub_key_pem = self.pub_key_pem.replace('PUBLIC KEY', 'RSA PUBLIC KEY')

                pem_ascii = self.pub_key_pem.encode("ascii")

                self.pub_key_pem_b64 = base64.b64encode(pem_ascii).decode("ascii")
                self.fingerprint = hashlib.sha256(pem_ascii).hexdigest()

                with open(self.fingerprint_path, 'w+t') as fp:
                    fp.write(self.fingerprint)

                # no exception, keys loaded correctly.
                self._view.on_starting()
                return

            except Exception as e:
                # if we're here, loading the keys broke something ...
                logging.exception("error loading keys, maybe corrupted, deleting and regenerating ...")
                try:
                    os.remove(self.priv_path)
                    os.remove(self.pub_path)
                except:
                    pass

    def sign(self, message):
        hasher = SHA256.new(message.encode("ascii"))
        signer = PKCS1_PSS.new(self.priv_key, saltLen=16)
        signature = signer.sign(hasher)
        signature_b64 = base64.b64encode(signature).decode("ascii")
        return signature, signature_b64
