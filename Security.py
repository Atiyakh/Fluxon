import platform
import pathlib
import os
import traceback
import logging
import warnings
import hashlib
import hmac
import os
from typing import Optional, Tuple

class Secrets:
    def __init__(self, secrets_dir):
        self.secrets_dir = secrets_dir
        self.system_platform = platform.system().lower()
        self.has_logger = False
    
    def set_logger(self, logger: logging.Logger): # logger is set beforehand from the caller script
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            warnings.warn("- invalid logger")
            self.logger = logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.has_logger = True

    def set_file_permissions(self, file_path):
        """Set appropriate file permissions for secrets based on the platform."""
        if not self.has_logger:
            self.set_logger(None) # set default logger

        if self.system_platform == 'linux' or self.system_platform == 'darwin':
            # Make file readable only by owner
            os.chmod(file_path, 0o600)
            self.logger.info(f"Permissions set to 600 for {file_path}")

        elif self.system_platform == 'windows':
            try:
                import win32security
                import win32con
                # Get the file's security descriptor
                security_info = win32security.GetFileSecurity(str(file_path), win32security.DACL_SECURITY_INFORMATION)
                dacl = win32security.ACL()

                # Explicitly grant access to the owner only
                user_sid = win32security.LookupAccountName(None, win32security.GetUserName())[0]
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    win32con.FILE_GENERIC_READ | win32con.FILE_GENERIC_WRITE,
                    user_sid
                )
                security_info.SetSecurityDescriptorDacl(1, dacl, 0)

                # Apply the new DACL to the file
                win32security.SetFileSecurity(str(file_path), win32security.DACL_SECURITY_INFORMATION, security_info)

                self.logger.info(f"Permissions set to restrict access for {file_path} on Windows")
            except ImportError:
                self.logger.error("pywin32 is required for Windows ACL management. Please install it.")
                exit(1)
            except Exception as e:  # Catch all unexpected errors
                except_details = traceback.format_exc()
                self.logger.error(f"Unexpected error: {e} | traceback: {except_details} | Unable to safely load secrets.")
                warnings.warn("- failed to set file permissions for Windows")
        else:
            self.logger.warning(f"Unknown platform or missing win32security: {self.system_platform}. Skipping permission change for {file_path}")

    def load_secrets_to_env(self):
        """Load secrets into environment variables."""
        if not self.has_logger:
            self.set_logger(None)
        if not pathlib.Path(self.secrets_dir).is_dir():
            self.logger.error(f"Invalid secrets directory: {self.secrets_dir}. Exiting.")
            exit(1)

        for secret_file in pathlib.Path(self.secrets_dir).iterdir():
            if secret_file.is_symlink():
                self.logger.warning(f"Skipping symlink {secret_file}")
                continue

            if secret_file.is_file():
                secret_name = secret_file.stem  # Use the filename without extension as the environment variable name

                try:
                    # Check and set permissions before loading the secret
                    self.set_file_permissions(secret_file)
                except Exception as e:
                    self.logger.error(f"Failed to set permissions for {secret_file}: {e}")
                    continue  # Skip this file if permission setting fails

                try:
                    with open(secret_file, 'r', encoding='utf-8') as file:
                        secret_content = file.read().strip()
                except IOError as e:
                    self.logger.error(f"Failed to read {secret_file}: {e}")
                    continue  # Skip if reading fails

                if secret_name in os.environ:
                    self.logger.warning(f"Environment variable {secret_name} already exists. Skipping.")
                    continue  # Skip if the variable already exists

                os.environ[secret_name] = secret_content
                self.logger.info(f"Loaded secret {secret_name} into environment variables.")
            else:
                self.logger.warning(f"Skipping non-file {secret_file}")

class Hash:
    MD5, SHA1, SHA224, SHA256, SHA384, SHA512, SHA3_224, SHA3_256, SHA3_384, SHA3_512, Blake2B, Blake2S = 'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512', 'blake2b', 'blake2s'
    @staticmethod
    def hash(data:str, algorithm:str = SHA256):
        """Hashes a string using the specified algorithm. """
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif not isinstance(data, bytes):
            raise TypeError(f"Invalid data type: {type(data).__name__}. Expected str or bytes.")
        try:
            hash_func = hashlib.new(algorithm)
            hash_func.update(data)
            return hash_func.hexdigest()
        except ValueError:
            raise ValueError(f"Unsupported hashing algorithm: {algorithm}")

    @staticmethod
    def hmac_hash(data: str, key: str, algorithm: str = "sha256") -> str:
        """Computes an HMAC hash of the data using the given key and algorithm."""
        try:
            return hmac.new(key.encode("utf-8"), data.encode("utf-8"), getattr(hashlib, algorithm)).hexdigest()
        except AttributeError:
            raise ValueError(f"Unsupported HMAC hashing algorithm: {algorithm}")

    @staticmethod
    def salted_hash(data: str, salt: Optional[bytes] = None, algorithm: str = "sha256") -> Tuple[str, bytes]:
        """Generates a salted hash of the input string.
        
        If no salt is provided, a random 16-byte salt is generated.
        Returns a tuple (hashed_value, salt).
        """
        if salt is None:
            salt = os.urandom(16)  # Generate a random 16-byte salt
        hash_func = hashlib.new(algorithm)
        hash_func.update(salt + data.encode("utf-8"))
        return hash_func.hexdigest(), salt

    @staticmethod
    def verify_salted_hash(data: str, salt: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verifies if the provided data, when hashed with the given salt, matches the expected hash."""
        computed_hash, _ = HashUtils.salted_hash(data, salt, algorithm)
        return computed_hash == expected_hash

