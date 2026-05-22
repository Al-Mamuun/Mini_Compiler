class AssemblyTranslator:
    """
    Translates three-address IR to pseudo-assembly.

    Improvements over the original
    ───────────────────────────────
    • Comparison ops now emit the correct conditional-set instruction
      (SETE, SETL, SETG, …) rather than a generic SETCC.
    • IDIV sequence emits the required CDQ (sign-extend) and uses the
      correct register convention (EAX / EDX).
    • MOD is handled as a separate IDIV + MOV-from-EDX sequence.
    • Operand source detection uses a helper so it's easier to extend.
    • Assembly header has a minimal NASM-compatible structure.
    """

    # Map IR relational operators → x86 SETcc mnemonics
    _SETCC = {
        '==': 'SETE',
        '!=': 'SETNE',
        '<':  'SETL',
        '<=': 'SETLE',
        '>':  'SETG',
        '>=': 'SETGE',
    }

    # Map IR relational operators → x86 conditional-jump mnemonics
    # (used when we inline the comparison into a branch)
    _JCC = {
        '==': 'JE',
        '!=': 'JNE',
        '<':  'JL',
        '<=': 'JLE',
        '>':  'JG',
        '>=': 'JGE',
    }

    _ARITH = {
        '+': 'ADD',
        '-': 'SUB',
        '*': 'IMUL',
    }

    def __init__(self):
        self.asm_output = []
        self._regs      = ['EBX', 'ECX', 'ESI', 'EDI']   # caller-preserved
        self._reg_alloc = {}
        self._reg_idx   = 0

    # ── Register allocation (trivial round-robin) ────────────────────────────

    def _alloc(self, var) -> str:
        """Return (and remember) a register for *var*."""
        if var not in self._reg_alloc:
            reg = self._regs[self._reg_idx % len(self._regs)]
            self._reg_idx += 1
            self._reg_alloc[var] = reg
        return self._reg_alloc[var]

    def _operand(self, v) -> str:
        """
        Return the assembly operand for an IR value:
          - numeric literal → immediate string  e.g. '42'
          - named variable  → its register      e.g. 'EBX'
        """
        if isinstance(v, (int, float)):
            return str(v)
        if v is None:
            return '??'
        return self._alloc(str(v))

    # ── Public API ───────────────────────────────────────────────────────────

    def translate(self, ir_code: list) -> list:
        """
        Convert a list of IR instruction dicts to assembly lines.

        Each dict has keys: op, src1, src2, dst.
        """
        self.asm_output  = []
        self._reg_alloc  = {}
        self._reg_idx    = 0

        out = self.asm_output
        out.append('; ── Generated Assembly ─────────────────────────────')
        out.append('section .data')
        out.append('    fmt_int  db "%d", 10, 0')
        out.append('section .text')
        out.append('    global main')
        out.append('    extern printf')
        out.append('')
        out.append('main:')
        out.append('    PUSH    EBP')
        out.append('    MOV     EBP, ESP')

        for instr in ir_code:
            op, s1, s2, dst = (instr['op'], instr['src1'],
                               instr['src2'], instr['dst'])
            self._emit_instr(op, s1, s2, dst)

        out.append('')
        out.append('.exit:')
        out.append('    XOR     EAX, EAX')
        out.append('    MOV     ESP, EBP')
        out.append('    POP     EBP')
        out.append('    RET')
        return out

    # ── Internal emission helpers ────────────────────────────────────────────

    def _emit_instr(self, op, s1, s2, dst):
        out = self.asm_output
        a   = self._operand

        # ── Labels / jumps ──────────────────────────────────────────────
        if op == 'mark':
            out.append(f'\n{s1}:')
            return
        if op == 'jump':
            out.append(f'    JMP     {s1}')
            return
        if op == 'jump_if_false':
            r = a(s1)
            out.append(f'    CMP     {r}, 0')
            out.append(f'    JE      {s2}')
            return

        # ── Assignment ──────────────────────────────────────────────────
        if op == 'assign':
            r_dst = a(dst)
            r_src = a(s1)
            out.append(f'    MOV     {r_dst}, {r_src}')
            return

        # ── Arithmetic: + - * ───────────────────────────────────────────
        if op in self._ARITH:
            r1    = a(s1)
            r2    = a(s2)
            r_res = a(dst)
            mnem  = self._ARITH[op]
            out.append(f'    MOV     EAX, {r1}')
            out.append(f'    {mnem:<7} EAX, {r2}')
            out.append(f'    MOV     {r_res}, EAX')
            return

        # ── Division ────────────────────────────────────────────────────
        if op == '/':
            r1    = a(s1)
            r2    = a(s2)
            r_res = a(dst)
            out.append(f'    MOV     EAX, {r1}')
            out.append( '    CDQ')                    # sign-extend EAX→EDX:EAX
            out.append(f'    IDIV    {r2}')
            out.append(f'    MOV     {r_res}, EAX')   # quotient in EAX
            return

        # ── Modulo ──────────────────────────────────────────────────────
        if op == '%':
            r1    = a(s1)
            r2    = a(s2)
            r_res = a(dst)
            out.append(f'    MOV     EAX, {r1}')
            out.append( '    CDQ')
            out.append(f'    IDIV    {r2}')
            out.append(f'    MOV     {r_res}, EDX')   # remainder in EDX
            return

        # ── Comparisons ─────────────────────────────────────────────────
        if op in self._SETCC:
            r1    = a(s1)
            r2    = a(s2)
            r_res = a(dst)
            setcc = self._SETCC[op]
            out.append(f'    CMP     {r1}, {r2}')
            out.append(f'    {setcc:<7} AL')
            out.append( '    MOVZX   EAX, AL')
            out.append(f'    MOV     {r_res}, EAX')
            return

        # ── Print / output ──────────────────────────────────────────────
        if op == 'output':
            r = a(s1)
            out.append(f'    PUSH    {r}')
            out.append( '    PUSH    fmt_int')
            out.append( '    CALL    printf')
            out.append( '    ADD     ESP, 8')
            return

        # ── Unknown op (safety net) ─────────────────────────────────────
        out.append(f'    ; [unhandled op: {op}]')

    # ── Function-related helpers (appended) ──────────────────────────────────
    # These are called from _emit_instr via the function op dispatcher below.
    # We patch _emit_instr at the bottom of the file via monkey-extension.

