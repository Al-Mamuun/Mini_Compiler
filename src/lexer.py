import ply.lex as lex

class TokenScanner:
    """Lexical analyzer — supports both LexiCore syntax and C-style code."""

    keywords = {
        'if':       'IF',
        'else':     'ELSE',
        'while':    'WHILE',
        'for':      'FOR',
        'int':      'INT',
        'float':    'FLOAT',
        'void':     'VOID',
        'return':   'RETURN',
        'print':    'PRINT',
        'scanf':    'SCANF',
        'printf':   'PRINTF',
        'break':    'BREAK',
        'continue': 'CONTINUE',
        'char':     'CHAR',
        'double':   'DOUBLE',
        'long':     'LONG',
        'short':    'SHORT',
        'unsigned': 'UNSIGNED',
        'main':     'MAIN',
    }

    tokens = [
        'IDENTIFIER', 'INTEGER', 'DECIMAL',
        'STRING_LIT',
        'PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE', 'MOD',
        'EQUALS',
        'EQUAL_TO', 'NOT_EQUAL',
        'LESS_EQ', 'GREATER_EQ', 'LESS', 'GREATER',
        'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
        'LBRACKET', 'RBRACKET',
        'SEMICOLON', 'COMMA',
        'AND', 'OR', 'NOT',
        'INCREMENT', 'DECREMENT',
        'PLUS_ASSIGN', 'MINUS_ASSIGN', 'MUL_ASSIGN', 'DIV_ASSIGN',
        'AMPERSAND',
        'HASH',
        'DOT',
    ] + list(keywords.values())

    # ── Preprocessor lines (#include, #define) — skip entirely ──────────────
    def t_PREPROCESSOR(self, tok):
        r'\#[^\n]*'
        pass  # discard preprocessor directives

    # ── Single-line comment ──────────────────────────────────────────────────
    def t_COMMENT_SINGLE(self, tok):
        r'//[^\n]*'
        pass

    # ── Multi-line comment ───────────────────────────────────────────────────
    def t_COMMENT_MULTI(self, tok):
        r'/\*(.|\n)*?\*/'
        tok.lexer.lineno += tok.value.count('\n')
        pass

    # ── String literals ──────────────────────────────────────────────────────
    def t_STRING_LIT(self, tok):
        r'"([^"\\]|\\.)*"'
        return tok

    # ── Three / two-char operators (must appear BEFORE shorter ones) ─────────
    t_AND           = r'&&'
    t_OR            = r'\|\|'
    t_INCREMENT     = r'\+\+'
    t_DECREMENT     = r'--'
    t_PLUS_ASSIGN   = r'\+='
    t_MINUS_ASSIGN  = r'-='
    t_MUL_ASSIGN    = r'\*='
    t_DIV_ASSIGN    = r'/='
    t_EQUAL_TO      = r'=='
    t_NOT_EQUAL     = r'!='
    t_LESS_EQ       = r'<='
    t_GREATER_EQ    = r'>='

    # ── Single-char operators ────────────────────────────────────────────────
    t_PLUS          = r'\+'
    t_MINUS         = r'-'
    t_MULTIPLY      = r'\*'
    t_DIVIDE        = r'/'
    t_MOD           = r'%'
    t_EQUALS        = r'='
    t_LESS          = r'<'
    t_GREATER       = r'>'
    t_NOT           = r'!'
    t_AMPERSAND     = r'&'
    t_DOT           = r'\.'

    # ── Delimiters ───────────────────────────────────────────────────────────
    t_LPAREN        = r'\('
    t_RPAREN        = r'\)'
    t_LBRACE        = r'\{'
    t_RBRACE        = r'\}'
    t_LBRACKET      = r'\['
    t_RBRACKET      = r'\]'
    t_SEMICOLON     = r';'
    t_COMMA         = r','
    t_HASH          = r'\#'

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
        self.scanner = lex.lex(module=self)

    def scan(self, code: str):
        self.token_stream = []
        self.issues = []
        self.scanner.lineno = 1
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