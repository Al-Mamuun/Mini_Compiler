import ply.yacc as yacc
from lexer import TokenScanner
from symbol_table import VariableRegistry


class SyntaxProcessor:
    """
    LALR(1) parser + IR emitter.
    Supports LexiCore syntax AND C-style code.
    Fixes: comma-separated declarations, braceless if/else/for/while,
           break inside loops, return 0, multi-var declarations.
    """

    tokens = TokenScanner.tokens

    precedence = (
        ('left',  'OR'),
        ('left',  'AND'),
        ('right', 'NOT'),
        ('left',  'EQUAL_TO', 'NOT_EQUAL'),
        ('left',  'LESS', 'LESS_EQ', 'GREATER', 'GREATER_EQ'),
        ('left',  'PLUS', 'MINUS'),
        ('left',  'MULTIPLY', 'DIVIDE', 'MOD'),
        ('right', 'UMINUS'),
        ('left',  'INCREMENT', 'DECREMENT'),
    )

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
        self.ir_instructions.append(
            {'op': op, 'src1': src1, 'src2': src2, 'dst': dst}
        )
        return dst

    # ════════════════════════════════════════════════════════════════════════
    #  TOP LEVEL
    # ════════════════════════════════════════════════════════════════════════

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
                | var_decl_multi
                | var_assign
                | compound_assign
                | output_stmt
                | input_stmt
                | conditional
                | loop
                | for_loop
                | code_block
                | func_decl
                | return_stmt
                | break_stmt
                | continue_stmt
                | expr_stmt
                | increment_stmt'''
        p[0] = p[1]

    # ── Data types ───────────────────────────────────────────────────────────

    def p_data_type(self, p):
        '''data_type : INT
                     | FLOAT
                     | VOID
                     | CHAR
                     | DOUBLE
                     | LONG
                     | SHORT
                     | UNSIGNED'''
        p[0] = p[1]

    # ── Single variable declaration ──────────────────────────────────────────

    def p_var_decl(self, p):
        '''var_decl : data_type IDENTIFIER SEMICOLON
                    | data_type IDENTIFIER EQUALS expr SEMICOLON'''
        dtype, name = p[1], p[2]
        if self.registry.is_declared_in_current_scope(name):
            self.issues.append(f"Error: '{name}' already declared in this scope")
        else:
            if len(p) == 4:
                self.registry.add(name, dtype, None)
                p[0] = ('decl', dtype, name)
            else:
                val = p[4]
                self.registry.add(name, dtype, val)
                self.emit('assign', val, None, name)
                p[0] = ('decl_init', dtype, name, val)

    # ── Comma-separated declaration: int n, i, flag = 0; ────────────────────

    def p_var_decl_multi(self, p):
        'var_decl_multi : data_type decl_list SEMICOLON'
        p[0] = ('decl_multi', p[1], p[2])

    def p_decl_list(self, p):
        '''decl_list : decl_list COMMA decl_item
                     | decl_item'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_decl_item(self, p):
        '''decl_item : IDENTIFIER
                     | IDENTIFIER EQUALS expr'''
        dtype = getattr(self, '_current_decl_type', 'int')
        name  = p[1]
        if self.registry.is_declared_in_current_scope(name):
            self.issues.append(f"Error: '{name}' already declared in this scope")
        else:
            if len(p) == 2:
                self.registry.add(name, dtype, None)
                p[0] = ('decl', dtype, name)
            else:
                val = p[3]
                self.registry.add(name, dtype, val)
                self.emit('assign', val, None, name)
                p[0] = ('decl_init', dtype, name, val)

    # Inject type into decl_item via p_var_decl_multi hook
    def p_decl_type_inject(self, p):
        'decl_type_inject : data_type'
        self._current_decl_type = p[1]
        p[0] = p[1]

    # ── Function Declaration ──────────────────────────────────────────────────

    def p_func_decl(self, p):
        '''func_decl : data_type IDENTIFIER LPAREN param_list RPAREN code_block
                     | data_type IDENTIFIER LPAREN RPAREN code_block
                     | data_type MAIN LPAREN RPAREN code_block
                     | data_type MAIN LPAREN param_list RPAREN code_block'''
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

    # ── Return / break / continue ─────────────────────────────────────────────

    def p_return_stmt(self, p):
        '''return_stmt : RETURN expr SEMICOLON
                       | RETURN SEMICOLON'''
        if len(p) == 4:
            self.emit('return', p[2])
            p[0] = ('return', p[2])
        else:
            self.emit('return', None)
            p[0] = ('return', None)

    def p_break_stmt(self, p):
        'break_stmt : BREAK SEMICOLON'
        # Emit jump to nearest loop-end label
        if hasattr(self, '_loop_end_stack') and self._loop_end_stack:
            self.emit('jump', self._loop_end_stack[-1])
        else:
            self.emit('break', None)
        p[0] = ('break',)

    def p_continue_stmt(self, p):
        'continue_stmt : CONTINUE SEMICOLON'
        if hasattr(self, '_loop_start_stack') and self._loop_start_stack:
            self.emit('jump', self._loop_start_stack[-1])
        else:
            self.emit('continue', None)
        p[0] = ('continue',)

    # ── Expression statement ──────────────────────────────────────────────────

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

    def p_increment_stmt(self, p):
        '''increment_stmt : IDENTIFIER INCREMENT SEMICOLON
                          | IDENTIFIER DECREMENT SEMICOLON'''
        name = p[1]
        op   = '+' if p[2] == '++' else '-'
        tmp  = self.gen_temp()
        self.emit(op, name, 1, tmp)
        self.emit('assign', tmp, None, name)
        if self.registry.find(name):
            self.registry.update(name, tmp)
        p[0] = ('incr_stmt', name, p[2])

    def p_arg_list_many(self, p):
        'arg_list : arg_list COMMA expr'
        p[0] = p[1] + [p[3]]

    def p_arg_list_one(self, p):
        'arg_list : expr'
        p[0] = [p[1]]

    def p_arg_list_empty(self, p):
        'arg_list :'
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

    def p_compound_assign(self, p):
        '''compound_assign : IDENTIFIER PLUS_ASSIGN expr SEMICOLON
                           | IDENTIFIER MINUS_ASSIGN expr SEMICOLON
                           | IDENTIFIER MUL_ASSIGN expr SEMICOLON
                           | IDENTIFIER DIV_ASSIGN expr SEMICOLON'''
        name = p[1]
        op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
        op  = op_map[p[2]]
        tmp = self.gen_temp()
        self.emit(op, name, p[3], tmp)
        self.emit('assign', tmp, None, name)
        if self.registry.find(name):
            self.registry.update(name, tmp)
        p[0] = ('compound_assign', name, p[2], p[3])

    # ── Output ───────────────────────────────────────────────────────────────

    def p_output_stmt(self, p):
        'output_stmt : PRINT LPAREN expr RPAREN SEMICOLON'
        self.emit('output', p[3])
        p[0] = ('output', p[3])

    def p_printf_stmt(self, p):
        '''output_stmt : PRINTF LPAREN STRING_LIT RPAREN SEMICOLON
                       | PRINTF LPAREN STRING_LIT COMMA printf_args RPAREN SEMICOLON'''
        if len(p) == 6:
            self.emit('output', p[3])
            p[0] = ('printf', p[3])
        else:
            for arg in p[5]:
                self.emit('output', arg)
            p[0] = ('printf', p[3], p[5])

    def p_printf_args(self, p):
        '''printf_args : printf_args COMMA expr
                       | expr'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    # ── Input (scanf) ─────────────────────────────────────────────────────────

    def p_input_stmt(self, p):
        '''input_stmt : SCANF LPAREN STRING_LIT COMMA AMPERSAND IDENTIFIER RPAREN SEMICOLON
                      | SCANF LPAREN STRING_LIT COMMA scanf_args RPAREN SEMICOLON'''
        if len(p) == 9:
            name = p[6]
            self.emit('input', name, None, name)
            if not self.registry.find(name):
                self.issues.append(f"Warning: '{name}' used in scanf but not declared")
            p[0] = ('scanf', name)
        else:
            p[0] = ('scanf_multi', p[5])

    def p_scanf_args(self, p):
        '''scanf_args : scanf_args COMMA AMPERSAND IDENTIFIER
                      | AMPERSAND IDENTIFIER'''
        if len(p) == 5:
            name = p[4]
            self.emit('input', name, None, name)
            p[0] = p[1] + [name]
        else:
            name = p[2]
            self.emit('input', name, None, name)
            p[0] = [name]

    # ════════════════════════════════════════════════════════════════════════
    #  BODY — braced block OR single statement (braceless)
    # ════════════════════════════════════════════════════════════════════════

    def p_body_block(self, p):
        'body : code_block'
        p[0] = p[1]

    def p_body_single(self, p):
        '''body : var_assign
                | compound_assign
                | output_stmt
                | input_stmt
                | return_stmt
                | break_stmt
                | continue_stmt
                | increment_stmt
                | expr_stmt'''
        p[0] = ('single_stmt', p[1])

    # ── If / If-else (both braced and braceless) ──────────────────────────────

    def p_conditional_if(self, p):
        'conditional : IF LPAREN comparison RPAREN if_jump body if_end'
        p[0] = ('if', p[3], p[6])

    def p_conditional_ifelse(self, p):
        'conditional : IF LPAREN comparison RPAREN if_jump body else_jump ELSE body if_end'
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

    # ── While loop (braced and braceless) ────────────────────────────────────

    def p_loop(self, p):
        'loop : WHILE while_start LPAREN comparison RPAREN while_body body while_end'
        p[0] = ('while', p[4], p[7])

    def p_while_start(self, p):
        'while_start :'
        lbl_start = self.gen_label()
        self.emit('mark', lbl_start)
        self._while_start_stack = getattr(self, '_while_start_stack', [])
        self._while_start_stack.append(lbl_start)
        self._loop_start_stack  = getattr(self, '_loop_start_stack', [])
        self._loop_start_stack.append(lbl_start)
        p[0] = None

    def p_while_body(self, p):
        'while_body :'
        cond    = self._last_cond
        lbl_end = self.gen_label()
        self._while_end_stack = getattr(self, '_while_end_stack', [])
        self._while_end_stack.append(lbl_end)
        self._loop_end_stack  = getattr(self, '_loop_end_stack', [])
        self._loop_end_stack.append(lbl_end)
        self.emit('jump_if_false', cond, lbl_end)
        p[0] = None

    def p_while_end(self, p):
        'while_end :'
        lbl_start = self._while_start_stack.pop()
        lbl_end   = self._while_end_stack.pop()
        self._loop_start_stack.pop()
        self._loop_end_stack.pop()
        self.emit('jump', lbl_start)
        self.emit('mark', lbl_end)
        p[0] = None

    # ── For loop ─────────────────────────────────────────────────────────────

    def p_for_loop(self, p):
        'for_loop : FOR LPAREN for_init SEMICOLON for_mark_start comparison SEMICOLON for_update RPAREN for_body body for_end'
        p[0] = ('for', p[6], p[11])

    def p_for_init(self, p):
        '''for_init : data_type IDENTIFIER EQUALS expr
                    | IDENTIFIER EQUALS expr
                    | IDENTIFIER INCREMENT
                    | IDENTIFIER DECREMENT
                    | INCREMENT IDENTIFIER
                    | DECREMENT IDENTIFIER
                    |'''
        if len(p) == 5:
            dtype, name, val = p[1], p[2], p[4]
            if not self.registry.is_declared_in_current_scope(name):
                self.registry.add(name, dtype, val)
            self.emit('assign', val, None, name)
            p[0] = ('for_init_decl', dtype, name, val)
        elif len(p) == 4:
            name, val = p[1], p[3]
            self.emit('assign', val, None, name)
            p[0] = ('for_init_assign', name, val)
        elif len(p) == 3:
            if p[1] in ('++', '--'):
                name = p[2]; op = '+' if p[1] == '++' else '-'
            else:
                name = p[1]; op = '+' if p[2] == '++' else '-'
            tmp = self.gen_temp()
            self.emit(op, name, 1, tmp)
            self.emit('assign', tmp, None, name)
            p[0] = ('for_init_incr', name)
        else:
            p[0] = None

    def p_for_mark_start(self, p):
        'for_mark_start :'
        lbl = self.gen_label()
        self.emit('mark', lbl)
        self._for_start_stack = getattr(self, '_for_start_stack', [])
        self._for_start_stack.append(lbl)
        self._loop_start_stack = getattr(self, '_loop_start_stack', [])
        self._loop_start_stack.append(lbl)
        p[0] = None

    def p_for_update(self, p):
        '''for_update : IDENTIFIER EQUALS expr
                      | IDENTIFIER INCREMENT
                      | IDENTIFIER DECREMENT
                      | INCREMENT IDENTIFIER
                      | DECREMENT IDENTIFIER
                      | IDENTIFIER PLUS_ASSIGN expr
                      | IDENTIFIER MINUS_ASSIGN expr
                      | IDENTIFIER MUL_ASSIGN expr
                      | IDENTIFIER DIV_ASSIGN expr
                      |'''
        self._for_update_instrs = []
        if len(p) == 4 and p[2] == '=':
            self._for_update_instrs = [('assign', p[3], None, p[1])]
            p[0] = ('for_update_assign', p[1], p[3])
        elif len(p) == 3:
            if p[1] in ('++', '--'):
                name = p[2]; op = '+' if p[1] == '++' else '-'
            else:
                name = p[1]; op = '+' if p[2] == '++' else '-'
            tmp = f"_fu{self.tmp_counter+1}"
            self._for_update_instrs = [(op, name, 1, tmp), ('assign', tmp, None, name)]
            p[0] = ('for_update_incr', name)
        elif len(p) == 4:
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            op  = op_map.get(p[2], '+')
            tmp = f"_fu{self.tmp_counter+1}"
            self._for_update_instrs = [(op, p[1], p[3], tmp), ('assign', tmp, None, p[1])]
            p[0] = ('for_update_compound', p[1], p[2], p[3])
        else:
            p[0] = None

    def p_for_body(self, p):
        'for_body :'
        cond    = self._last_cond
        lbl_end = self.gen_label()
        self._for_end_stack  = getattr(self, '_for_end_stack', [])
        self._for_end_stack.append(lbl_end)
        self._loop_end_stack = getattr(self, '_loop_end_stack', [])
        self._loop_end_stack.append(lbl_end)
        self.emit('jump_if_false', cond, lbl_end)
        p[0] = None

    def p_for_end(self, p):
        'for_end :'
        for instr in getattr(self, '_for_update_instrs', []):
            self.ir_instructions.append(
                {'op': instr[0], 'src1': instr[1], 'src2': instr[2], 'dst': instr[3]}
            )
        lbl_start = self._for_start_stack.pop()
        lbl_end   = self._for_end_stack.pop()
        self._loop_start_stack.pop()
        self._loop_end_stack.pop()
        self.emit('jump', lbl_start)
        self.emit('mark', lbl_end)
        p[0] = None

    # ── Blocks ───────────────────────────────────────────────────────────────

    def p_code_block(self, p):
        'code_block : block_start stmt_sequence block_end'
        p[0] = ('block', p[2])

    def p_block_start(self, p):
        'block_start : LBRACE'
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

    def p_comparison_expr(self, p):
        'comparison : expr'
        self._last_cond = p[1]
        p[0] = p[1]

    def p_rel_op(self, p):
        '''rel_op : LESS
                  | LESS_EQ
                  | GREATER
                  | GREATER_EQ
                  | EQUAL_TO
                  | NOT_EQUAL'''
        p[0] = p[1]

    # ── Expressions ──────────────────────────────────────────────────────────

    def p_expr_or(self, p):
        'expr : expr OR expr'
        tmp = self.gen_temp()
        self.emit('||', p[1], p[3], tmp)
        p[0] = tmp

    def p_expr_and(self, p):
        'expr : expr AND expr'
        tmp = self.gen_temp()
        self.emit('&&', p[1], p[3], tmp)
        p[0] = tmp

    def p_expr_not(self, p):
        'expr : NOT expr'
        tmp = self.gen_temp()
        self.emit('!', p[2], None, tmp)
        p[0] = tmp

    def p_expr_add(self, p):
        '''expr : expr PLUS term
                | expr MINUS term'''
        tmp = self.gen_temp()
        self.emit(p[2], p[1], p[3], tmp)
        p[0] = tmp

    def p_expr_cmp(self, p):
        '''expr : expr EQUAL_TO expr
                | expr NOT_EQUAL expr
                | expr LESS expr
                | expr LESS_EQ expr
                | expr GREATER expr
                | expr GREATER_EQ expr'''
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

    def p_base_string(self, p):
        'base : STRING_LIT'
        p[0] = p[1]

    def p_base_uminus(self, p):
        'base : MINUS base %prec UMINUS'
        tmp = self.gen_temp()
        self.emit('*', p[2], -1, tmp)
        p[0] = tmp

    def p_base_id(self, p):
        'base : IDENTIFIER'
        if not self.registry.find(p[1]):
            self.issues.append(f"Error: Undefined variable '{p[1]}'")
        p[0] = p[1]

    def p_base_increment(self, p):
        '''base : IDENTIFIER INCREMENT
               | IDENTIFIER DECREMENT'''
        name = p[1]
        op   = '+' if p[2] == '++' else '-'
        tmp  = self.gen_temp()
        self.emit(op, name, 1, tmp)
        self.emit('assign', tmp, None, name)
        if self.registry.find(name):
            self.registry.update(name, tmp)
        p[0] = name

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
        import logging
        logging.getLogger('ply').setLevel(logging.CRITICAL)
        self.processor = yacc.yacc(
            module=self,
            debug=False,
            write_tables=False,
            errorlog=yacc.NullLogger(),
        )

    def process(self, code: str):
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
        self._for_start_stack   = []
        self._for_end_stack     = []
        self._for_update_instrs = []
        self._loop_start_stack  = []
        self._loop_end_stack    = []
        self.registry.clear()
        return self.processor.parse(code)