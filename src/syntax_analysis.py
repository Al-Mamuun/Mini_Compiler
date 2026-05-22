# ============================================================
# PHASE 2 — SYNTAX ANALYSIS
# LexiCore
# ============================================================
"""
syntax_analysis.py

Wraps the SyntaxProcessor (PLY LALR parser) and exposes a clean
result dict that the GUI's render_syntax() function can display.

Result structure
────────────────
{
  'productions': [str, ...],      # every grammar rule fired, in order
  'ast_nodes':   [str, ...],      # node labels collected from the AST tuples
  'parse_tree':  str,             # indented text representation of the AST
  'errors':      [str, ...],      # syntax / parse errors
  'stats': {
      'productions': int,
      'ast_nodes':   int,
      'depth':       int,
      'errors':      int,
  }
}
"""

from __future__ import annotations


# ── production-name → readable label ────────────────────────────────────────
_PROD_LABELS: dict[str, str] = {
    'p_start':              'start  →  stmt_sequence',
    'p_stmt_sequence':      'stmt_sequence  →  stmt_sequence stmt  |  stmt',
    'p_stmt':               'stmt  →  var_decl | var_assign | output_stmt | conditional | loop | code_block',
    'p_var_decl':           'var_decl  →  data_type IDENTIFIER ; | data_type IDENTIFIER = expr ;',
    'p_data_type':          'data_type  →  int | float',
    'p_var_assign':         'var_assign  →  IDENTIFIER = expr ;',
    'p_output_stmt':        'output_stmt  →  print ( expr ) ;',
    'p_conditional_if':     'conditional  →  if ( comparison ) { ... }',
    'p_conditional_ifelse': 'conditional  →  if ( comparison ) { ... } else { ... }',
    'p_if_jump':            'if_jump  →  ε   [back-patch false label]',
    'p_else_jump':          'else_jump  →  ε  [emit jump-over-else]',
    'p_if_end':             'if_end  →  ε   [patch end label]',
    'p_loop':               'loop  →  while ( comparison ) { ... }',
    'p_while_start':        'while_start  →  ε  [mark loop entry]',
    'p_while_body':         'while_body  →  ε  [emit conditional exit]',
    'p_while_end':          'while_end  →  ε  [back-jump to start]',
    'p_code_block':         'code_block  →  { stmt_sequence }',
    'p_block_start':        'block_start  →  {   [push scope]',
    'p_block_end':          'block_end  →  }    [pop scope]',
    'p_comparison':         'comparison  →  expr rel_op expr',
    'p_rel_op':             'rel_op  →  < | <= | > | >= | == | !=',
    'p_expr_add':           'expr  →  expr + term  |  expr - term',
    'p_expr_term':          'expr  →  term',
    'p_term_mul':           'term  →  term * base  |  term / base  |  term % base',
    'p_term_base':          'term  →  base',
    'p_base_num':           'base  →  INTEGER | DECIMAL',
    'p_base_id':            'base  →  IDENTIFIER',
    'p_base_paren':         'base  →  ( expr )',
    'p_error':              '⚠  Syntax error / recovery',
    'p_func_decl':          'func_decl  →  type id ( params ) { ... }',
    'p_param_list':         'param_list  →  param_list , param  |  param',
    'p_param':              'param  →  data_type IDENTIFIER',
    'p_return_stmt':        'return_stmt  →  return expr ;  |  return ;',
    'p_expr_stmt':          'expr_stmt  →  IDENTIFIER ( args ) ;',
    'p_arg_list_many':      'arg_list  →  arg_list , expr',
    'p_arg_list_one':       'arg_list  →  expr',
    'p_arg_list_empty':     'arg_list  →  ε',
    'p_base_call':          'base  →  IDENTIFIER ( arg_list )',
}


# ── AST helpers ─────────────────────────────────────────────────────────────

def _ast_depth(node, depth: int = 0) -> int:
    if not isinstance(node, (list, tuple)) or not node:
        return depth
    if isinstance(node, tuple):
        return max(_ast_depth(child, depth + 1) for child in node[1:]) if len(node) > 1 else depth + 1
    # list
    return max(_ast_depth(item, depth) for item in node)


