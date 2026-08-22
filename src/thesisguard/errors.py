"""Typed error hierarchy. Input, analysis, safety and contract failures are never merged."""

from __future__ import annotations


class ThesisGuardError(Exception):
    """Base class for all ThesisGuard errors."""


class PackValidationError(ThesisGuardError):
    """Raised when a DailyEvidencePack cannot be parsed against the strict schema."""


class AnalysisError(ThesisGuardError):
    """Raised when the analysis engine fails or returns schema-invalid output."""


class SafetyViolation(ThesisGuardError):
    """Raised when generated output violates financial-safety policy."""


class ContractViolation(ThesisGuardError):
    """Raised when JSON and Markdown outputs disagree on the same facts."""
