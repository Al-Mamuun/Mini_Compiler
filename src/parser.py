import ply.yacc as yacc
from lexer import TokenScanner
from symbol_table import VariableRegistry


class SyntaxProcessor:
    """
    LALR(1) parser + IR emitter.
    """

    tokens = TokenScanner.tokens

    # ── Operator precedence ──────────────────────────────────────────────────
    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'MULTIPLY', 'DIVIDE', 'MOD'),
    )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def __init__(self):
        self.registry        = VariableRegistry()
        self.ir_instructions = []
        self.tmp_counter     = 0
        self.lbl_counter     = 0
        self.issues          = []
        self.ast             = []
        self._last_cond      = None

    def gen_temp(self) -> str:
        self.tmp_counter += 1
        return f"t{self.tmp_counter}"

    def gen_label(self) -> str:
        self.lbl_counter += 1
        return f"L{self.lbl_counter}"

    def emit(self, op, src1=None, src2=None, dst=None):
        """Append one three-address instruction and return *dst*."""
        self.ir_instructions.append(
            {'op': op, 'src1': src1, 'src2': src2, 'dst': dst}
        )
        return dst

    # ── Grammar ──────────────────────────────────────────────────────────────

    def p_start(self, p):
        'start : stmt_sequence'
        p[0] = ('program', p[1])
        self.ast.append(p[0])

    def p_stmt_sequence(self, p):
        '''stmt_sequence : stmt_sequence stmt
                         | stmt'''
        p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

    def p_stmt(self, p):
        '''stmt : var_decl
                | var_assign
                | output_stmt
                | conditional
                | loop
                | code_block
                | func_decl
                | return_stmt
                | expr_stmt'''
        p[0] = p[1]

    # ── Declarations ─────────────────────────────────────────────────────────

    def p_var_decl(self, p):
        '''var_decl : data_type IDENTIFIER SEMICOLON
                    | data_type IDENTIFIER EQUALS expr SEMICOLON'''
        dtype, name = p[1], p[2]
        if self.registry.is_declared_in_current_scope(name):
            self.issues.append(
                f"Error: '{name}' already declared in this scope"
            )
        else:
            if len(p) == 4:                 # int x;
                self.registry.add(name, dtype, None)
                p[0] = ('decl', dtype, name)
            else:                           # int x = expr;
                val = p[4]
                self.registry.add(name, dtype, val)
                self.emit('assign', val, None, name)
                p[0] = ('decl_init', dtype, name, val)

    def p_data_type(self, p):
        '''data_type : INT
                     | FLOAT
                     | VOID'''
        p[0] = p[1]

    # ── Function Declaration ──────────────────────────────────────────────────

    def p_func_decl(self, p):
        '''func_decl : data_type IDENTIFIER LPAREN param_list RPAREN code_block
                     | data_type IDENTIFIER LPAREN RPAREN code_block'''
        fname = p[2]
        dtype = p[1]
        if len(p) == 7:
            params = p[4]
            body   = p[6]
        else:
            params = []
            body   = p[5]
        if self.registry.is_declared_in_current_scope(fname):
            self.issues.append(f"Error: function '{fname}' already declared")
        else:
            self.registry.add(fname, dtype, None, 'function')
        self.emit('func_begin', fname, dtype)
        p[0] = ('func_decl', dtype, fname, params, body)

    def p_param_list(self, p):
        '''param_list : param_list COMMA param
                      | param'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_param(self, p):
        '''param : data_type IDENTIFIER'''
        self.registry.add(p[2], p[1], None, 'param')
        self.emit('param', p[2], p[1])
        p[0] = (p[1], p[2])

    # ── Return statement ─────────────────────────────────────────────────────

    def p_return_stmt(self, p):
        '''return_stmt : RETURN expr SEMICOLON
                       | RETURN SEMICOLON'''
        if len(p) == 4:
            self.emit('return', p[2])
            p[0] = ('return', p[2])
        else:
            self.emit('return', None)
            p[0] = ('return', None)

    # ── Expression statement (function call as statement) ────────────────────

    def p_expr_stmt(self, p):
        'expr_stmt : IDENTIFIER LPAREN arg_list RPAREN SEMICOLON'
        fname = p[1]
        args  = p[3]
        if not self.registry.find(fname):
            self.issues.append(f"Error: Undefined function '{fname}'")
        tmp = self.gen_temp()
        for arg in args:
            self.emit('arg', arg)
        self.emit('call', fname, len(args), tmp)
        p[0] = ('call_stmt', fname, args)

    def p_arg_list_many(self, p):
        '''arg_list : arg_list COMMA expr'''
        p[0] = p[1] + [p[3]]

    def p_arg_list_one(self, p):
        '''arg_list : expr'''
        p[0] = [p[1]]

    def p_arg_list_empty(self, p):
        '''arg_list :'''
        p[0] = []

    # ── Assignment ───────────────────────────────────────────────────────────

    def p_var_assign(self, p):
        'var_assign : IDENTIFIER EQUALS expr SEMICOLON'
        name, val = p[1], p[3]
        if not self.registry.find(name):
            self.issues.append(f"Error: Undefined variable '{name}'")
        else:
            self.registry.update(name, val)
        self.emit('assign', val, None, name)
        p[0] = ('assign', name, val)

    # ── Output ───────────────────────────────────────────────────────────────

    def p_output_stmt(self, p):
        'output_stmt : PRINT LPAREN expr RPAREN SEMICOLON'
        self.emit('output', p[3])
        p[0] = ('output', p[3])

    # ── If / If-else ─────────────────────────────────────────────────────────

    def p_conditional_if(self, p):
        'conditional : IF LPAREN comparison RPAREN if_jump code_block if_end'
        p[0] = ('if', p[3], p[6])

    def p_conditional_ifelse(self, p):
        ('conditional : IF LPAREN comparison RPAREN'
         ' if_jump code_block else_jump ELSE code_block if_end')
        p[0] = ('ifelse', p[3], p[6], p[9])

    def p_if_jump(self, p):
        'if_jump :'
        lbl_false = self.gen_label()
        self.emit('jump_if_false', self._last_cond, lbl_false)
        self._if_false_stack = getattr(self, '_if_false_stack', [])
        self._if_false_stack.append(lbl_false)
        p[0] = None

    def p_else_jump(self, p):
        'else_jump :'
        lbl_end = self.gen_label()
        self._if_end_stack = getattr(self, '_if_end_stack', [])
        self._if_end_stack.append(lbl_end)
        self.emit('jump', lbl_end)
        lbl_false = self._if_false_stack.pop()
        self.emit('mark', lbl_false)
        p[0] = None

    def p_if_end(self, p):
        'if_end :'
        if hasattr(self, '_if_end_stack') and self._if_end_stack:
            lbl_end = self._if_end_stack.pop()
            self.emit('mark', lbl_end)
        else:
            lbl_false = self._if_false_stack.pop()
            self.emit('mark', lbl_false)
        p[0] = None

    # ── While loop ───────────────────────────────────────────────────────────

    def p_loop(self, p):
        'loop : WHILE while_start LPAREN comparison RPAREN while_body code_block while_end'
        p[0] = ('while', p[4], p[7])

    def p_while_start(self, p):
        'while_start :'
        lbl_start = self.gen_label()
        self.emit('mark', lbl_start)
        self._while_start_stack = getattr(self, '_while_start_stack', [])
        self._while_start_stack.append(lbl_start)
        p[0] = None

    def p_while_body(self, p):
        'while_body :'
        cond = self._last_cond
        lbl_end = self.gen_label()
        self._while_end_stack = getattr(self, '_while_end_stack', [])
        self._while_end_stack.append(lbl_end)
        self.emit('jump_if_false', cond, lbl_end)
        p[0] = None

    def p_while_end(self, p):
        'while_end :'
        lbl_start = self._while_start_stack.pop()
        lbl_end   = self._while_end_stack.pop()
        self.emit('jump', lbl_start)
        self.emit('mark', lbl_end)
        p[0] = None

    # ── Blocks ───────────────────────────────────────────────────────────────

    def p_code_block(self, p):
        'code_block : block_start stmt_sequence block_end'
        p[0] = ('block', p[2])

    def p_block_start(self, p):
        'block_start : LBRACE'
        # FIX: push_scope() কে name দেওয়া হচ্ছে না —
        # symbol_table নিজেই block_1, block_2 ... সঠিকভাবে তৈরি করবে
        self.registry.push_scope()
        p[0] = 'block_start'

    def p_block_end(self, p):
        'block_end : RBRACE'
        self.registry.pop_scope()
        p[0] = 'block_end'

    # ── Comparisons ──────────────────────────────────────────────────────────

    def p_comparison(self, p):
        'comparison : expr rel_op expr'
        tmp = self.gen_temp()
        self.emit(p[2], p[1], p[3], tmp)
        self._last_cond = tmp
        p[0] = tmp

    def p_rel_op(self, p):
        '''rel_op : LESS
                  | LESS_EQ
                  | GREATER
                  | GREATER_EQ
                  | EQUAL_TO
                  | NOT_EQUAL'''
        p[0] = p[1]

    # ── Expressions ──────────────────────────────────────────────────────────

    def p_expr_add(self, p):
        '''expr : expr PLUS term
                | expr MINUS term'''
        tmp = self.gen_temp()
        self.emit(p[2], p[1], p[3], tmp)
        p[0] = tmp

    def p_expr_term(self, p):
        'expr : term'
        p[0] = p[1]

    def p_term_mul(self, p):
        '''term : term MULTIPLY base
                | term DIVIDE base
                | term MOD base'''
        tmp = self.gen_temp()
        self.emit(p[2], p[1], p[3], tmp)
        p[0] = tmp

    def p_term_base(self, p):
        'term : base'
        p[0] = p[1]

    def p_base_num(self, p):
        '''base : INTEGER
                | DECIMAL'''
        p[0] = p[1]

    def p_base_id(self, p):
        'base : IDENTIFIER'
        if not self.registry.find(p[1]):
            self.issues.append(f"Error: Undefined variable '{p[1]}'")
        p[0] = p[1]

    def p_base_call(self, p):
        'base : IDENTIFIER LPAREN arg_list RPAREN'
        fname = p[1]
        args  = p[3]
        if not self.registry.find(fname):
            self.issues.append(f"Error: Undefined function '{fname}'")
        for arg in args:
            self.emit('arg', arg)
        tmp = self.gen_temp()
        self.emit('call', fname, len(args), tmp)
        p[0] = tmp

    def p_base_paren(self, p):
        'base : LPAREN expr RPAREN'
        p[0] = p[2]

    # ── Error recovery ───────────────────────────────────────────────────────

    def p_error(self, p):
        if p:
            self.issues.append(
                f"Syntax error near '{p.value}' (line {p.lineno})"
            )
            while True:
                tok = self.processor.token()
                if tok is None or tok.type in ('SEMICOLON', 'RBRACE'):
                    break
            self.processor.restart()
        else:
            self.issues.append("Syntax error: unexpected end of input")

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def initialize(self):
        """Build the PLY parser (no output files generated)."""
        import logging
        logging.getLogger('ply').setLevel(logging.CRITICAL)
        self.processor = yacc.yacc(
            module=self,
            debug=False,
            write_tables=False,
            errorlog=yacc.NullLogger(),
        )

    def process(self, code: str):
        """Parse *code*, populate the symbol table, and emit IR."""
        self.ir_instructions    = []
        self.tmp_counter        = 0
        self.lbl_counter        = 0
        self.issues             = []
        self.ast                = []
        self._last_cond         = None
        self._if_false_stack    = []
        self._if_end_stack      = []
        self._while_start_stack = []
        self._while_end_stack   = []
        self.registry.clear()

        return self.processor.parse(code)