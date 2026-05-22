"""
grammar_utils.py  –  LL(1) grammar analysis utilities.

Key fix in this version
───────────────────────
_normalize_grammar used to keep any all-lowercase multi-char token (like
'abc', 'abd', 'ae') as a single opaque terminal, which broke left-factoring
because the grouping step never saw a common first character.

Now the rule is:
  • known NT            → kept whole
  • 'ε'                 → kept whole
  • single char         → kept whole
  • multi-char token that IS in a curated "known terminal" list
    (e.g. 'id', 'num', 'then', 'else', 'begin', 'end', 'int', 'float')
    → kept whole
  • anything else (e.g. 'abc', 'abd', 'ae') → split char-by-char
    (after first trying to consume known NTs greedily)
"""

import re
from collections import OrderedDict


# Terminals that are always kept as a single token even though they are
# multi-character lowercase strings.  Extend this list as needed.
_KNOWN_TERMINALS = {
    'id', 'num', 'int', 'float', 'char', 'void',
    'if', 'else', 'then', 'while', 'do', 'for',
    'begin', 'end', 'return', 'print', 'read',
    'true', 'false', 'and', 'or', 'not',
}


# ─────────────────────────────────────────────────────────────────────────────
#  Normalizer
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_grammar(grammar: dict) -> dict:
    """
    Split every token in every production into proper atomic symbols.

    Rules (in priority order):
      1. 'ε'                            → kept whole
      2. token is a known NT            → kept whole
      3. single character               → kept whole
      4. token is in _KNOWN_TERMINALS   → kept whole  (e.g. 'id', 'num')
      5. everything else                → greedy-NT split, then char-by-char
    """
    nts = set(grammar.keys())

    def split_prod(prod):
        result = []
        for token in prod:
            if token == 'ε':
                result.append(token)
            elif token in nts:
                result.append(token)
            elif len(token) == 1:
                result.append(token)
            elif token in _KNOWN_TERMINALS:
                # recognised keyword/terminal – keep whole
                result.append(token)
            else:
                # Unknown multi-char string (e.g. 'abc', 'abd', 'ae').
                # Greedy-match known NTs first, then fall back to char-by-char.
                i = 0
                while i < len(token):
                    matched = False
                    for length in range(len(token) - i, 1, -1):
                        if token[i:i+length] in nts:
                            result.append(token[i:i+length])
                            i += length
                            matched = True
                            break
                    if not matched:
                        result.append(token[i])
                        i += 1
        return result

    new_grammar = OrderedDict()
    for nt, productions in grammar.items():
        new_grammar[nt] = [split_prod(p) for p in productions]
    return new_grammar


# ─────────────────────────────────────────────────────────────────────────────
#  Left Recursion Removal  (direct + indirect)
# ─────────────────────────────────────────────────────────────────────────────

def remove_left_recursion(grammar: dict) -> dict:
    """Remove both direct AND indirect left recursion."""
    grammar     = _normalize_grammar(grammar)
    nts         = list(grammar.keys())
    new_grammar = OrderedDict((nt, list(prods)) for nt, prods in grammar.items())

    for i, ai in enumerate(nts):
        # Substitute earlier NTs to expose indirect left recursion
        for aj in nts[:i]:
            new_prods = []
            for prod in new_grammar[ai]:
                if prod and prod[0] == aj:
                    for aj_prod in new_grammar[aj]:
                        if aj_prod == ['ε']:
                            new_prods.append(prod[1:] if prod[1:] else ['ε'])
                        else:
                            new_prods.append(aj_prod + prod[1:])
                else:
                    new_prods.append(prod)
            new_grammar[ai] = new_prods

        # Now eliminate direct left recursion for ai
        recursive     = []
        non_recursive = []
        for prod in new_grammar[ai]:
            if prod and prod[0] == ai:
                recursive.append(prod[1:])
            else:
                non_recursive.append(prod)

        if not recursive:
            continue

        prime = ai + "'"
        while prime in new_grammar:
            prime += "'"

        new_grammar[ai] = []
        for beta in non_recursive:
            new_grammar[ai].append((beta if beta else ['ε']) + [prime])
        if not non_recursive:
            new_grammar[ai].append([prime])

        new_grammar[prime] = []
        for alpha in recursive:
            new_grammar[prime].append((alpha if alpha else ['ε']) + [prime])
        new_grammar[prime].append(['ε'])

    return new_grammar


# ─────────────────────────────────────────────────────────────────────────────
#  Left Factoring
# ─────────────────────────────────────────────────────────────────────────────

def _common_prefix(prods: list) -> list:
    if not prods:
        return []
    prefix = list(prods[0])
    for prod in prods[1:]:
        length = 0
        for a, b in zip(prefix, prod):
            if a == b:
                length += 1
            else:
                break
        prefix = prefix[:length]
        if not prefix:
            break
    return prefix