def _ast_to_lines(node, indent: int = 0, lines: list | None = None) -> list[str]:
    """Recursively convert the AST (nested tuples / lists) to indented lines."""
    if lines is None:
        lines = []
    pad = '  ' * indent

    if node is None:
        lines.append(f'{pad}None')
        return lines

    if isinstance(node, tuple):
        label = str(node[0]) if node else '()'
        lines.append(f'{pad}({label}')
        for child in node[1:]:
            _ast_to_lines(child, indent + 1, lines)
        lines.append(f'{pad})')
        return lines

    if isinstance(node, list):
        lines.append(f'{pad}[')
        for item in node:
            _ast_to_lines(item, indent + 1, lines)
        lines.append(f'{pad}]')
        return lines

    lines.append(f'{pad}{repr(node)}')
    return lines


def _collect_node_labels(node, out: list | None = None) -> list[str]:
    if out is None:
        out = []
    if node is None:
        return out
    if isinstance(node, tuple) and node:
        out.append(str(node[0]).upper())
        for child in node[1:]:
            _collect_node_labels(child, out)
    elif isinstance(node, list):
        for item in node:
            _collect_node_labels(item, out)
    return out


# ── patch SyntaxProcessor to log productions ────────────────────────────────

def _patch_processor(processor) -> list[str]:
    """
    Monkey-patches the production functions of *processor* so every
    successful reduction appends its canonical name to a shared list.
    Returns that list (mutations are visible to the caller).
    """
    import types

    fired: list[str] = []
    processor._fired_productions = fired

    # Iterate over all methods whose names start with 'p_'
    for attr in dir(processor.__class__):
        if not attr.startswith('p_'):
            continue
        orig = getattr(processor.__class__, attr, None)
        if not callable(orig):
            continue
        # Only wrap grammar-action functions (they take exactly one arg: p)
        try:
            import inspect
            sig = inspect.signature(orig)
            params = list(sig.parameters)
        except (ValueError, TypeError):
            continue
        # Grammar rules take (self, p) → 2 params
        if len(params) != 2:
            continue

        label = _PROD_LABELS.get(attr, attr)

        def _make_wrapper(original, lbl, name):
            def wrapper(self_inner, p):
                try:
                    original(self_inner, p)
                except Exception:
                    pass
                if lbl not in self_inner._fired_productions:
                    self_inner._fired_productions.append(lbl)
            wrapper.__name__ = name
            wrapper.__doc__  = original.__doc__
            return wrapper

        setattr(processor.__class__, attr, _make_wrapper(orig, label, attr))

    return fired


# ── public API ───────────────────────────────────────────────────────────────

def run_syntax_analysis(processor, src: str) -> dict:
    """
    Run (or re-use) the SyntaxProcessor on *src* and return a result dict.

    Parameters
    ----------
    processor : SyntaxProcessor
        Already-initialised parser (processor.initialize() must have been
        called).  This function calls processor.process(src) itself.
    src : str
        Source code string.

    Returns
    -------
    dict   (see module docstring for structure)
    """
    # Patch once (idempotent — second call is harmless)
    if not hasattr(processor, '_fired_productions'):
        _patch_processor(processor)
    else:
        processor._fired_productions.clear()

    # Run the parse (also resets ir_instructions, registry, issues)
    processor.process(src)

    fired  = list(processor._fired_productions)
    errors = list(processor.issues)

    # Build AST representation from processor.ast
    ast_root = processor.ast  # list of top-level tuples
    node_labels = _collect_node_labels(ast_root)
    parse_tree_lines = _ast_to_lines(ast_root)
    parse_tree_text  = '\n'.join(parse_tree_lines)

    depth = _ast_depth(ast_root)

    return {
        'productions': fired,
        'ast_nodes':   node_labels,
        'parse_tree':  parse_tree_text,
        'errors':      errors,
        'stats': {
            'productions': len(fired),
            'ast_nodes':   len(node_labels),
            'depth':       depth,
            'errors':      len(errors),
        },
    }