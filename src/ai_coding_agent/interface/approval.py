"""Approval system for user confirmation of operations."""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from .display import display


class ApprovalType(str, Enum):
    """Types of approval requests."""
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXECUTION = "command_execution"
    GIT_OPERATION = "git_operation"
    DESTRUCTIVE_OPERATION = "destructive_operation"
    NETWORK_ACCESS = "network_access"


class ApprovalResult(str, Enum):
    """Results of approval requests."""
    APPROVED = "approved"
    DENIED = "denied"
    ALWAYS_ALLOW = "always_allow"
    NEVER_ALLOW = "never_allow"


class ApprovalSystem:
    """Manages user approval for potentially destructive operations."""
    
    def __init__(self):
        self.approval_rules: Dict[str, ApprovalResult] = {}
        self.approval_callbacks: Dict[ApprovalType, Callable] = {}
        self.auto_approve_patterns: List[str] = []
        self.auto_deny_patterns: List[str] = []
    
    def set_approval_callback(
        self, 
        approval_type: ApprovalType, 
        callback: Callable[[str, Dict[str, Any]], bool]
    ) -> None:
        """Set a custom approval callback for a specific type."""
        self.approval_callbacks[approval_type] = callback
    
    def add_auto_approve_pattern(self, pattern: str) -> None:
        """Add a pattern that will be automatically approved."""
        self.auto_approve_patterns.append(pattern)
    
    def add_auto_deny_pattern(self, pattern: str) -> None:
        """Add a pattern that will be automatically denied."""
        self.auto_deny_patterns.append(pattern)
    
    def request_approval(
        self,
        approval_type: ApprovalType,
        operation_description: str,
        details: Optional[Dict[str, Any]] = None,
        preview: Optional[str] = None
    ) -> ApprovalResult:
        """Request approval for an operation."""
        details = details or {}
        
        # Check for automatic patterns first
        if self._check_auto_patterns(operation_description, details):
            return self._get_auto_result(operation_description, details)
        
        # Check existing rules
        rule_key = self._get_rule_key(approval_type, operation_description, details)
        if rule_key in self.approval_rules:
            stored_result = self.approval_rules[rule_key]
            if stored_result in [ApprovalResult.ALWAYS_ALLOW, ApprovalResult.NEVER_ALLOW]:
                return stored_result
        
        # Use custom callback if available
        if approval_type in self.approval_callbacks:
            callback = self.approval_callbacks[approval_type]
            try:
                approved = callback(operation_description, details)
                return ApprovalResult.APPROVED if approved else ApprovalResult.DENIED
            except Exception as e:
                display.print_error(f"Approval callback error: {e}")
                return ApprovalResult.DENIED
        
        # Default interactive approval
        return self._interactive_approval(
            approval_type, operation_description, details, preview
        )
    
    def _check_auto_patterns(
        self, 
        operation_description: str, 
        details: Dict[str, Any]
    ) -> bool:
        """Check if operation matches auto-approval/denial patterns."""
        operation_text = f"{operation_description} {str(details)}".lower()
        
        # Check deny patterns first (higher priority)
        for pattern in self.auto_deny_patterns:
            if pattern.lower() in operation_text:
                return True
        
        # Check approve patterns
        for pattern in self.auto_approve_patterns:
            if pattern.lower() in operation_text:
                return True
        
        return False
    
    def _get_auto_result(
        self, 
        operation_description: str, 
        details: Dict[str, Any]
    ) -> ApprovalResult:
        """Get automatic approval/denial result."""
        operation_text = f"{operation_description} {str(details)}".lower()
        
        # Check deny patterns first
        for pattern in self.auto_deny_patterns:
            if pattern.lower() in operation_text:
                return ApprovalResult.NEVER_ALLOW
        
        # Check approve patterns
        for pattern in self.auto_approve_patterns:
            if pattern.lower() in operation_text:
                return ApprovalResult.ALWAYS_ALLOW
        
        return ApprovalResult.DENIED
    
    def _interactive_approval(
        self,
        approval_type: ApprovalType,
        operation_description: str,
        details: Dict[str, Any],
        preview: Optional[str] = None
    ) -> ApprovalResult:
        """Interactive approval dialog."""
        # Show operation details
        display.print_panel(
            operation_description,
            title=f"🔐 Approval Required: {approval_type.value.replace('_', ' ').title()}",
            style="yellow",
            border_style="yellow"
        )
        
        # Show additional details
        if details:
            display.print_header("📋 Operation Details")
            for key, value in details.items():
                display.print(f"  {key}: {value}", style="dim")
        
        # Show preview if available
        if preview:
            display.print_header("👀 Preview")
            display.print_panel(preview, style="cyan", border_style="cyan")
        
        # Show options
        display.print("\nOptions:")
        display.print("  [bold green]y[/bold green] - Approve this operation")
        display.print("  [bold red]n[/bold red] - Deny this operation")
        display.print("  [bold cyan]a[/bold cyan] - Always approve operations like this")
        display.print("  [bold magenta]never[/bold magenta] - Never approve operations like this")
        display.print("  [bold blue]details[/bold blue] - Show more details")
        
        while True:
            try:
                response = display.console.input("\nYour choice: ").strip().lower()
                
                if response in ['y', 'yes', 'approve']:
                    return ApprovalResult.APPROVED
                elif response in ['n', 'no', 'deny']:
                    return ApprovalResult.DENIED
                elif response in ['a', 'always', 'always_allow']:
                    # Store rule for future
                    rule_key = self._get_rule_key(approval_type, operation_description, details)
                    self.approval_rules[rule_key] = ApprovalResult.ALWAYS_ALLOW
                    display.print_success("✅ Rule saved: Future similar operations will be auto-approved")
                    return ApprovalResult.ALWAYS_ALLOW
                elif response in ['never', 'never_allow']:
                    # Store rule for future
                    rule_key = self._get_rule_key(approval_type, operation_description, details)
                    self.approval_rules[rule_key] = ApprovalResult.NEVER_ALLOW
                    display.print_warning("⛔ Rule saved: Future similar operations will be auto-denied")
                    return ApprovalResult.NEVER_ALLOW
                elif response == 'details':
                    self._show_detailed_info(approval_type, operation_description, details)
                else:
                    display.print("Invalid choice. Please enter y, n, a, never, or details", style="red")
            
            except KeyboardInterrupt:
                display.print("\nOperation cancelled by user", style="yellow")
                return ApprovalResult.DENIED
            except EOFError:
                return ApprovalResult.DENIED
    
    def _show_detailed_info(
        self,
        approval_type: ApprovalType,
        operation_description: str,
        details: Dict[str, Any]
    ) -> None:
        """Show detailed information about the operation."""
        display.print_header("🔍 Detailed Information")
        
        # Risk assessment
        risk_level = self._assess_risk(approval_type, operation_description, details)
        risk_color = {
            "low": "green",
            "medium": "yellow", 
            "high": "red"
        }.get(risk_level, "white")
        
        display.print(f"Risk Level: [{risk_color}]{risk_level.upper()}[/{risk_color}]")
        
        # Operation type info
        type_info = {
            ApprovalType.FILE_WRITE: "Modifies file system content",
            ApprovalType.FILE_DELETE: "Permanently removes files or directories",
            ApprovalType.COMMAND_EXECUTION: "Executes system commands",
            ApprovalType.GIT_OPERATION: "Modifies version control state",
            ApprovalType.DESTRUCTIVE_OPERATION: "May cause irreversible changes",
            ApprovalType.NETWORK_ACCESS: "Accesses network resources"
        }
        
        display.print(f"Operation Type: {type_info.get(approval_type, 'Unknown')}")
        
        # Show what could go wrong
        risks = self._get_operation_risks(approval_type, details)
        if risks:
            display.print("\nPotential Risks:")
            for risk in risks:
                display.print(f"  ⚠️  {risk}", style="yellow")
        
        # Show mitigation suggestions
        mitigations = self._get_mitigation_suggestions(approval_type, details)
        if mitigations:
            display.print("\nMitigation Suggestions:")
            for mitigation in mitigations:
                display.print(f"  🛡️  {mitigation}", style="cyan")
    
    def _assess_risk(
        self,
        approval_type: ApprovalType,
        operation_description: str,
        details: Dict[str, Any]
    ) -> str:
        """Assess the risk level of an operation."""
        high_risk_patterns = [
            "delete", "remove", "rm ", "format", "truncate",
            "sudo", "su ", "chmod 777", "git push", "git reset --hard"
        ]
        
        medium_risk_patterns = [
            "write", "modify", "overwrite", "commit", "move"
        ]
        
        operation_text = f"{operation_description} {str(details)}".lower()
        
        if any(pattern in operation_text for pattern in high_risk_patterns):
            return "high"
        elif any(pattern in operation_text for pattern in medium_risk_patterns):
            return "medium"
        else:
            return "low"
    
    def _get_operation_risks(
        self,
        approval_type: ApprovalType,
        details: Dict[str, Any]
    ) -> List[str]:
        """Get list of potential risks for an operation."""
        risks = []
        
        if approval_type == ApprovalType.FILE_DELETE:
            risks.extend([
                "Permanent data loss",
                "Breaking application functionality",
                "Loss of uncommitted changes"
            ])
        elif approval_type == ApprovalType.FILE_WRITE:
            risks.extend([
                "Overwriting important data",
                "Introducing syntax errors",
                "Breaking existing functionality"
            ])
        elif approval_type == ApprovalType.COMMAND_EXECUTION:
            risks.extend([
                "System modification",
                "Security vulnerabilities",
                "Unintended side effects"
            ])
        elif approval_type == ApprovalType.GIT_OPERATION:
            risks.extend([
                "History modification",
                "Merge conflicts",
                "Lost commits"
            ])
        elif approval_type == ApprovalType.NETWORK_ACCESS:
            risks.extend([
                "Data leakage",
                "Security exposure",
                "Rate limiting/blocking"
            ])
        
        return risks
    
    def _get_mitigation_suggestions(
        self,
        approval_type: ApprovalType,
        details: Dict[str, Any]
    ) -> List[str]:
        """Get mitigation suggestions for an operation."""
        suggestions = []
        
        if approval_type in [ApprovalType.FILE_WRITE, ApprovalType.FILE_DELETE]:
            suggestions.extend([
                "Create a backup before proceeding",
                "Use version control to track changes",
                "Test in a development environment first"
            ])
        elif approval_type == ApprovalType.COMMAND_EXECUTION:
            suggestions.extend([
                "Review the command carefully",
                "Run in a sandbox if possible",
                "Check for unintended side effects"
            ])
        elif approval_type == ApprovalType.GIT_OPERATION:
            suggestions.extend([
                "Create a branch backup",
                "Review changes before pushing",
                "Understand the operation's impact"
            ])
        
        return suggestions
    
    def _get_rule_key(
        self,
        approval_type: ApprovalType,
        operation_description: str,
        details: Dict[str, Any]
    ) -> str:
        """Generate a key for storing approval rules."""
        # Create a simplified key based on operation type and key details
        key_parts = [approval_type.value]
        
        # Add relevant details for rule matching
        if "path" in details:
            # Generalize file paths
            path = str(details["path"])
            if "/" in path:
                key_parts.append(f"path_type:{path.split('/')[-1].split('.')[-1]}")
            else:
                key_parts.append(f"path_type:{path}")
        
        if "command" in details:
            # Generalize commands
            command = str(details["command"]).split()[0]  # Just the base command
            key_parts.append(f"command:{command}")
        
        return ":".join(key_parts)
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """Get statistics about approval rules and patterns."""
        return {
            "stored_rules": len(self.approval_rules),
            "auto_approve_patterns": len(self.auto_approve_patterns),
            "auto_deny_patterns": len(self.auto_deny_patterns),
            "rules_by_type": {},  # Could be expanded
            "approval_rules": dict(self.approval_rules)
        }
    
    def clear_approval_rules(self, approval_type: Optional[ApprovalType] = None) -> None:
        """Clear stored approval rules."""
        if approval_type:
            # Clear rules for specific type
            keys_to_remove = [
                key for key in self.approval_rules.keys()
                if key.startswith(approval_type.value)
            ]
            for key in keys_to_remove:
                del self.approval_rules[key]
        else:
            # Clear all rules
            self.approval_rules.clear()
    
    def export_approval_rules(self) -> Dict[str, Any]:
        """Export approval rules for backup/sharing."""
        return {
            "approval_rules": dict(self.approval_rules),
            "auto_approve_patterns": list(self.auto_approve_patterns),
            "auto_deny_patterns": list(self.auto_deny_patterns)
        }
    
    def import_approval_rules(self, rules_data: Dict[str, Any]) -> None:
        """Import approval rules from backup/sharing."""
        if "approval_rules" in rules_data:
            self.approval_rules.update(rules_data["approval_rules"])
        
        if "auto_approve_patterns" in rules_data:
            self.auto_approve_patterns.extend(rules_data["auto_approve_patterns"])
        
        if "auto_deny_patterns" in rules_data:
            self.auto_deny_patterns.extend(rules_data["auto_deny_patterns"])


# Global approval system instance
approval_system = ApprovalSystem()