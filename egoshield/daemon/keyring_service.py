"""
EgoShield Keyring Service
OS keychain integration for credential management

Per Section 9.4:
- IMAP credentials stored in OS keychain using keyring library
- Never stored in SQLite, config file, or environment variables
"""

import keyring
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "EgoShield"


class KeyringService:
    """
    Service for managing credentials via OS keychain.
    
    Uses the keyring library which provides cross-platform
    access to:
    - Windows Credential Manager
    - macOS Keychain
    - Linux Secret Service / KDE Wallet / etc.
    """
    
    @staticmethod
    def store_imap_credential(account_id: str, password: str) -> bool:
        """
        Store IMAP credential in OS keychain.
        
        Args:
            account_id: Unique account identifier (e.g., "imap.gmail.com:993:user@gmail.com")
            password: IMAP password
            
        Returns:
            True if stored successfully
        """
        try:
            keyring.set_password(SERVICE_NAME, account_id, password)
            logger.info(f"Stored credential for account: {account_id[:20]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            return False
    
    @staticmethod
    def get_imap_credential(account_id: str) -> Optional[str]:
        """
        Retrieve IMAP credential from OS keychain.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            Password string or None if not found
        """
        try:
            password = keyring.get_password(SERVICE_NAME, account_id)
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return None
    
    @staticmethod
    def delete_imap_credential(account_id: str) -> bool:
        """
        Delete IMAP credential from OS keychain.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            keyring.delete_password(SERVICE_NAME, account_id)
            logger.info(f"Deleted credential for account: {account_id[:20]}...")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"Credential not found for: {account_id[:20]}...")
            return False
        except Exception as e:
            logger.error(f"Failed to delete credential: {e}")
            return False
    
    @staticmethod
    def list_accounts() -> list:
        """
        List all EgoShield accounts stored in keychain.
        
        Note: This is a best-effort operation as keyring doesn't
        provide a direct list function across all platforms.
        
        Returns:
            List of account identifiers
        """
        # This is platform-dependent and may not work everywhere
        try:
            import keyring.backends
            for backend in keyring.backend.get_all_keyring():
                if hasattr(backend, 'get_password'):
                    # Can't enumerate without knowing what to look for
                    pass
        except Exception:
            pass
        
        return []  # Return empty list; user must manage accounts via UI
    
    @staticmethod
    def test_connection(account_id: str) -> bool:
        """
        Test if a credential exists and is valid.
        
        Args:
            account_id: Account identifier to test
            
        Returns:
            True if credential exists
        """
        password = KeyringService.get_imap_credential(account_id)
        return password is not None and len(password) > 0