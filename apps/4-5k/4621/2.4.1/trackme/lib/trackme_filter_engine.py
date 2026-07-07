"""
trackme_filter_engine.py

Lightweight entity filter DSL — Python port of filterEngine.ts.

Grammar:
  query    := or_expr
  or_expr  := and_expr ('OR' and_expr)*
  and_expr := atom+
  atom     := 'NOT' atom | '(' or_expr ')' | condition
  condition:= FIELD '=' VALUE
            | FIELD '!=' VALUE
            | FIELD 'IN(' VALUE [',' VALUE]* ')'

VALUE supports glob wildcards (* = any sequence, ? = any one char).
All comparisons are case-insensitive.
Multiple conditions separated by whitespace are an implicit AND.
'AND' keyword is accepted as an explicit separator (same as whitespace).

Examples:
  object=*prod*
  priority=high OR priority=critical
  (object=siem-* OR object=network-*) priority=high
  tags="security" priority=high
  NOT priority=low
  priority!=low
  index IN("_internal", "os-unix-*")
  object=*prod* AND priority=high
  NOT (priority=low OR priority=medium)
"""

import fnmatch
import logging
import re

logger = logging.getLogger("trackme.filter_engine")


# ---------------------------------------------------------------------------
# AST types
# ---------------------------------------------------------------------------

class FilterExpr:
    """Base class for filter AST nodes."""
    pass


class AndExpr(FilterExpr):
    """AND node — all children must match."""

    def __init__(self, children):
        self.children = children


class OrExpr(FilterExpr):
    """OR node — at least one child must match."""

    def __init__(self, children):
        self.children = children


class NotExpr(FilterExpr):
    """NOT node — child must NOT match."""

    def __init__(self, child):
        self.child = child


class ConditionExpr(FilterExpr):
    """Leaf node — field=value comparison with glob support."""

    def __init__(self, field, value):
        self.field = field
        self.value = value


class InExpr(FilterExpr):
    """Leaf node — field IN(value1, value2, ...) with glob support."""

    def __init__(self, field, values):
        self.field = field
        self.values = values


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

class Token:
    """Token produced by the tokeniser."""

    def __init__(self, token_type, field=None, value=None, values=None):
        self.type = token_type  # 'LPAREN', 'RPAREN', 'OR', 'AND', 'NOT', 'CONDITION', 'CONDITION_NEQ', 'IN'
        self.field = field
        self.value = value
        self.values = values


def _read_word(s, start):
    """Read a contiguous non-whitespace, non-paren word."""
    i = start
    word = []
    while i < len(s) and s[i] not in (' ', '\t', '\n', '\r', '(', ')'):
        word.append(s[i])
        i += 1
    return ''.join(word), i


def _strip_quotes(s):
    """Strip surrounding single or double quotes from a string."""
    return re.sub(r"^(['\"])(.*)\1$", r'\2', s)


def _read_in_values(s, start):
    """
    Read comma-separated values inside IN(...) starting after the '('.
    Returns (values_list, end_position).
    """
    i = start
    depth = 1
    content = []
    while i < len(s) and depth > 0:
        if s[i] == '(':
            depth += 1
            content.append(s[i])
        elif s[i] == ')':
            depth -= 1
            if depth > 0:
                content.append(s[i])
        else:
            content.append(s[i])
        i += 1
    raw = ''.join(content)
    values = []
    for part in raw.split(','):
        v = part.strip()
        v = _strip_quotes(v)
        if v:
            values.append(v)
    return values, i


