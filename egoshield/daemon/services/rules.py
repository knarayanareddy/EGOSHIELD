"""
EgoShield Rules Service
Manages user rules (trusted domains, suppressed tactics, custom patterns)
"""

import logging
from typing import List, Dict, Optional

from ..db.connection import Database
from ..db.models import RulesRepository, RuleType, UserRule
from ..utils.logging import log_event

logger = logging.getLogger(__name__)


class RulesService:
    """
    Service for managing user rules.
    
    Rule types:
    - trusted_domain: Domains where analysis is skipped
    - suppress_tactic: Tactic names to suppress in results
    - custom_pattern: User-defined detection patterns
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.repo = RulesRepository(db)
    
    def get_all_rules(self) -> List[UserRule]:
        """Get all user rules"""
        return self.repo.get_all()
    
    def get_rules_dict(self) -> Dict[str, List[str]]:
        """
        Get rules as a structured dictionary.
        
        Returns:
            {
                'trusted_domains': [...],
                'suppressed_tactics': [...],
                'custom_patterns': [...]
            }
        """
        return self.repo.get_rules_dict()
    
    def add_trusted_domain(self, domain: str, notes: Optional[str] = None) -> UserRule:
        """Add a domain to the trusted list"""
        return self._add_rule(RuleType.TRUSTED_DOMAIN.value, domain, notes)
    
    def remove_trusted_domain(self, domain: str) -> bool:
        """Remove a domain from the trusted list"""
        return self._remove_rule(RuleType.TRUSTED_DOMAIN.value, domain)
    
    def add_suppressed_tactic(self, tactic_name: str, notes: Optional[str] = None) -> UserRule:
        """Add a tactic to the suppressed list"""
        return self._add_rule(RuleType.SUPPRESS_TACTIC.value, tactic_name, notes)
    
    def remove_suppressed_tactic(self, tactic_name: str) -> bool:
        """Remove a tactic from the suppressed list"""
        return self._remove_rule(RuleType.SUPPRESS_TACTIC.value, tactic_name)
    
    def add_custom_pattern(self, pattern: str, notes: Optional[str] = None) -> UserRule:
        """Add a custom detection pattern"""
        return self._add_rule(RuleType.CUSTOM_PATTERN.value, pattern, notes)
    
    def remove_custom_pattern(self, pattern: str) -> bool:
        """Remove a custom pattern"""
        return self._remove_rule(RuleType.CUSTOM_PATTERN.value, pattern)
    
    def _add_rule(self, rule_type: str, value: str, notes: Optional[str] = None) -> UserRule:
        """Add a generic rule"""
        try:
            rule = self.repo.create({
                'rule_type': rule_type,
                'value': value,
                'notes': notes
            })
            
            log_event(logger, "INFO", "rule_added", {
                'rule_type': rule_type,
                'value': value
            })
            
            return rule
            
        except Exception as e:
            # Check if it's a duplicate constraint
            if "UNIQUE" in str(e):
                raise ValueError(f"Rule already exists: {rule_type}:{value}")
            raise
    
    def _remove_rule(self, rule_type: str, value: str) -> bool:
        """Remove a generic rule"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM user_rules WHERE rule_type = ? AND value = ?
            """, (rule_type, value))
            
            if cursor.rowcount > 0:
                log_event(logger, "INFO", "rule_removed", {
                    'rule_type': rule_type,
                    'value': value
                })
                return True
            
            return False
    
    def is_domain_trusted(self, domain: str) -> bool:
        """Check if a domain is trusted"""
        return domain in self.get_rules_dict()['trusted_domains']
    
    def get_suppressed_tactics(self) -> List[str]:
        """Get list of suppressed tactic names"""
        return self.get_rules_dict()['suppressed_tactics']
    
    def get_custom_patterns(self) -> List[str]:
        """Get list of custom detection patterns"""
        return self.get_rules_dict()['custom_patterns']