"""Tests for the hybrid early-veto detector in :mod:`boule.debate`.

The detector layers three signals:

1. Explicit colon-suffixed markers (``VETO:``, ``VIOLATION:``).
2. Line-leading veto verbs (``VETO``, ``REJECT``, etc.).
3. Negation-guarded loose substring fallback.

The case that motivated the rewrite: Zeus replying
``"no apparent constitutional violations ... may proceed"``. The old
detector flagged this as a veto because ``"VIOLATIONS"`` contains
``"VIOLATION"``. The hybrid detector recognises the surrounding
negation and lets it through.
"""

from __future__ import annotations

from athean_core.schema import ThesisBlock

from boule.debate import _is_early_veto


def _block(text: str) -> ThesisBlock:
    return ThesisBlock(
        agent="zeus", round=1, content=text, tokens=len(text), latency_ms=1
    )


# ─── negation guard (the bug we are fixing) ─────────────────────────


def test_no_constitutional_violations_is_not_a_veto():
    """The Zeus response that surfaced the bug must now pass through."""
    text = (
        "CONSTITUTIONAL.\n\n"
        "The proposed trade for the Bitcoin market does not present any "
        "apparent constitutional violations. The market probability and "
        "oracle probability, while differing, do not inherently breach "
        "any articles. The council may proceed."
    )
    assert _is_early_veto(_block(text)) is False


def test_no_violations_found_is_not_a_veto():
    text = "All policy checks pass. No violations found."
    assert _is_early_veto(_block(text)) is False


def test_zero_violations_is_not_a_veto():
    text = "Zero violations detected across the constitutional review."
    assert _is_early_veto(_block(text)) is False


def test_lacks_any_violation_is_not_a_veto():
    text = "The trade lacks any violation of the council's rules."
    assert _is_early_veto(_block(text)) is False


def test_does_not_veto_phrasing_passes_through():
    text = "Zeus does not veto this trade. All checks clear."
    assert _is_early_veto(_block(text)) is False


# ─── real vetoes still fire ─────────────────────────────────────────


def test_explicit_veto_marker_fires():
    text = "VETO: Article 3 of the constitution prohibits self-dealing."
    assert _is_early_veto(_block(text)) is True


def test_explicit_violation_marker_fires():
    text = "VIOLATION: This market resolves on an oracle the council has flagged as compromised."
    assert _is_early_veto(_block(text)) is True


def test_line_leading_veto_verb_fires():
    text = "VETO. The signal references an oracle without provenance."
    assert _is_early_veto(_block(text)) is True


def test_line_leading_reject_fires():
    text = "REJECT this trade. The edge is fabricated."
    assert _is_early_veto(_block(text)) is True


def test_unqualified_violation_in_body_fires():
    text = (
        "After full review, the trade represents a clear policy violation "
        "of Article 7."
    )
    assert _is_early_veto(_block(text)) is True


def test_constitutional_violation_keyword_fires():
    text = "Constitutional_violation flagged on Article 4 breach."
    assert _is_early_veto(_block(text)) is True


# ─── boundary cases ─────────────────────────────────────────────────


def test_empty_content_is_not_a_veto():
    assert _is_early_veto(_block("")) is False


def test_unrelated_text_is_not_a_veto():
    text = "Liquidity adequate. Edge plausible. Recommend APPROVE at half-Kelly."
    assert _is_early_veto(_block(text)) is False


def test_verb_substring_does_not_falsely_fire():
    """``REJECTED LAST QUARTER`` is past-tense narration, not a command."""
    text = "Similar markets were rejected last quarter, but this one is cleaner."
    # ``REJECTED`` starts a line but isn't a bare REJECT — should not
    # fire on the line-leading-verb rule alone. The body word
    # ``cleaner`` carries no veto keyword. Negation guard ("but this
    # one is cleaner") is absent for the loose rule, so the only risk
    # is the line-leading rule.
    assert _is_early_veto(_block(text)) is False


def test_bullet_prefixed_veto_still_fires():
    text = "- VETO. Tail risk uncovered after Cassandra's flag."
    assert _is_early_veto(_block(text)) is True


def test_negation_only_guards_within_window():
    """A negation 80 chars before the keyword should NOT mute the veto."""
    text = (
        "There is no good evidence the council was wrong on prior calls, "
        "however the current trade is a clear violation of Article 9."
    )
    assert _is_early_veto(_block(text)) is True


# ─── Zeus / Solon prompt vocabulary (verb forms) ────────────────────


def test_violated_verb_form_fires():
    """The actual Zeus prompt instructs: "quote the specific Article
    being violated". The detector must catch the verb form, not just
    the noun.
    """
    text = "Article 3 of the constitution is violated by self-dealing on this trade."
    assert _is_early_veto(_block(text)) is True


def test_violates_present_tense_fires():
    text = "This trade violates the Pantheon Constitution Article 7."
    assert _is_early_veto(_block(text)) is True


def test_breach_fires():
    text = "The proposed position is a breach of risk policy section 4."
    assert _is_early_veto(_block(text)) is True


def test_breached_past_tense_fires():
    text = "Article 5 was breached: proposed size 6.2% exceeds the 5% cap."
    assert _is_early_veto(_block(text)) is True


def test_illegal_fires():
    text = "Material non-public information makes this trade illegal."
    assert _is_early_veto(_block(text)) is True


def test_forbidden_fires():
    text = "The market category is forbidden under the active risk policy."
    assert _is_early_veto(_block(text)) is True


def test_unconstitutional_fires():
    text = "Treating prior vetoes as inputs is unconstitutional per Article 9."
    assert _is_early_veto(_block(text)) is True


# ─── Solon canonical approval phrasing must still pass ──────────────


def test_solon_approval_phrase_passes():
    """Solon's literal APPROVE format from his prompt:
    "All policy checks pass. No violations found."
    """
    text = "All policy checks pass. No violations found."
    assert _is_early_veto(_block(text)) is False


def test_zeus_approval_phrase_passes():
    """Zeus's literal APPROVE format from his prompt:
    "Constitution intact. No violations found. The council may proceed."
    """
    text = (
        "Constitution intact. No violations found. The council may proceed."
    )
    assert _is_early_veto(_block(text)) is False


def test_explicit_reject_marker_fires():
    text = "REJECT: position size 6.2% breaches risk policy 5.0% cap."
    assert _is_early_veto(_block(text)) is True


def test_explicit_block_marker_fires():
    text = "BLOCK: cooling period active until 2026-06-01."
    assert _is_early_veto(_block(text)) is True


def test_line_leading_halt_fires():
    text = "HALT. Drawdown trigger fired at 4.2% peak-to-trough."
    assert _is_early_veto(_block(text)) is True


def test_line_leading_stop_fires():
    text = "STOP. The market is under emergency pause."
    assert _is_early_veto(_block(text)) is True


def test_decline_command_fires():
    text = "DECLINE. The information set is incomplete."
    assert _is_early_veto(_block(text)) is True
