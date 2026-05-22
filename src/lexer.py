import ply.lex as lex

class TokenScanner:
    """Lexical analyzer for scanning and tokenizing source code"""

    keywords = {
        'if':     'IF',
        'else':   'ELSE',
        'while':  'WHILE',
        'for':    'FOR',
        'int':    'INT',
        'float':  'FLOAT',
        'return': 'RETURN',
        'print':  'PRINT',
    }

    tokens = [
        'IDENTIFIER', 'INTEGER', 'DECIMAL',
        'PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE', 'MOD',
        'EQUALS',
        'EQUAL_TO', 'NOT_EQUAL',
        'LESS_EQ', 'GREATER_EQ', 'LESS', 'GREATER',
        'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
        'SEMICOLON', 'COMMA',
    ] + list(keywords.values())

    # ── Single-line comment ──────────────────────────────────────────────────
    def t_COMMENT_SINGLE(self, tok):
        r'//[^\n]*'
        pass  # discard

    # ── Multi-line comment ───────────────────────────────────────────────────
    def t_COMMENT_MULTI(self, tok):
        r'/\*(.|\n)*?\*/'
        tok.lexer.lineno += tok.value.count('\n')
        pass  # discard

    # ── Two-char operators (must appear BEFORE single-char versions) ─────────
    t_EQUAL_TO   = r'=='
    t_NOT_EQUAL  = r'!='
    t_LESS_EQ    = r'<='
    t_GREATER_EQ = r'>='

    # ── Single-char operators ────────────────────────────────────────────────
    t_PLUS      = r'\+'
    t_MINUS     = r'-'
    t_MULTIPLY  = r'\*'
    t_DIVIDE    = r'/'
    t_MOD       = r'%'
    t_EQUALS    = r'='
    t_LESS      = r'<'
    t_GREATER   = r'>'

    # ── Delimiters ───────────────────────────────────────────────────────────
    t_LPAREN    = r'\('
    t_RPAREN    = r'\)'
    t_LBRACE    = r'\{'
    t_RBRACE    = r'\}'
    t_SEMICOLON = r';'
    t_COMMA     = r','

    t_ignore = ' \t'

    # ── Literals ─────────────────────────────────────────────────────────────
    def t_DECIMAL(self, tok):
        r'\d+\.\d+'
        tok.value = float(tok.value)
        return tok

    def t_INTEGER(self, tok):
        r'\d+'
        tok.value = int(tok.value)
        return tok

    def t_IDENTIFIER(self, tok):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        tok.type = self.keywords.get(tok.value, 'IDENTIFIER')
        return tok

    def t_newline(self, tok):
        r'\n+'
        tok.lexer.lineno += len(tok.value)

    def t_error(self, tok):
        self.issues.append(
            f"Line {tok.lineno}: Invalid character '{tok.value[0]}'"
        )
        tok.lexer.skip(1)

    # ── Public API ───────────────────────────────────────────────────────────
    def __init__(self):
        self.scanner = None
        self.token_stream = []
        self.issues = []

    def initialize(self):
        """Build the PLY lexer."""
        self.scanner = lex.lex(module=self)

    def scan(self, code: str):
        """
        Tokenize *code*.

        Returns
        -------
        token_stream : list[dict]   – one dict per token
        issues       : list[str]    – lexical error messages
        """
        self.token_stream = []
        self.issues = []
        self.scanner.lineno = 1          # reset line counter for each run
        self.scanner.input(code)

        while True:
            tok = self.scanner.token()
            if not tok:
                break
            self.token_stream.append({
                'kind': tok.type,
                'val':  tok.value,
                'ln':   tok.lineno,
                'pos':  tok.lexpos,
            })

        return self.token_stream, self.issues