def left_factoring(grammar: dict) -> dict:
    """
    Apply left factoring using longest-common-prefix grouping.

    The outer loop keeps iterating until no more factoring is possible,
    so nested common prefixes (like 'ab' inside 'abc'/'abd') are handled
    correctly in successive passes.
    """
    grammar = _normalize_grammar(grammar)

    def _make_new_nt(base: str, existing: set) -> str:
        candidate = base + "'"
        while candidate in existing:
            candidate += "'"
        return candidate

    changed = True
    while changed:
        changed = False
        new_grammar = OrderedDict()

        for nt, productions in grammar.items():
            all_nts = set(grammar.keys()) | set(new_grammar.keys())

            # Group productions by their first symbol
            groups: dict = OrderedDict()
            for prod in productions:
                key = prod[0] if prod else 'ε'
                groups.setdefault(key, []).append(prod)

            # No group has more than one alternative → nothing to factor
            if all(len(g) == 1 for g in groups.values()):
                new_grammar[nt] = productions
                continue

            changed = True
            new_grammar[nt] = []

            for _key, group in groups.items():
                if len(group) == 1:
                    new_grammar[nt].append(group[0])
                    continue

                lcp    = _common_prefix(group)
                new_nt = _make_new_nt(nt, all_nts)
                all_nts.add(new_nt)

                new_grammar[nt].append(lcp + [new_nt])
                new_grammar[new_nt] = []
                for prod in group:
                    rest = prod[len(lcp):]
                    new_grammar[new_nt].append(rest if rest else ['ε'])

        grammar = new_grammar

    return grammar


# ─────────────────────────────────────────────────────────────────────────────
#  FIRST Sets
# ─────────────────────────────────────────────────────────────────────────────

def compute_first(grammar: dict) -> dict:
    """
    Compute FIRST sets for all non-terminals.
    A terminal t is in FIRST(A) if A =>* t...
    ε is in FIRST(A) if A =>* ε
    """
    first = {nt: set() for nt in grammar}

    def first_of(symbol):
        if symbol not in grammar:
            return {symbol}
        return first[symbol]

    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                if prod == ['ε']:
                    if 'ε' not in first[nt]:
                        first[nt].add('ε')
                        changed = True
                    continue

                derives_eps = True
                for symbol in prod:
                    f      = first_of(symbol)
                    before = len(first[nt])
                    first[nt] |= (f - {'ε'})
                    if len(first[nt]) != before:
                        changed = True
                    if 'ε' not in f:
                        derives_eps = False
                        break

                if derives_eps:
                    if 'ε' not in first[nt]:
                        first[nt].add('ε')
                        changed = True

    return first


# ─────────────────────────────────────────────────────────────────────────────
#  FOLLOW Sets
# ─────────────────────────────────────────────────────────────────────────────

def compute_follow(grammar: dict, first: dict) -> dict:
    nts    = list(grammar.keys())
    follow = {nt: set() for nt in nts}
    follow[nts[0]].add('$')

    def first_of_sequence(symbols):
        result       = set()
        all_nullable = True
        for s in symbols:
            sf = first.get(s, set()) if s in grammar else {s}
            result |= (sf - {'ε'})
            if 'ε' not in sf:
                all_nullable = False
                break
        return result, all_nullable

    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                if prod == ['ε']:
                    continue
                for idx, symbol in enumerate(prod):
                    if symbol not in grammar:
                        continue

                    rest                = prod[idx + 1:]
                    first_rest, all_eps = first_of_sequence(rest)

                    before = len(follow[symbol])
                    follow[symbol] |= first_rest
                    if all_eps:
                        follow[symbol] |= follow[nt]
                    if len(follow[symbol]) != before:
                        changed = True

    return follow


# ─────────────────────────────────────────────────────────────────────────────
#  Display Helpers
# ─────────────────────────────────────────────────────────────────────────────

def format_grammar(grammar: dict, title: str = '') -> str:
    lines = []
    if title:
        lines.append(title)
        lines.append('─' * max(len(title), 40))
    for nt, productions in grammar.items():
        rhs = ' | '.join(' '.join(prod) for prod in productions)
        lines.append(f'  {nt:<12} →  {rhs}')
    return '\n'.join(lines)


def format_first_follow(first: dict, follow: dict) -> str:
    lines = ['── FIRST Sets ─────────────────────────', '']
    for nt, s in first.items():
        clean = ', '.join(sorted(s)) if s else '∅'
        lines.append(f'  FIRST({nt}) = {{ {clean} }}')
    lines += ['', '── FOLLOW Sets ────────────────────────', '']
    for nt, s in follow.items():
        if not s:
            lines.append(f'  FOLLOW({nt}) = ∅')
        else:
            clean = ', '.join(sorted(s))
            lines.append(f'  FOLLOW({nt}) = {{ {clean} }}')
    return '\n'.join(lines)

def print_grammar(grammar: dict):
    for nt, productions in grammar.items():
        rhs = ' | '.join(' '.join(prod) for prod in productions)
        print(f'  {nt} → {rhs}')