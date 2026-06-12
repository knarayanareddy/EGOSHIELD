"""
EgoShield Email Reader Module
Optional IMAP email integration for email analysis
"""

import imaplib
import logging
from typing import Optional, List
from dataclasses import dataclass

from .utils.logging import log_event

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Represented email message"""
    sender: str
    subject: str
    body: str
    date: str
    message_id: str


class EmailReader:
    """
    Email reader using imaplib (Python stdlib).
    
    Per Section 6.3:
    - Uses imaplib exclusively (no third-party IMAP libraries)
    - Credentials retrieved from OS keychain
    - No credential caching in memory beyond connection context
    - Only message body text is fetched, no attachments
    """
    
    def __init__(self, keyring_service):
        """
        Initialize email reader.
        
        Args:
            keyring_service: Keyring service for credential retrieval
        """
        self.keyring_service = keyring_service
        self._connection: Optional[imaplib.IMAP4_SSL] = None
        self._current_account: Optional[str] = None
    
    def connect(self, account_id: str) -> bool:
        """
        Connect to IMAP server using credentials from keychain.
        
        Args:
            account_id: Account identifier for keychain lookup
            
        Returns:
            True if connection successful
        """
        # Get credentials from keychain
        password = self.keyring_service.get_imap_credential(account_id)
        if not password:
            log_event(logger, "ERROR", "imap_connection_error", {
                'account_id_hash': hash(account_id) % 10000,  # Don't log actual ID
                'error_type': 'credential_not_found'
            })
            return False
        
        try:
            # Parse account configuration
            # Format: imap.server.com:993:username
            parts = account_id.split(':')
            if len(parts) != 3:
                logger.error(f"Invalid account ID format: {account_id}")
                return False
            
            server, port_str, username = parts
            port = int(port_str) if port_str else 993
            
            # Connect
            self._connection = imaplib.IMAP4_SSL(server, port)
            self._connection.login(username, password)
            self._current_account = account_id
            
            log_event(logger, "INFO", "imap_connected", {
                'account_id_hash': hash(account_id) % 10000
            })
            
            return True
            
        except imaplib.IMAP4.error as e:
            log_event(logger, "ERROR", "imap_connection_error", {
                'account_id_hash': hash(account_id) % 10000,
                'error_type': 'authentication_failed'
            })
            return False
            
        except Exception as e:
            log_event(logger, "ERROR", "imap_connection_error", {
                'account_id_hash': hash(account_id) % 10000,
                'error_type': type(e).__name__
            })
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None
            self._current_account = None
    
    def fetch_recent_emails(self, folder: str = 'INBOX', limit: int = 10) -> List[EmailMessage]:
        """
        Fetch recent emails from specified folder.
        
        Args:
            folder: IMAP folder to fetch from
            limit: Maximum number of emails to fetch
            
        Returns:
            List of EmailMessage objects
        """
        if not self._connection:
            logger.warning("Not connected to IMAP server")
            return []
        
        try:
            # Select folder
            status, _ = self._connection.select(folder)
            if status != 'OK':
                logger.error(f"Failed to select folder {folder}")
                return []
            
            # Search for recent emails
            status, message_ids = self._connection.search(None, 'ALL')
            if status != 'OK':
                return []
            
            # Get latest messages (up to limit)
            all_ids = message_ids[0].split()
            recent_ids = all_ids[-limit:] if len(all_ids) > limit else all_ids
            
            emails = []
            for msg_id in reversed(recent_ids):
                email = self._fetch_single_message(msg_id.decode())
                if email:
                    emails.append(email)
            
            return emails
            
        except Exception as e:
            log_event(logger, "ERROR", "imap_fetch_error", {
                'folder': folder,
                'error_type': type(e).__name__
            })
            return []
    
    def _fetch_single_message(self, msg_id: str) -> Optional[EmailMessage]:
        """Fetch a single email message"""
        try:
            status, msg_data = self._connection.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                return None
            
            # Parse the message
            from email.parser import Parser
            from email.header import decode_header
            
            raw_email = msg_data[0][1]
            msg = Parser().parsestr(raw_email)
            
            # Extract sender
            sender = self._decode_header(msg.get('From', ''))
            
            # Extract subject
            subject = self._decode_header(msg.get('Subject', ''))
            
            # Extract body (plain text only)
            body = self._extract_body(msg)
            
            # Extract date
            date = msg.get('Date', '')
            
            # Extract message ID
            message_id = msg.get('Message-ID', msg_id)
            
            return EmailMessage(
                sender=sender,
                subject=subject,
                body=body,
                date=date,
                message_id=message_id
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch message {msg_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header value"""
        from email.header import decode_header
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except Exception:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(part)
        
        return ' '.join(decoded_parts)
    
    def _extract_body(self, msg) -> str:
        """Extract plain text body from email message"""
        body = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        body.append(part.get_payload(decode=True).decode(charset, errors='replace'))
                    except Exception:
                        pass
        else:
            try:
                charset = msg.get_content_charset() or 'utf-8'
                body.append(msg.get_payload(decode=True).decode(charset, errors='replace'))
            except Exception:
                pass
        
        return '\n\n'.join(body)[:50000]  # Cap at 50k characters
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False