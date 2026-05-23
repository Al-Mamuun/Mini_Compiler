class VariableRegistry:
    """
    Symbol table with nested-scope support.

    Scopes are maintained as a stack of dicts.  Each dict maps an
    identifier name to its entry.  Searching always walks from the
    innermost scope outward so that inner declarations shadow outer ones.
    """

    def __init__(self):
        self.scope_stack      = [{}]
        self.scope_names      = ['global']
        self.current_scope_id = 0
        self.all_variables    = []

    # ── Write operations ─────────────────────────────────────────────────────

    def add(self, identifier: str, var_type: str,
            initial_val=None, context: str = 'declaration'):
        """Declare a new variable in the *current* scope."""
        entry = {
            'id':          identifier,
            'dtype':       var_type,
            'val':         initial_val,
            'ctx':         context,
            'scope':       self.scope_names[-1],
            'scope_level': len(self.scope_stack) - 1,
        }
        self.scope_stack[-1][identifier] = entry
        self.all_variables.append(entry)

    def update(self, identifier: str, new_value) -> bool:
        """
        Update the stored value of *identifier* in the nearest enclosing
        scope that declares it.
        """
        for scope in reversed(self.scope_stack):
            if identifier in scope:
                scope[identifier]['val'] = new_value
                for var in reversed(self.all_variables):
                    if (var['id'] == identifier
                            and var['scope'] == scope[identifier]['scope']):
                        var['val'] = new_value
                        break
                return True
        return False

    # ── Read operations ──────────────────────────────────────────────────────

    def find(self, identifier: str):
        """Return the entry for *identifier* (nearest scope), or None."""
        for scope in reversed(self.scope_stack):
            if identifier in scope:
                return scope[identifier]
        return None

    def find_in_current_scope(self, identifier: str):
        return self.scope_stack[-1].get(identifier)

    def is_declared_in_current_scope(self, identifier: str) -> bool:
        return identifier in self.scope_stack[-1]

    def all_entries(self):
        """All entries ever declared, in declaration order (for the UI)."""
        return self.all_variables

    def current_scope_entries(self):
        return list(self.scope_stack[-1].values())

    # ── Scope management ─────────────────────────────────────────────────────

    def push_scope(self, scope_name: str = None):
        if scope_name is None:
            
            self.current_scope_id += 1
            scope_name = f"block_{self.current_scope_id}"
        self.scope_stack.append({})
        self.scope_names.append(scope_name)

    def pop_scope(self):
        """Pop the innermost scope. The global scope is never popped."""
        if len(self.scope_stack) > 1:
            self.scope_names.pop()
            return self.scope_stack.pop()
        return None

    def get_scope_level(self) -> int:
        return len(self.scope_stack) - 1

    def get_current_scope_name(self) -> str:
        return self.scope_names[-1]

    # ── Reset ────────────────────────────────────────────────────────────────

    def clear(self):
        self.scope_stack      = [{}]
        self.scope_names      = ['global']
        self.current_scope_id = 0
        self.all_variables    = []