def tokenize(input_str):
    """Tokenise a filter expression string."""
    tokens = []
    s = input_str.strip()
    i = 0
    pending_field = None  # bare word that might precede IN(...)

    while i < len(s):
        ch = s[i]
        if ch in (' ', '\t', '\n', '\r'):
            i += 1
        elif ch == '(':
            pending_field = None
            tokens.append(Token('LPAREN'))
            i += 1
        elif ch == ')':
            pending_field = None
            tokens.append(Token('RPAREN'))
            i += 1
        else:
            word, i = _read_word(s, i)
            if not word:
                continue

            upper = word.upper()

            if upper == 'OR':
                pending_field = None
                tokens.append(Token('OR'))
            elif upper == 'AND':
                pending_field = None
                tokens.append(Token('AND'))
            elif upper == 'NOT':
                pending_field = None
                tokens.append(Token('NOT'))
            elif upper == 'IN' and pending_field:
                # field IN(...) pattern — pending_field is the field name
                # Skip whitespace and find opening paren
                j = i
                while j < len(s) and s[j] in (' ', '\t', '\n', '\r'):
                    j += 1
                if j < len(s) and s[j] == '(':
                    j += 1  # skip '('
                    values, j = _read_in_values(s, j)
                    if values:
                        tokens.append(Token('IN', field=pending_field.lower(), values=values))
                    i = j
                pending_field = None
            else:
                # Find first '=' to determine operator (= or !=)
                eq_idx = word.find('=')
                if eq_idx > 0 and word[eq_idx - 1] == '!':
                    # != operator: field!=value
                    pending_field = None
                    field = word[:eq_idx - 1].lower()
                    raw_value = word[eq_idx + 1:]
                    value = _strip_quotes(raw_value)
                    if field and value:
                        tokens.append(Token('CONDITION_NEQ', field=field, value=value))
                elif eq_idx > 0:
                    pending_field = None
                    field = word[:eq_idx].lower()
                    raw_value = word[eq_idx + 1:]
                    value = _strip_quotes(raw_value)
                    if field and value:
                        tokens.append(Token('CONDITION', field=field, value=value))
                else:
                    # Bare word with no '=' — could be field name for IN(...)
                    pending_field = word

    return tokens


# ---------------------------------------------------------------------------
# Parser — recursive descent
# ---------------------------------------------------------------------------