def _patched_emit_instr(self, op, s1, s2, dst):
    """Extends AssemblyTranslator._emit_instr with function-related ops."""
    out = self.asm_output
    a   = self._operand

    if op == 'func_begin':
        out.append(f'\n; ── function: {s1}  (returns {s2}) ──')
        out.append(f'{s1}:')
        out.append('    PUSH    EBP')
        out.append('    MOV     EBP, ESP')
        return

    if op == 'param':
        reg = self._alloc(s1)
        param_keys = [k for k in self._reg_alloc if k == s1]
        idx = list(self._reg_alloc.keys()).index(s1)
        offset = 8 + idx * 4
        out.append(f'    MOV     {reg}, [EBP+{offset}]  ; param {s1}:{s2}')
        return

    if op == 'arg':
        r = a(s1)
        out.append(f'    PUSH    {r}')
        return

    if op == 'call':
        out.append(f'    CALL    {s1}')
        if s2 and int(s2) > 0:
            out.append(f'    ADD     ESP, {int(s2) * 4}')
        if dst:
            r_dst = self._alloc(str(dst))
            out.append(f'    MOV     {r_dst}, EAX')
        return

    if op == 'return':
        if s1 is not None:
            r = a(s1)
            out.append(f'    MOV     EAX, {r}')
        out.append('    MOV     ESP, EBP')
        out.append('    POP     EBP')
        out.append('    RET')
        return

    # Delegate to original
    _original_emit_instr(self, op, s1, s2, dst)

_original_emit_instr = AssemblyTranslator._emit_instr
AssemblyTranslator._emit_instr = _patched_emit_instr