class Parser:
    """Recursive descent parser for the filter grammar."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def parse(self):
        result = self._parse_or_expr()
        # Ensure all tokens were consumed — trailing tokens indicate malformed input
        if self.pos < len(self.tokens):
            remaining = self.tokens[self.pos]
            raise ValueError(
                f"Unexpected token at position {self.pos}: {remaining.type}"
            )
        return result

    def _parse_or_expr(self):
        parts = [self._parse_and_expr()]
        while self.peek() and self.peek().type == 'OR':
            self.consume()
            parts.append(self._parse_and_expr())
        if len(parts) == 1:
            return parts[0]
        return OrExpr(parts)

    def _parse_and_expr(self):
        atoms = []
        while self.pos < len(self.tokens):
            t = self.peek()
            if not t or t.type in ('OR', 'RPAREN'):
                break
            # Explicit AND keyword — consume and continue (acts as whitespace)
            if t.type == 'AND':
                self.consume()
                continue
            atoms.append(self._parse_atom())
        if len(atoms) == 0:
            return AndExpr([])
        if len(atoms) == 1:
            return atoms[0]
        return AndExpr(atoms)

    def _parse_atom(self):
        t = self.peek()
        if not t:
            return AndExpr([])

        if t.type == 'NOT':
            self.consume()
            child = self._parse_atom()
            return NotExpr(child)

        if t.type == 'LPAREN':
            self.consume()
            expr = self._parse_or_expr()
            if self.peek() and self.peek().type == 'RPAREN':
                self.consume()
            else:
                raise ValueError("Unclosed parenthesis in filter expression")
            return expr

        if t.type == 'CONDITION':
            self.consume()
            return ConditionExpr(t.field, t.value)

        if t.type == 'CONDITION_NEQ':
            self.consume()
            return NotExpr(ConditionExpr(t.field, t.value))

        if t.type == 'IN':
            self.consume()
            return InExpr(t.field, t.values)

        # unexpected token — skip
        self.consume()
        return AndExpr([])


# ---------------------------------------------------------------------------
# Glob matching
# ---------------------------------------------------------------------------

def _glob_match(pattern, text):
    """Case-insensitive glob matching using fnmatch."""
    return fnmatch.fnmatch(text.lower(), pattern.lower())


# ---------------------------------------------------------------------------
# Field extraction from entity
# ---------------------------------------------------------------------------

def _get_entity_field_values(entity, field):
    """
    Extract field values from an entity record, returning a list of strings.
    Handles special fields (index, sourcetype, tags, etc.) and falls back
    to raw entity field access.
    """
    if field in ('data_index', 'index'):
        val = entity.get('data_index') or entity.get('index')
        if val:
            return [v.strip() for v in str(val).split(',') if v.strip()]
        obj = str(entity.get('object', ''))
        parts = obj.split('::')
        if len(parts) >= 2:
            return [parts[0]]
        return [obj] if obj else []

    if field in ('data_sourcetype', 'sourcetype'):
        val = entity.get('data_sourcetype') or entity.get('sourcetype')
        if val:
            return [v.strip() for v in str(val).split(',') if v.strip()]
        obj = str(entity.get('object', ''))
        parts = obj.split('::')
        if len(parts) >= 2:
            return ['::'.join(parts[1:])]
        return []

    if field == 'object':
        val = entity.get('object') or entity.get('alias', '')
        return [str(val)] if val else []

    if field == 'tags':
        raw = entity.get('tags')
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        s = str(raw or '')
        if s:
            return [t.strip() for t in s.split(',') if t.strip()]
        return []

    if field == 'priority':
        val = str(entity.get('priority', '')).lower()
        return [val] if val else []

    if field == 'tenant':
        val = str(entity.get('tenant_id', ''))
        return [val] if val else []

    if field == 'component':
        val = str(entity.get('component', ''))
        return [val] if val else []

    # Default: raw field access
    val = entity.get(field)
    if val is None or val == '':
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    return [str(val)]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def _evaluate_expr(entity, expr):
    """Evaluate a filter expression against an entity record."""
    if isinstance(expr, AndExpr):
        if not expr.children:
            return True
        return all(_evaluate_expr(entity, c) for c in expr.children)

    if isinstance(expr, OrExpr):
        return any(_evaluate_expr(entity, c) for c in expr.children)

    if isinstance(expr, NotExpr):
        return not _evaluate_expr(entity, expr.child)

    if isinstance(expr, InExpr):
        values = _get_entity_field_values(entity, expr.field)
        if not values:
            return False
        return any(
            _glob_match(pattern, v)
            for pattern in expr.values
            for v in values
        )

    if isinstance(expr, ConditionExpr):
        values = _get_entity_field_values(entity, expr.field)
        if not values:
            return False
        return any(_glob_match(expr.value, v) for v in values)

    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_filter(filter_str):
    """
    Parse a filter string into an AST.
    Returns None for empty/invalid input.
    """
    if not filter_str or not filter_str.strip():
        return None
    try:
        tokens = tokenize(filter_str)
        if not tokens:
            return None
        return Parser(tokens).parse()
    except Exception:
        return None


def apply_filter(entities, filter_str):
    """
    Apply a filter string to an entity list.
    Returns the full list unchanged when the filter is empty/null.
    Returns an empty list when the filter is non-empty but unparseable
    (fail-closed — prevents silent over-matching).

    :param entities: list of dict — entity records
    :param filter_str: str — filter expression (e.g. "priority=high object=*prod*")
    :return: list of dict — filtered entities
    """
    if not filter_str or not filter_str.strip():
        return entities
    expr = parse_filter(filter_str)
    if not expr or _has_empty_and(expr):
        # Non-empty filter that produced no valid AST, or AST contains
        # unparseable remnants (empty AND nodes) — fail closed to avoid
        # silently returning all entities on unparseable expressions.
        logger.warning(
            "Filter expression could not be parsed, returning empty result set "
            "(fail-closed). filter=%s",
            filter_str,
        )
        return []
    return [e for e in entities if _evaluate_expr(e, expr)]


def validate_filter(filter_str):
    """
    Validate a filter string.
    Returns None when the string is valid (or empty), an error message otherwise.
    """
    if not filter_str or not filter_str.strip():
        return None
    tokens = tokenize(filter_str)
    # Reject input that produces no CONDITION/IN tokens — would silently match all
    if not any(t.type in ('CONDITION', 'CONDITION_NEQ', 'IN') for t in tokens):
        return 'Filter must contain at least one field=value condition (e.g. priority=high)'
    try:
        ast = Parser(tokens).parse()
        if _has_empty_and(ast):
            return 'Filter contains unrecognised syntax that would be silently ignored'
        return None
    except Exception as e:
        return f'Filter syntax error: {str(e)}'


def _has_empty_and(expr):
    """Return True if the AST contains any empty AND node (unparseable remnant)."""
    if isinstance(expr, AndExpr):
        if not expr.children:
            return True
        return any(_has_empty_and(c) for c in expr.children)
    if isinstance(expr, OrExpr):
        return any(_has_empty_and(c) for c in expr.children)
    if isinstance(expr, NotExpr):
        return _has_empty_and(expr.child)
    return False
