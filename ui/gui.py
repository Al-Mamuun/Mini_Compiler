import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import re

from lexer          import TokenScanner
from parser         import SyntaxProcessor
from code_generator import AssemblyTranslator
from grammar_utils  import (remove_left_recursion, left_factoring,
                             format_grammar, compute_first, compute_follow,
                             format_first_follow)
from symbol_table   import VariableRegistry
from semantic       import semantic_analysis, CHECKS
from syntax_analysis import run_syntax_analysis

# ─────────────────────────────────────────────────────────────────────────────
#  Colour palette  ── refined dark theme (screenshot-matched)
# ─────────────────────────────────────────────────────────────────────────────
C = {
    'bg':          '#282A36',
    'bg2':         '#21222C',
    'bg3':         '#282A36',
    'bg_card':     '#21222C',
    'border':      '#44475A',
    'border2':     '#44475A',
    'accent':      '#50FA7B',
    'accent2':     '#8BE9FD',
    'accent3':     '#FF5555',
    'accent4':     '#FFB86C',
    'dim':         '#44475A',
    'text':        '#F8F8F2',
    'text_dim':    '#6272A4',
    'text_bright': '#FFFFFF',
    'purple':      '#BD93F9',
    'pink':        '#FF79C6',
    'yellow':      '#F1FA8C',
    'cyan':        '#8BE9FD',
    'teal':        '#50FA7B',
    'sidebar':     '#21222C',
    'editor':      '#282A36',
    'panel':       '#21222C',
    'selection':   '#44475A',
    'active_tab':  '#282A36',
    'inactive_tab':'#21222C',
    'statusbar':   '#BD93F9',
    'green':       '#50FA7B',
    'orange':      '#FFB86C',
    'red':         '#FF5555',
    'tab_line':    '#8BE9FD',
}

FONT_MONO   = ('Consolas', 11)
FONT_MONO_S = ('Consolas', 12)      # output panel font — bigger & easier to read
FONT_MONO_L = ('Consolas', 13, 'bold')
FONT_UI     = ('Segoe UI', 10)
FONT_UI_B   = ('Segoe UI', 10, 'bold')
FONT_CARD_N = ('Segoe UI', 28, 'bold')
FONT_CARD_L = ('Segoe UI', 8)


# ─────────────────────────────────────────────────────────────────────────────
#  Code Snippets
# ─────────────────────────────────────────────────────────────────────────────
SNIPPETS = [
    ("Hello", "int x;\nx = 42;\nprint(x);\n"),
    ("Factorial", "int n;\nint result;\nn = 5;\nresult = 1;\nwhile (n > 0) {\n    result = result * n;\n    n = n - 1;\n}\nprint(result);\n"),
    ("Sum 1-N", "int n;\nint i;\nint sum;\nn = 10;\ni = 1;\nsum = 0;\nwhile (i <= n) {\n    sum = sum + i;\n    i = i + 1;\n}\nprint(sum);\n"),
    ("Max of 2", "int a;\nint b;\nint mx;\na = 17;\nb = 42;\nif (a > b) {\n    mx = a;\n}\nif (b >= a) {\n    mx = b;\n}\nprint(mx);\n"),
    ("Even/Odd", "int n;\nint r;\nn = 7;\nr = n - (n / 2) * 2;\nif (r == 0) {\n    print(0);\n}\nif (r != 0) {\n    print(1);\n}\n"),
    ("Power", "int base;\nint exp;\nint res;\nbase = 2;\nexp = 8;\nres = 1;\nwhile (exp > 0) {\n    res = res * base;\n    exp = exp - 1;\n}\nprint(res);\n"),
    ("Bubble Sort", "int a;\nint b;\nint c;\nint tmp;\na = 9;\nb = 3;\nc = 7;\nif (a > b) { tmp = a; a = b; b = tmp; }\nif (b > c) { tmp = b; b = c; c = tmp; }\nif (a > b) { tmp = a; a = b; b = tmp; }\nprint(a);\nprint(b);\nprint(c);\n"),
    ("Counter", "int i;\nint limit;\nlimit = 5;\ni = 0;\nwhile (i < limit) {\n    print(i);\n    i = i + 1;\n}\n"),
    ("Swap", "int x;\nint y;\nint tmp;\nx = 10;\ny = 20;\ntmp = x;\nx = y;\ny = tmp;\nprint(x);\nprint(y);\n"),
    ("FizzBuzz", "int i;\nint r3;\nint r5;\ni = 1;\nwhile (i <= 15) {\n    r3 = i - (i / 3) * 3;\n    r5 = i - (i / 5) * 5;\n    if (r3 == 0) { print(3); }\n    if (r5 == 0) { print(5); }\n    if (r3 != 0) {\n        if (r5 != 0) { print(i); }\n    }\n    i = i + 1;\n}\n"),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Syntax highlighter
# ─────────────────────────────────────────────────────────────────────────────
class SyntaxHighlighter:
    def __init__(self, widget):
        self.w = widget
        defs = {
            'keyword':  {'foreground': '#FF7B72'},
            'type':     {'foreground': '#58A6FF'},
            'number':   {'foreground': '#BC8CFF'},
            'string':   {'foreground': '#E3B341'},
            'comment':  {'foreground': '#484F58', 'font': ('Consolas', 11, 'italic')},
            'operator': {'foreground': '#FF7B72'},
            'function': {'foreground': '#3FB950', 'font': ('Consolas', 11, 'bold')},
            'variable': {'foreground': '#C9D1D9'},
        }
        for tag, cfg in defs.items():
            self.w.tag_config(tag, **cfg)

    def highlight(self, event=None):
        content = self.w.get('1.0', 'end-1c')
        for tag in ['keyword','type','number','string','comment','operator','function','variable']:
            self.w.tag_remove(tag, '1.0', 'end')

        def mark(pattern, tag, flags=0):
            for m in re.finditer(pattern, content, flags):
                self.w.tag_add(tag, f'1.0+{m.start()}c', f'1.0+{m.end()}c')

        mark(r'\b(int|if|else|while|print|return|void|char|float|double)\b', 'keyword')
        mark(r'\b\d+(\.\d+)?\b', 'number')
        mark(r'//.*?$', 'comment', re.MULTILINE)
        mark(r'/\*.*?\*/', 'comment', re.DOTALL)
        mark(r'[+\-*/%=<>!&|]+', 'operator')
        mark(r'\b(\w+)\s*\(', 'function')


# ─────────────────────────────────────────────────────────────────────────────
#  NeonButton  ── polished with glow pulse on hover
# ─────────────────────────────────────────────────────────────────────────────
class NeonButton(tk.Canvas):
    def __init__(self, parent, text, command, color=None, **kwargs):
        w     = kwargs.pop('width',  94)
        h     = kwargs.pop('height', 28)
        color = color or C['accent']
        super().__init__(parent, width=w, height=h, bg=C['bg2'],
                         highlightthickness=0, cursor='hand2', **kwargs)
        self.command = command
        self.color   = color
        self.w, self.h = w, h
        self._hovered = False

        # subtle dark fill so text is always readable
        self._bg_fill = self.create_rectangle(
            2, 2, w-2, h-2,
            outline='', fill=C['bg2'])
        # border rectangle (rounded feel via slight inset)
        self._border = self.create_rectangle(
            1, 1, w-1, h-1,
            outline=color, width=1, fill='')
        # top accent line for depth
        self._top_line = self.create_line(
            3, 1, w-3, 1, fill=color, width=1)
        # label
        self._text = self.create_text(
            w//2, h//2, text=text,
            fill=color, font=('Consolas', 9, 'bold'))

        self.bind('<Enter>',    self._on_enter)
        self.bind('<Leave>',    self._on_leave)
        self.bind('<Button-1>', self._on_click)

    def _on_enter(self, _=None):
        self._hovered = True
        # flood-fill with color, darken text to bg
        self.itemconfig(self._bg_fill, fill=self.color)
        self.itemconfig(self._border,  outline=self.color, fill=self.color)
        self.itemconfig(self._top_line, fill=C['text_bright'])
        self.itemconfig(self._text,    fill=C['bg'])

    def _on_leave(self, _=None):
        self._hovered = False
        self.itemconfig(self._bg_fill, fill=C['bg2'])
        self.itemconfig(self._border,  outline=self.color, fill='')
        self.itemconfig(self._top_line, fill=self.color)
        self.itemconfig(self._text,    fill=self.color)

    def _on_click(self, _=None):
        self.itemconfig(self._border, outline=C['text_bright'])
        self.after(140, lambda: self.itemconfig(
            self._border, outline=self.color if not self._hovered else self.color))
        self.command()


# ─────────────────────────────────────────────────────────────────────────────
#  LL1 NeonButton  ── slightly larger variant for the LL(1) toolbar
# ─────────────────────────────────────────────────────────────────────────────
class LL1Button(tk.Canvas):
    """Wider, taller NeonButton for the LL(1) window toolbar."""
    def __init__(self, parent, text, command, color=None, width=120, height=30):
        color = color or C['accent']
        super().__init__(parent, width=width, height=height, bg=C['bg2'],
                         highlightthickness=0, cursor='hand2')
        self.command = command
        self.color   = color
        w, h         = width, height

        self._bg   = self.create_rectangle(2, 2, w-2, h-2, outline='', fill=C['bg2'])
        self._brd  = self.create_rectangle(1, 1, w-1, h-1, outline=color, width=1, fill='')
        self._tl   = self.create_line(3, 1, w-3, 1, fill=color, width=2)
        self._lbl  = self.create_text(w//2, h//2, text=text,
                                      fill=color, font=('Consolas', 9, 'bold'))

        self.bind('<Enter>',    self._enter)
        self.bind('<Leave>',    self._leave)
        self.bind('<Button-1>', self._click)

    def _enter(self, _=None):
        self.itemconfig(self._bg,  fill=self.color)
        self.itemconfig(self._brd, fill=self.color, outline=self.color)
        self.itemconfig(self._tl,  fill=C['text_bright'])
        self.itemconfig(self._lbl, fill=C['bg'])

    def _leave(self, _=None):
        self.itemconfig(self._bg,  fill=C['bg2'])
        self.itemconfig(self._brd, fill='', outline=self.color)
        self.itemconfig(self._tl,  fill=self.color)
        self.itemconfig(self._lbl, fill=self.color)

    def _click(self, _=None):
        self.itemconfig(self._brd, outline=C['text_bright'])
        self.after(140, lambda: self.itemconfig(self._brd, outline=self.color))
        self.command()


# ─────────────────────────────────────────────────────────────────────────────
#  SnippetButton  ── brighter, more visible
# ─────────────────────────────────────────────────────────────────────────────
class SnippetButton(tk.Canvas):
    def __init__(self, parent, label, command):
        tw = max(68, len(label) * 7 + 24)
        super().__init__(parent, width=tw, height=22,
                         bg=C['bg2'], highlightthickness=0, cursor='hand2')
        self._rect = self.create_rectangle(1, 1, tw-1, 21,
                                           outline=C['border2'], width=1, fill='#1E1F2B')
        # top accent line
        self._top  = self.create_line(2, 1, tw-2, 1, fill=C['border2'], width=1)
        self._txt  = self.create_text(tw//2, 11, text=label,
                                      fill='#8899BB', font=('Consolas', 8, 'bold'))
        self.bind('<Enter>',    self._enter)
        self.bind('<Leave>',    self._leave)
        self.bind('<Button-1>', lambda _: command())

    def _enter(self, _=None):
        self.itemconfig(self._rect, outline=C['accent4'], fill='#2A2030')
        self.itemconfig(self._top,  fill=C['accent4'])
        self.itemconfig(self._txt,  fill=C['accent4'])

    def _leave(self, _=None):
        self.itemconfig(self._rect, outline=C['border2'], fill='#1E1F2B')
        self.itemconfig(self._top,  fill=C['border2'])
        self.itemconfig(self._txt,  fill='#8899BB')


# ─────────────────────────────────────────────────────────────────────────────
#  ToolButton
# ─────────────────────────────────────────────────────────────────────────────
class ToolButton(tk.Canvas):
    def __init__(self, parent, text, command, icon='', color='#21262D', width=85):
        super().__init__(parent, height=24, width=width,
                         highlightthickness=0, bg=color, cursor='hand2')
        self._base  = color
        self._alpha = 0
        self._aid   = None
        self._rect  = self.create_rectangle(0, 0, width, 24, fill=color, outline='')
        label = f'{icon}  {text}' if icon else text
        self.create_text(width // 2, 12, text=label, fill=C['text'], font=FONT_UI)
        self.bind('<Button-1>', lambda _: command())
        self.bind('<Enter>',    lambda _: self._anim(True))
        self.bind('<Leave>',    lambda _: self._anim(False))

    def _anim(self, entering):
        if self._aid:
            self.after_cancel(self._aid)
        tgt = 25 if entering else 0
        if self._alpha == tgt:
            return
        self._alpha = max(0, min(25, self._alpha + (5 if entering else -5)))
        b = self._base.lstrip('#')
        r, g, bl = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
        f = 1 + self._alpha / 100
        self.itemconfig(self._rect,
                        fill=f'#{min(int(r*f),255):02x}{min(int(g*f),255):02x}{min(int(bl*f),255):02x}')
        self._aid = self.after(16, lambda: self._anim(entering))


# ─────────────────────────────────────────────────────────────────────────────
#  SidebarButton  ── colorful pill design with left accent bar
# ─────────────────────────────────────────────────────────────────────────────
class SidebarButton(tk.Canvas):
    """
    Each button has:
      • a colored left-edge accent bar (3 px, always visible)
      • icon + short label centered
      • on hover: pill background fills with a tinted version of the accent
    """
    def __init__(self, parent, icon, label, tooltip, command, color=None):
        W, H = 52, 48
        color = color or C['accent']
        super().__init__(parent, width=W, height=H,
                         highlightthickness=0, bg=C['bg2'], cursor='hand2')
        self._color    = color
        self._tip_win  = None
        self._tooltip  = tooltip
        self._aid      = None
        self._hovering = False

        # left accent bar (always on)
        self.create_rectangle(0, 4, 3, H-4, fill=color, outline='', tags='bar')

        # hover pill background (initially same as bg)
        self._pill = self.create_rectangle(4, 3, W-3, H-3,
                                           fill=C['bg2'], outline='', tags='pill')

        # icon (big)
        self._ico = self.create_text(W//2 + 2, H//2 - 5, text=icon,
                                     font=('Segoe UI', 13),
                                     fill=color, tags='ico')
        # label (tiny, below icon)
        self._lbl = self.create_text(W//2 + 2, H//2 + 9, text=label,
                                     font=('Consolas', 6, 'bold'),
                                     fill=color, tags='lbl')

        self.bind('<Button-1>', lambda _: command())
        self.bind('<Enter>',    self._on_enter)
        self.bind('<Leave>',    self._on_leave)

    def _on_enter(self, event):
        self._hovering = True
        self._animate_to(40)
        self._show_tip()

    def _on_leave(self, _):
        self._hovering = False
        self._animate_to(0)
        if self._tip_win:
            self._tip_win.destroy()
            self._tip_win = None

    def _show_tip(self):
        if self._tip_win:
            return
        x = self.winfo_rootx() + 56
        y = self.winfo_rooty() + 14
        self._tip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        tk.Label(tw, text=self._tooltip,
                 bg='#2D2F3F', fg=C['text'],
                 font=('Segoe UI', 9), padx=8, pady=4,
                 relief='flat').pack()

    # interpolate pill background from bg2 toward a tinted accent
    def _animate_to(self, target):
        if self._aid:
            self.after_cancel(self._aid)
        self._aid = self.after(0, self._step, target)

    def _step(self, target):
        # current pill color
        try:
            cur_hex = self.itemcget(self._pill, 'fill').lstrip('#')
        except Exception:
            return
        # parse RGB
        try:
            cr, cg, cb = int(cur_hex[0:2],16), int(cur_hex[2:4],16), int(cur_hex[4:6],16)
        except Exception:
            cr, cg, cb = 0x21, 0x22, 0x2C

        # target color: blend accent color at ~18% opacity over bg2
        ac = self._color.lstrip('#')
        ar, ag, ab = int(ac[0:2],16), int(ac[2:4],16), int(ac[4:6],16)
        bg = C['bg2'].lstrip('#')
        br, bg2r, bb = int(bg[0:2],16), int(bg[2:4],16), int(bg[4:6],16)

        if target > 0:
            # tinted pill color
            t = 0.18
            tr = int(ar*t + br*(1-t))
            tg = int(ag*t + bg2r*(1-t))
            tb = int(ab*t + bb*(1-t))
        else:
            tr, tg, tb = br, bg2r, bb

        # ease toward target
        speed = 0.25
        nr = int(cr + (tr - cr) * speed)
        ng = int(cg + (tg - cg) * speed)
        nb = int(cb + (tb - cb) * speed)

        self.itemconfig(self._pill, fill=f'#{nr:02x}{ng:02x}{nb:02x}')

        # keep going until close enough
        if abs(nr-tr) + abs(ng-tg) + abs(nb-tb) > 3:
            self._aid = self.after(16, self._step, target)
        else:
            self.itemconfig(self._pill, fill=f'#{tr:02x}{tg:02x}{tb:02x}')
            self._aid = None

    def set_active(self, active: bool):
        col = self._color if active else C['text_dim']
        self.itemconfig(self._ico, fill=col)
        self.itemconfig(self._lbl, fill=col)


# ─────────────────────────────────────────────────────────────────────────────
#  Output-pane colour tags
# ─────────────────────────────────────────────────────────────────────────────
def setup_output_tags(widget):
    tag_map = {
        'header':      {'foreground': C['accent2'],    'font': ('Consolas', 10, 'bold')},
        'separator':   {'foreground': C['border2']},
        'line_num':    {'foreground': C['text_dim']},
        'keyword_tok': {'foreground': C['pink']},
        'number_tok':  {'foreground': C['purple']},
        'ident_tok':   {'foreground': C['accent2']},
        'op_tok':      {'foreground': C['pink']},
        'type_name':   {'foreground': C['accent2']},
        'sym_val':     {'foreground': C['purple']},
        'sym_scope':   {'foreground': C['accent4']},
        'ir_label':    {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'ir_op':       {'foreground': C['pink']},
        'ir_var':      {'foreground': C['accent2']},
        'ir_num':      {'foreground': C['purple']},
        'ir_idx':      {'foreground': C['text_dim']},
        'asm_instr':   {'foreground': C['accent2'],    'font': ('Consolas', 10, 'bold')},
        'asm_reg':     {'foreground': C['accent']},
        'asm_label':   {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'asm_comment': {'foreground': C['text_dim']},
        'asm_imm':     {'foreground': C['purple']},
        'asm_dlabel':  {'foreground': C['accent']},
        'err_icon':    {'foreground': C['accent3'],    'font': ('Consolas', 10, 'bold')},
        'ok_icon':     {'foreground': C['accent'],     'font': ('Consolas', 10, 'bold')},
        'err_text':    {'foreground': '#FF8FA3'},
        'll1_head':    {'foreground': C['accent2'],    'font': ('Consolas', 10, 'bold')},
        'll1_nt':      {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'll1_arrow':   {'foreground': C['pink']},
        'll1_prod':    {'foreground': C['accent']},
        'll1_eps':     {'foreground': C['purple']},
        'll1_prime':   {'foreground': C['accent4']},
        'tac_label':   {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'sym_addr':    {'foreground': C['purple']},
        'sym_kind':    {'foreground': C['accent4']},
        'sym_init_y':  {'foreground': C['accent']},
        'sym_init_n':  {'foreground': C['accent3']},
        'sym_func':    {'foreground': C['pink'],       'font': ('Consolas', 10, 'bold')},
        'scope_hdr':   {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'sem_pass':    {'foreground': C['accent'],     'font': ('Consolas', 10, 'bold')},
        'sem_fail':    {'foreground': C['accent3'],    'font': ('Consolas', 10, 'bold')},
        'sem_check':   {'foreground': C['text']},
        'sem_sub':     {'foreground': C['text_dim']},
        'sem_err':     {'foreground': '#FF8FA3'},
        'count_box':   {'foreground': C['yellow'],     'font': ('Consolas', 10, 'bold')},
        'count_val':   {'foreground': C['accent'],     'font': ('Consolas', 10, 'bold')},
        'count_sep':   {'foreground': C['text_dim']},
        'row_idx':     {'foreground': C['text_dim'],  'font': ('Consolas', 12)},
        'row_kw':      {'foreground': C['pink'],       'font': ('Consolas', 12, 'bold')},
        'row_id':      {'foreground': C['accent2'],    'font': ('Consolas', 12)},
        'row_num':     {'foreground': C['purple'],     'font': ('Consolas', 12)},
        'row_op':      {'foreground': C['accent4'],    'font': ('Consolas', 12)},
        'row_other':   {'foreground': C['text'],       'font': ('Consolas', 12)},
        'row_val':     {'foreground': C['cyan'],       'font': ('Consolas', 12)},
    }
    for tag, cfg in tag_map.items():
        widget.tag_config(tag, **cfg)


# ─────────────────────────────────────────────────────────────────────────────
#  Stat Card bar
# ─────────────────────────────────────────────────────────────────────────────
def _insert_stat_cards(text_widget, cards: list):
    bar = tk.Frame(text_widget, bg=C['bg3'], pady=14)
    for item in cards:
        val  = item[0]
        lbl  = item[1]
        col  = item[2] if len(item) > 2 else C['accent2']
        card = tk.Frame(bar, bg=C['bg_card'], padx=0, pady=0)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=2)
        tk.Frame(card, bg=col, height=2).pack(fill=tk.X)
        inner = tk.Frame(card, bg=C['bg_card'], padx=20, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)
        tk.Label(inner, text=str(val),
                 font=('Segoe UI', 26, 'bold'),
                 bg=C['bg_card'], fg=col, anchor='w').pack(anchor='w')
        tk.Label(inner, text=lbl,
                 font=('Segoe UI', 8),
                 bg=C['bg_card'], fg=C['text_dim'], anchor='w').pack(anchor='w')
    text_widget.window_create('end', window=bar)
    text_widget.insert('end', '\n')


# ─────────────────────────────────────────────────────────────────────────────
#  Symbol Table Renderer
# ─────────────────────────────────────────────────────────────────────────────
def render_symbol_table(sv, sym_data: dict):
    scopes = sym_data.get('scopes', [])
    errors = sym_data.get('errors', [])

    total  = sum(len(s) for s in scopes)
    funcs  = sum(1 for s in scopes for e in s.values() if e.get('kind') == 'function')
    vars_  = total - funcs
    inited = sum(1 for s in scopes for e in s.values() if e.get('initialized'))
    errc   = len(errors)

    _insert_stat_cards(sv, [
        (total,  'TOTAL SYMBOLS',   C['accent2']),
        (vars_,  'VARIABLES',       C['accent']),
        (funcs,  'FUNCTIONS',       C['purple']),
        (inited, 'INITIALIZED',     C['yellow']),
        (errc,   'ERRORS',          C['accent3'] if errc else C['text_dim']),
    ])

    sv.insert('end', '\n', 'separator')

    HDR_BG   = '#1A1B26'
    ROW_FONT = ('Consolas', 12)
    HDR_FONT = ('Segoe UI', 9, 'bold')

    # column specs: (label, width_chars, color_key)
    COLS = [
        ('  NAME',    14, None),
        ('  TYPE',     8, None),
        ('  KIND',    10, None),
        ('  SCOPE',    6, None),
        ('  ADDRESS', 10, None),
        ('  SIZE',     6, None),
        ('  INIT',     6, None),
    ]

    def _make_sym_header(widget):
        hdr = tk.Frame(widget, bg=HDR_BG)
        for label, w, _ in COLS:
            tk.Label(hdr, text=label, width=w, anchor='w',
                     bg=HDR_BG, fg=C['text_dim'], font=HDR_FONT,
                     padx=8, pady=6, relief='flat', bd=0).pack(side=tk.LEFT)
            tk.Frame(hdr, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=3)
        # tk.Frame filler — no relief/border artifacts
        tk.Frame(hdr, bg=HDR_BG).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Frame(hdr, bg=C['border2'], height=1).pack(fill=tk.X, side=tk.BOTTOM)
        widget.window_create('end', window=hdr, stretch=True)
        widget.insert('end', '\n')

    def _make_sym_row(widget, sym, row_idx):
        is_func  = sym.get('kind') == 'function'
        addr_str = '—' if is_func else f"0x{sym['addr']:04X}"
        size_str = ('—' if is_func
                    else '4' if sym['type'] in ('int', 'float')
                    else '1' if sym['type'] == 'char' else '0')
        init_str = '—' if is_func else ('yes' if sym['initialized'] else 'no')

        name_col = C['pink']     if is_func else C['accent2']
        init_col = (C['text_dim'] if init_str == '—'
                    else C['accent'] if init_str == 'yes' else C['accent3'])

        row_bg = C['bg3'] if row_idx % 2 == 0 else '#252636'
        row = tk.Frame(widget, bg=row_bg)

        vals_colors = [
            (sym['name'],               name_col),
            (sym['type'],               C['accent2']),
            (sym.get('kind','variable'),C['accent4']),
            (str(sym['scope']),         C['text_dim']),
            (addr_str,                  C['purple']),
            (size_str,                  C['text_dim']),
            (init_str,                  init_col),
        ]
        for (text, color), (_, w, _c) in zip(vals_colors, COLS):
            tk.Label(row, text=f'  {text}', width=w, anchor='w',
                     bg=row_bg, fg=color, font=ROW_FONT,
                     padx=8, pady=5, relief='flat', bd=0).pack(side=tk.LEFT)
            tk.Frame(row, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=2)
        tk.Frame(row, bg=row_bg).pack(side=tk.LEFT, fill=tk.X, expand=True)
        widget.window_create('end', window=row, stretch=True)
        widget.insert('end', '\n')

    row_counter = [0]
    for level, scope in enumerate(scopes):
        if not scope:
            continue
        scope_label = 'Global scope' if level == 0 else f'Local scope  (level {level})'
        sv.insert('end', f'\n  {scope_label}\n', 'scope_hdr')
        _make_sym_header(sv)
        for sym in scope.values():
            row_counter[0] += 1
            _make_sym_row(sv, sym, row_counter[0])
        sv.insert('end', '\n', 'separator')

    if errors:
        sv.insert('end', f'\n  {len(errors)} SYMBOL TABLE ERROR(S):\n\n', 'sem_fail')
        for i, err in enumerate(errors, 1):
            sv.insert('end', f'  [{i:02d}]  ', 'sem_fail')
            sv.insert('end', f'{err}\n', 'sem_err')
    else:
        sv.insert('end', '  ✓  No symbol-table errors\n', 'sem_pass')


# ─────────────────────────────────────────────────────────────────────────────
#  Semantic Analysis Renderer
# ─────────────────────────────────────────────────────────────────────────────
def render_semantic(semv, errors: list, ast=None, sym_data=None):
    passed = max(0, len(CHECKS) - len(errors))
    _insert_stat_cards(semv, [
        (len(CHECKS), 'CHECKS',       C['accent2']),
        (passed,      'PASSED',       C['accent']),
        (len(errors), 'ERRORS',       C['accent3'] if errors else C['text_dim']),
    ])

    semv.insert('end', '\n  CHECKS PERFORMED\n', 'scope_hdr')
    semv.insert('end', '  ' + '─' * 60 + '\n\n', 'separator')

    for label, sub in CHECKS:
        keyword = label.lower().split()[0]
        is_err  = any(keyword in e.lower() for e in errors)
        if is_err:
            semv.insert('end', '  ✗  ', 'sem_fail')
            semv.insert('end', f'{label}\n', 'sem_check')
        else:
            semv.insert('end', '  ✓  ', 'sem_pass')
            semv.insert('end', f'{label}\n', 'sem_check')
        semv.insert('end', f'       {sub}\n', 'sem_sub')

    semv.insert('end', '\n' + '  ' + '─' * 60 + '\n', 'separator')
    if errors:
        semv.insert('end', f'\n  {len(errors)} SEMANTIC ERROR(S) DETECTED:\n\n', 'sem_fail')
        for i, err in enumerate(errors, 1):
            semv.insert('end', f'  [{i:02d}]  ', 'sem_fail')
            semv.insert('end', f'{err}\n\n', 'sem_err')
    else:
        semv.insert('end', '\n  ✓  Semantic analysis passed — no errors found\n', 'sem_pass')



# ─────────────────────────────────────────────────────────────────────────────
#  Syntax Analysis Renderer  ── beautiful tree + production list
# ─────────────────────────────────────────────────────────────────────────────

# Node type → (display label, color key)
_NODE_STYLE = {
    'program':    ('◈ PROGRAM',      'accent2'),
    'block':      ('{ BLOCK }',      'purple'),
    'decl':       ('⬡ DECL',         'accent4'),
    'decl_init':  ('⬡ DECL=',        'accent4'),
    'assign':     ('← ASSIGN',       'yellow'),
    'output':     ('▶ PRINT',        'teal'),
    'if':         ('? IF',           'pink'),
    'ifelse':     ('? IF-ELSE',      'pink'),
    'while':      ('↻ WHILE',        'cyan'),
}

_TYPE_COLOR = {
    'int':   'accent2',
    'float': 'purple',
}


def _pretty_ast(widget, node, prefix: str = '  ', is_last: bool = True,
                depth: int = 0):
    """
    Recursively draw one AST node as a coloured tree line.
    Uses box-drawing chars: └── ├── │
    """
    if node is None:
        return

    connector = '└── ' if is_last else '├── '
    child_pfx  = prefix + ('    ' if is_last else '│   ')

    # ── list of statements ────────────────────────────────────────────────
    if isinstance(node, list):
        for i, item in enumerate(node):
            _pretty_ast(widget, item, prefix, i == len(node) - 1, depth)
        return

    # ── leaf value (int / float / str identifier) ─────────────────────────
    if not isinstance(node, tuple):
        val = str(node)
        # pick colour for leaf
        if isinstance(node, (int, float)):
            tag = 'ir_num'
        else:
            tag = 'ir_var'
        widget.insert('end', prefix + connector, 'tree_line')
        widget.insert('end', val + '\n', tag)
        return

    # ── tuple node  (kind, child, child, …) ──────────────────────────────
    kind = str(node[0]) if node else '?'
    style = _NODE_STYLE.get(kind)

    if style:
        label, col = style
    else:
        label = kind.upper()
        col   = 'text'

    widget.insert('end', prefix + connector, 'tree_line')
    widget.insert('end', label + '\n', f'tree_{col}')

    children = node[1:]
    for i, child in enumerate(children):
        _pretty_ast(widget, child, child_pfx, i == len(children) - 1, depth + 1)


def _setup_tree_tags(widget):
    """Register tree-specific text tags (call once per widget)."""
    tag_defs = {
        'tree_line':    {'foreground': '#44475A'},
        'tree_accent2': {'foreground': C['accent2'],  'font': ('Consolas', 11, 'bold')},
        'tree_purple':  {'foreground': C['purple'],   'font': ('Consolas', 11, 'bold')},
        'tree_accent4': {'foreground': C['accent4'],  'font': ('Consolas', 11, 'bold')},
        'tree_yellow':  {'foreground': C['yellow'],   'font': ('Consolas', 11, 'bold')},
        'tree_teal':    {'foreground': C['teal'],     'font': ('Consolas', 11, 'bold')},
        'tree_pink':    {'foreground': C['pink'],     'font': ('Consolas', 11, 'bold')},
        'tree_cyan':    {'foreground': C['cyan'],     'font': ('Consolas', 11, 'bold')},
        'tree_text':    {'foreground': C['text'],     'font': ('Consolas', 11)},
        'tree_accent':  {'foreground': C['accent'],   'font': ('Consolas', 11, 'bold')},
        'prod_bullet':  {'foreground': C['accent4']},
        'prod_arrow':   {'foreground': C['pink']},
        'prod_rule':    {'foreground': C['text']},
        'prod_nt':      {'foreground': C['accent2'],  'font': ('Consolas', 11, 'bold')},
        'prod_err':     {'foreground': C['accent3'],  'font': ('Consolas', 11, 'bold')},
        'prod_idx':     {'foreground': C['text_dim'], 'font': ('Consolas', 10)},
    }
    for tag, cfg in tag_defs.items():
        widget.tag_config(tag, **cfg)


def render_syntax(synv, result: dict):
    stats  = result.get('stats', {})
    errors = result.get('errors', [])

    _setup_tree_tags(synv)

    # ── stat cards ────────────────────────────────────────────────────────
    _insert_stat_cards(synv, [
        (stats.get('productions', 0), 'PRODUCTIONS', C['accent2']),
        (stats.get('ast_nodes',   0), 'AST NODES',   C['accent']),
        (stats.get('depth',       0), 'TREE DEPTH',  C['purple']),
        (stats.get('errors',      0), 'ERRORS',      C['accent3'] if errors else C['text_dim']),
    ])

    # ── Productions fired ─────────────────────────────────────────────────
    synv.insert('end', '\n  GRAMMAR PRODUCTIONS USED\n', 'scope_hdr')
    synv.insert('end', '  ' + '─' * 62 + '\n\n', 'separator')

    for i, prod in enumerate(result.get('productions', []), 1):
        synv.insert('end', f'  {i:>2}  ', 'prod_idx')
        # split on →  for colouring
        if '→' in prod:
            lhs, rhs = prod.split('→', 1)
            synv.insert('end', '▸ ', 'prod_bullet')
            synv.insert('end', lhs.strip(), 'prod_nt')
            synv.insert('end', '  →  ', 'prod_arrow')
            synv.insert('end', rhs.strip() + '\n', 'prod_rule')
        elif prod.startswith('⚠'):
            synv.insert('end', prod + '\n', 'prod_err')
        else:
            synv.insert('end', '▸ ' + prod + '\n', 'prod_rule')

    # ── Parse / AST tree ─────────────────────────────────────────────────
    synv.insert('end', '\n\n  PARSE TREE  (AST)\n', 'scope_hdr')
    synv.insert('end', '  ' + '─' * 62 + '\n\n', 'separator')

    ast_root = result.get('_ast_raw')          # raw AST list if available
    parse_tree_text = result.get('parse_tree', '')

    if ast_root:
        # draw coloured tree from raw AST
        synv.insert('end', '  ◈ PROGRAM\n', 'tree_accent2')
        for i, node in enumerate(ast_root):
            _pretty_ast(synv, node, prefix='  ',
                        is_last=(i == len(ast_root) - 1))
    elif parse_tree_text.strip():
        # fallback: render the indented text with nicer tree lines
        _render_tree_text(synv, parse_tree_text)
    else:
        synv.insert('end', '  (empty tree)\n', 'tree_text')

    # ── Errors ────────────────────────────────────────────────────────────
    synv.insert('end', '\n\n  ' + '─' * 62 + '\n', 'separator')
    if errors:
        synv.insert('end', f'\n  ✗  {len(errors)} SYNTAX ERROR(S) FOUND\n\n', 'sem_fail')
        for i, err in enumerate(errors, 1):
            synv.insert('end', f'    [{i:02d}]  ', 'sem_fail')
            synv.insert('end', f'{err}\n\n', 'sem_err')
    else:
        synv.insert('end', '\n  ✓  Syntax analysis passed — no errors\n', 'sem_pass')


def _render_tree_text(widget, text: str):
    """
    Convert the raw parenthesised tree text into a prettier tree display
    using box-drawing characters and colour tags.
    """
    INDENT = 2   # spaces per level in the raw text

    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]

    # map each line to its indent depth
    def _depth(line):
        return (len(line) - len(line.lstrip(' '))) // INDENT

    def _tag_for(token: str):
        t = token.strip("()'\"")
        style = _NODE_STYLE.get(t.lower())
        if style:
            return f'tree_{style[1]}'
        if token.startswith("'") or token.startswith('"'):
            return 'ir_var'
        if t.replace('.', '', 1).lstrip('-').isdigit():
            return 'ir_num'
        if t in ('None', ')'):
            return 'tree_line'
        if t.upper() == t and len(t) > 1:
            return 'tree_accent2'
        return 'tree_text'

    # build parent-stack to know if a line is last child
    depth_stack = []   # stack of (depth, remaining_siblings)
    # pre-scan to count siblings at each depth per parent
    # simple approach: just render with ├── / └── based on next-line depth
    for idx, line in enumerate(lines):
        stripped = line.lstrip('([')
        token    = stripped.split()[0] if stripped.split() else ''
        depth    = _depth(line)

        # skip pure bracket lines
        if token in (')', ']', ''):
            continue

        # peek ahead: is the next non-bracket line at the same or lower depth?
        is_last = True
        for ahead in lines[idx + 1:]:
            t = ahead.lstrip('([').split()
            if not t or t[0] in (')', ']'):
                continue
            nd = _depth(ahead)
            if nd < depth:
                break
            if nd == depth:
                is_last = False
                break

        prefix   = '  ' + '    ' * (depth)
        connector = '└── ' if is_last else '├── '

        style = _NODE_STYLE.get(token.lower())
        if style:
            label, col = style
            widget.insert('end', prefix + connector, 'tree_line')
            widget.insert('end', label + '\n', f'tree_{col}')
        else:
            tag = _tag_for(token)
            widget.insert('end', prefix + connector, 'tree_line')
            widget.insert('end', token + '\n', tag)


def render_ir(iv, ir_instructions):
    total  = len(ir_instructions)
    labels = sum(1 for i in ir_instructions if i['op'] == 'mark')
    temps  = len({i['dst'] for i in ir_instructions
                  if i.get('dst') and str(i['dst']).startswith('t')
                  and str(i['dst'])[1:].isdigit()})

    _insert_stat_cards(iv, [
        (total,  'INSTRUCTIONS', C['accent2']),
        (labels, 'LABELS',       C['yellow']),
        (temps,  'TEMPORARIES',  C['purple']),
    ])

    iv.insert('end', '\n  THREE ADDRESS CODE  (TAC / IR)\n', 'scope_hdr')
    iv.insert('end', '  ' + '─' * 60 + '\n\n', 'separator')

    for idx, ins in enumerate(ir_instructions):
        op, s1, s2, d = ins['op'], ins['src1'], ins['src2'], ins['dst']
        iv.insert('end', f'{idx:>4}: ', 'ir_idx')

        if op == 'assign':
            iv.insert('end', f'  {d} ', 'ir_var')
            iv.insert('end', '= ', 'ir_op')
            iv.insert('end', f'{s1}\n', 'ir_num' if str(s1).isdigit() else 'ir_var')
        elif op in ('+', '-', '*', '/', '%'):
            iv.insert('end', f'  {d} ', 'ir_var')
            iv.insert('end', '= ', 'ir_op')
            iv.insert('end', f'{s1} ', 'ir_var')
            iv.insert('end', f'{op} ', 'ir_op')
            iv.insert('end', f'{s2}\n', 'ir_var')
        elif op in ('<', '<=', '>', '>=', '==', '!='):
            iv.insert('end', f'  {d} ', 'ir_var')
            iv.insert('end', '= ', 'ir_op')
            iv.insert('end', f'{s1} ', 'ir_var')
            iv.insert('end', f'{op} ', 'ir_op')
            iv.insert('end', f'{s2}\n', 'ir_var')
        elif op == 'mark':
            iv.insert('end', f'\n  {s1}:\n', 'ir_label')
        elif op == 'jump':
            iv.insert('end', '  goto ', 'ir_op')
            iv.insert('end', f'{s1}\n', 'ir_label')
        elif op == 'jump_if_false':
            iv.insert('end', '  if !', 'ir_op')
            iv.insert('end', f'{s1} ', 'ir_var')
            iv.insert('end', 'goto ', 'ir_op')
            iv.insert('end', f'{s2}\n', 'ir_label')
        elif op == 'output':
            iv.insert('end', '  print ', 'ir_op')
            iv.insert('end', f'{s1}\n', 'ir_var')


# ─────────────────────────────────────────────────────────────────────────────
#  Assembly Renderer
# ─────────────────────────────────────────────────────────────────────────────
class AsmRenderer:
    _REG = {'EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP',
            'AX','BX','CX','DX','AL','AH','BL','CL','DL'}
    _MNE = {'MOV','MOVZX','ADD','SUB','IMUL','IDIV','CDQ',
            'PUSH','POP','CALL','RET','LEAVE',
            'JMP','JE','JNE','JL','JLE','JG','JGE','JZ','JNZ',
            'CMP','XOR','AND','OR','NOT','NEG','INC','DEC',
            'SETE','SETNE','SETL','SETLE','SETG','SETGE','LEA','NOP'}
    _DIR = {'section','global','extern','db','dw','dd','equ','resb','resd'}

    def __init__(self, widget):
        self.w = widget

    def _i(self, text, tag=''):
        self.w.insert('end', text, tag or None)

    def _ops(self, s):
        for tok in re.split(r'(,\s*)', s):
            if not tok:
                continue
            if tok.startswith(','):
                self._i(tok); continue
            tc = tok.strip()
            if tc in self._REG:
                self._i(tok, 'asm_reg')
            elif re.fullmatch(r'-?\d+', tc):
                self._i(tok, 'asm_imm')
            elif tc.startswith('fmt_') or tc.startswith('.') or tc in ('printf','scanf'):
                self._i(tok, 'asm_dlabel')
            else:
                self._i(tok, 'tac_label')

    def render(self, lines):
        for raw in lines:
            s = raw.strip()
            if not s:
                self._i('\n'); continue
            if s.startswith(';'):
                self._i(raw + '\n', 'asm_comment'); continue
            if re.fullmatch(r'[\w.]+:', s):
                self._i(raw + '\n', 'asm_label'); continue
            fw = s.split()[0].lower()
            if fw in self._DIR or s.startswith('fmt_'):
                self._i(raw + '\n', 'asm_comment'); continue
            ni = len(raw) - len(raw.lstrip(' '))
            m  = re.match(r'(\S+)(\s+)(.*)', raw[ni:])
            if not m:
                self._i(raw + '\n'); continue
            mnem, pad, ops = m.group(1), m.group(2), m.group(3)
            self._i(raw[:ni])
            self._i(mnem, 'asm_instr' if mnem.upper() in self._MNE else '')
            self._i(pad)
            if ops:
                self._ops(ops)
            self._i('\n')


# ─────────────────────────────────────────────────────────────────────────────
#  LL(1) Grammar Window  ── bigger, better buttons, always-visible FIRST/FOLLOW
# ─────────────────────────────────────────────────────────────────────────────
class LL1Window(tk.Toplevel):
    _EXAMPLE = (
        "S -> iEtSD | a\n"
        "A -> BD | h\n"
        "B -> Ae | Df\n"
        "D -> d | ε\n"
        "E -> b\n"
        "F -> Sc | g"
    )

    def __init__(self, master):
        super().__init__(master)
        self.title('LL(1) Grammar Tool')
        # ── BIGGER window ─────────────────────────────────────────────────
        self.geometry('1150x720')
        self.minsize(900, 560)
        self.configure(bg=C['bg'])
        self.resizable(True, True)
        self._build()

    def _build(self):
        # ── header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C['bg2'], height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text='  ◈', font=('Segoe UI', 13, 'bold'),
                 bg=C['bg2'], fg=C['purple']).pack(side=tk.LEFT, pady=6)
        tk.Label(hdr, text=' LL(1) GRAMMAR TRANSFORMER',
                 font=('Consolas', 10, 'bold'),
                 bg=C['bg2'], fg=C['text_bright']).pack(side=tk.LEFT)

        tk.Frame(hdr, bg=C['purple'], height=2).pack(side=tk.BOTTOM, fill=tk.X)

        # ── toolbar  (LL1Button — always wide enough so FIRST/FOLLOW fits) ─
        tb = tk.Frame(self, bg=C['bg2'], height=46)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)

        # separator line below toolbar
        tk.Frame(self, bg=C['border2'], height=1).pack(fill=tk.X)

        btn_specs = [
            ('⚡  Transform',    self._transform,    C['accent'],   130),
            ('∑  FIRST / FOLLOW', self._show_ff,    C['accent2'],  160),
            ('✕  Clear',         self._clear,        C['accent3'],  110),
            ('◎  Example',       self._load_example, C['purple'],   120),
        ]
        for label, cmd, col, w in btn_specs:
            LL1Button(tb, label, cmd, color=col, width=w, height=32
                      ).pack(side=tk.LEFT, padx=5, pady=7)

        tk.Frame(tb, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=10)
        tk.Label(tb, text='   NT  →  prod1 | prod2    (use ε or eps for epsilon)',
                 font=('Consolas', 8), bg=C['bg2'],
                 fg=C['text_dim']).pack(side=tk.LEFT, padx=10)

        # ── paned editor / output ─────────────────────────────────────────
        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                              bg=C['bg'], sashwidth=5, sashrelief=tk.FLAT, bd=0)
        pane.pack(fill=tk.BOTH, expand=True)

        # left: input
        lf = tk.Frame(pane, bg=C['bg'])
        pane.add(lf, width=480)

        lhdr = tk.Frame(lf, bg=C['bg2'], height=28)
        lhdr.pack(fill=tk.X)
        lhdr.pack_propagate(False)
        tk.Label(lhdr, text='  INPUT GRAMMAR', font=FONT_UI_B,
                 bg=C['bg2'], fg=C['text_dim']).pack(side=tk.LEFT, pady=4)
        tk.Frame(lhdr, bg=C['border2'], height=1).pack(side=tk.BOTTOM, fill=tk.X)

        self.inp = scrolledtext.ScrolledText(
            lf, font=FONT_MONO, bg=C['bg'], fg=C['text'],
            insertbackground=C['accent'], selectbackground=C['selection'],
            relief='flat', bd=0, padx=14, pady=12)
        self.inp.pack(fill=tk.BOTH, expand=True)
        self.inp.insert('1.0', self._EXAMPLE)

        # right: output
        rf = tk.Frame(pane, bg=C['bg2'])
        pane.add(rf, width=640)

        rhdr = tk.Frame(rf, bg=C['bg2'], height=28)
        rhdr.pack(fill=tk.X)
        rhdr.pack_propagate(False)
        tk.Label(rhdr, text='  OUTPUT', font=FONT_UI_B,
                 bg=C['bg2'], fg=C['text_dim']).pack(side=tk.LEFT, pady=4)
        tk.Frame(rhdr, bg=C['border2'], height=1).pack(side=tk.BOTTOM, fill=tk.X)

        self.out = scrolledtext.ScrolledText(
            rf, font=FONT_MONO, bg=C['bg2'], fg=C['text'],
            insertbackground=C['accent'], selectbackground=C['selection'],
            relief='flat', bd=0, padx=14, pady=12, state='disabled')
        self.out.pack(fill=tk.BOTH, expand=True)
        setup_output_tags(self.out)

        # ── status bar ────────────────────────────────────────────────────
        sb = tk.Frame(self, bg=C['bg2'], height=24)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)
        tk.Frame(sb, bg=C['purple'], width=3).pack(side=tk.LEFT, fill=tk.Y)
        self._status = tk.Label(sb,
                                text='Ready — enter grammar then click Transform or FIRST/FOLLOW',
                                bg=C['bg2'], fg=C['text_dim'],
                                font=('Consolas', 8), anchor='w')
        self._status.pack(side=tk.LEFT, padx=10, pady=2)

    _ARROW_RE = re.compile(r'\s*(?:->|–>|—>|→)\s*')
    _PIPE_RE  = re.compile(r'\s*(?:\||\u2223|\uff5c)\s*')

    def _parse_input(self) -> dict:
        raw_text = self.inp.get('1.0', 'end-1c')
        nts, lines_data = set(), []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = self._ARROW_RE.search(line)
            if not m:
                continue
            left  = line[:m.start()].strip()
            right = line[m.end():]
            if left:
                nts.add(left)
                lines_data.append((left, right))

        # Multi-char lowercase strings that should stay as one terminal token.
        # Everything else (e.g. 'abc', 'abd', 'ae') gets split char-by-char
        # so that left-factoring can find common prefixes correctly.
        _KNOWN_TERM = {
            'id', 'num', 'int', 'float', 'char', 'void',
            'if', 'else', 'then', 'while', 'do', 'for',
            'begin', 'end', 'return', 'print', 'read',
            'true', 'false', 'and', 'or', 'not',
        }

        def tokenize(part):
            tokens = []
            for tok in part.split():
                if tok in ('ε', 'eps', "''"):
                    tokens.append('ε'); continue
                if tok in nts or len(tok) == 1:
                    tokens.append(tok); continue
                if tok in _KNOWN_TERM:
                    # recognised keyword terminal – keep whole
                    tokens.append(tok); continue
                # Unknown multi-char token: greedy-NT split then char-by-char
                i = 0
                while i < len(tok):
                    matched = False
                    for length in range(len(tok) - i, 1, -1):
                        if tok[i:i+length] in nts:
                            tokens.append(tok[i:i+length])
                            i += length; matched = True; break
                    if not matched:
                        tokens.append(tok[i]); i += 1
            return tokens

        grammar = {}
        for left, right in lines_data:
            prods = []
            for part in self._PIPE_RE.split(right):
                part = part.strip()
                if not part: continue
                toks = tokenize(part)
                if toks: prods.append(toks)
            if prods:
                grammar[left] = prods
        return grammar

    def _write_output(self, text: str):
        self.out.config(state='normal')
        self.out.delete('1.0', 'end')
        for line in text.splitlines():
            if line.startswith('─') or not line.strip():
                self.out.insert('end', line + '\n', 'separator')
            elif '→' in line:
                parts = line.split('→', 1)
                nt_part = parts[0]
                nt = nt_part.strip()
                tag = 'll1_prime' if nt.endswith("'") or '_' in nt else 'll1_nt'
                self.out.insert('end', nt_part, tag)
                self.out.insert('end', '→', 'll1_arrow')
                for token in re.split(r'(\s+\|\s+|\s+)', parts[1]):
                    if token.strip() == '|':
                        self.out.insert('end', token, 'll1_arrow')
                    elif token.strip() == 'ε':
                        self.out.insert('end', token, 'll1_eps')
                    elif token.strip():
                        t2 = 'll1_prime' if token.strip().endswith("'") or '_' in token.strip() else 'll1_prod'
                        self.out.insert('end', token, t2)
                    else:
                        self.out.insert('end', token)
                self.out.insert('end', '\n')
            else:
                self.out.insert('end', line + '\n', 'll1_head')
        self.out.config(state='disabled')

    def _has_left_recursion(self, g):
        return any(any(p and p[0] == nt for p in prods) for nt, prods in g.items())

    def _needs_factoring(self, g):
        for prods in g.values():
            seen = {}
            for p in prods:
                k = p[0] if p else 'ε'
                seen[k] = seen.get(k, 0) + 1
                if seen[k] > 1: return True
        return False

    def _transform(self):
        try:
            g = self._parse_input()
            if not g:
                messagebox.showwarning('Empty', 'No valid productions found.', parent=self)
                return
            sections = [format_grammar(g, '── Original Grammar')]
            if self._has_left_recursion(g):
                g = remove_left_recursion(g)
                sections.append(format_grammar(g, '── After Removing Left Recursion'))
            if self._needs_factoring(g):
                g = left_factoring(g)
                sections.append(format_grammar(g, '── After Left Factoring'))
            self._write_output('\n\n'.join(sections))
            self._status.config(text='✓  Transformation complete', fg=C['accent'])
        except Exception as e:
            messagebox.showerror('Error', str(e), parent=self)
            self._status.config(text=f'Error: {e}', fg=C['accent3'])

    def _show_ff(self):
        try:
            g = self._parse_input()
            if not g:
                messagebox.showwarning('Empty', 'No valid productions found.', parent=self)
                return
            f  = compute_first(g)
            fo = compute_follow(g, f)
            self._write_output(format_first_follow(f, fo))
            self._status.config(text='✓  FIRST / FOLLOW computed', fg=C['accent2'])
        except Exception as e:
            messagebox.showerror('Error', str(e), parent=self)
            self._status.config(text=f'Error: {e}', fg=C['accent3'])

    def _clear(self):
        self.inp.delete('1.0', 'end')
        self.out.config(state='normal')
        self.out.delete('1.0', 'end')
        self.out.config(state='disabled')
        self._status.config(text='Cleared', fg=C['text_dim'])

    def _load_example(self):
        self.inp.delete('1.0', 'end')
        self.inp.insert('1.0', self._EXAMPLE)
        self._status.config(text='Example loaded — click Transform or FIRST/FOLLOW', fg=C['text_dim'])


# ─────────────────────────────────────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────────────────────────────────────
class CompilerInterface:

    def __init__(self, root):
        self.root = root
        self.root.title("COMPILER // MAMUN_SYS v2.0")
        self.root.geometry("1440x860")
        self.root.configure(bg=C['bg'])
        self.root.minsize(1100, 650)

        self.current_file  = None
        self.file_modified = False
        self._blink_id     = None
        self._ll1_win      = None

        self.scanner    = TokenScanner();    self.scanner.initialize()
        self.processor  = SyntaxProcessor(); self.processor.initialize()
        self.translator = AssemblyTranslator()

        self._build()

    def _build(self):
        self._top_bar()
        self._body()
        self._snippet_bar()
        self._status_bar()

    # ── TOP BAR ───────────────────────────────────────────────────────────────
    def _top_bar(self):
        bar = tk.Frame(self.root, bg=C['bg2'], height=42)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Frame(self.root, bg=C['border2'], height=1).pack(fill=tk.X)

        left = tk.Frame(bar, bg=C['bg2'])
        left.pack(side=tk.LEFT, padx=12)
        tk.Label(left, text='◈', font=('Segoe UI', 14, 'bold'),
                 bg=C['bg2'], fg=C['accent']).pack(side=tk.LEFT)
        tk.Label(left, text='  MINI_COMPILER', font=('Segoe UI', 10, 'bold'),
                 bg=C['bg2'], fg=C['text_bright']).pack(side=tk.LEFT)
        tk.Label(left, text='  // Abdullah Al-Mamun', font=('Segoe UI', 9, 'bold'),
                 bg=C['bg2'], fg=C['accent4']).pack(side=tk.LEFT)

        tk.Frame(bar, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8, padx=12)

        self.file_label = tk.Label(bar, text='untitled', font=FONT_UI,
                                   bg=C['bg2'], fg=C['text_dim'])
        self.file_label.pack(side=tk.LEFT)

        right = tk.Frame(bar, bg=C['bg2'])
        right.pack(side=tk.RIGHT, padx=12)

        # ── Top bar buttons: slightly wider, taller, more breathing room ──
        buttons = [
            ('Open',   self.open_file,       C['accent2'],  82),
            ('Save',   self.save_file,       C['accent4'],  82),
            ('LL(1)',  self.open_ll1_window, C['purple'],   82),
            ('▶ Run',  self.run_compilation, C['accent'],   92),
            ('Clear',  self.reset_all,       C['accent3'],  82),
        ]
        for label, cmd, col, w in buttons:
            NeonButton(right, label, cmd, color=col, width=w, height=28
                       ).pack(side=tk.LEFT, padx=4, pady=7)

    # ── BODY ──────────────────────────────────────────────────────────────────
    def _body(self):
        self._activity_bar()

        pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                              bg=C['bg'], sashwidth=4, sashrelief=tk.FLAT,
                              bd=0, sashpad=0)
        pane.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(pane, bg=C['bg'])
        pane.add(left, width=520, minsize=300)
        self._build_editor(left)

        right = tk.Frame(pane, bg=C['bg'])
        pane.add(right, minsize=600)
        self._build_output(right)

    def _activity_bar(self):
        bar = tk.Frame(self.root, bg=C['bg2'], width=56)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar.pack_propagate(False)
        tk.Frame(self.root, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # top logo pip
        logo = tk.Canvas(bar, width=56, height=36,
                         bg=C['bg2'], highlightthickness=0)
        logo.pack(pady=(6, 4))
        logo.create_text(28, 18, text='◈', font=('Segoe UI', 16, 'bold'),
                         fill=C['accent'])

        # thin separator
        tk.Frame(bar, bg=C['border2'], height=1).pack(fill=tk.X, padx=4, pady=2)

        # (icon, short_label, tooltip, command, color)
        specs = [
            ('📂', 'OPEN',  'Open File',   self.open_file,       C['accent2']),
            ('💾', 'SAVE',  'Save File',   self.save_file,       C['yellow']),
            ('▶',  'RUN',   'Run Compile', self.run_compilation, C['accent']),
            ('⊞',  'LL(1)', 'LL(1) Tool',  self.open_ll1_window, C['purple']),
            ('↺',  'CLR',   'Clear All',   self.reset_all,       C['accent3']),
        ]

        self._sb_open  = None
        self._sb_save  = None
        self._sb_run   = None
        self._sb_ll1   = None
        self._sb_clear = None

        attr_names = ['_sb_open','_sb_save','_sb_run','_sb_ll1','_sb_clear']
        for (icon, lbl, tip, cmd, col), attr in zip(specs, attr_names):
            btn = SidebarButton(bar, icon, lbl, tip, cmd, color=col)
            btn.pack(pady=2)
            setattr(self, attr, btn)

    # ── EDITOR ────────────────────────────────────────────────────────────────
    def _build_editor(self, parent):
        header = tk.Frame(parent, bg=C['bg2'], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='  EDITOR', font=FONT_UI_B,
                 bg=C['bg2'], fg=C['accent']).pack(side=tk.LEFT)
        tk.Label(header, text='ctrl+s  ctrl+o',
                 font=('Consolas', 8), bg=C['bg2'],
                 fg=C['text_dim']).pack(side=tk.RIGHT, padx=8)
        tk.Frame(header, bg=C['accent'], height=2).pack(side=tk.BOTTOM, fill=tk.X)

        container = tk.Frame(parent, bg=C['bg'])
        container.pack(fill=tk.BOTH, expand=True)

        self.line_nums = tk.Text(container, width=4,
                                 bg=C['bg2'], fg=C['text_dim'],
                                 font=FONT_MONO_S, state='disabled',
                                 relief='flat', bd=0, padx=6, pady=10,
                                 cursor='arrow')
        self.line_nums.pack(side=tk.LEFT, fill=tk.Y)
        tk.Frame(container, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y)

        self.editor = scrolledtext.ScrolledText(
            container,
            font=FONT_MONO,
            bg=C['bg'],
            fg=C['text'],
            insertbackground=C['accent'],
            selectbackground=C['selection'],
            relief='flat', bd=0,
            padx=14, pady=10,
            undo=True,
            wrap=tk.NONE,
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.vbar.config(bg=C['bg2'], troughcolor=C['bg'], width=6,
                                relief='flat', bd=0)

        self.highlighter = SyntaxHighlighter(self.editor)
        self.editor.bind('<KeyRelease>', self._on_key)
        self.editor.bind('<<Modified>>', self._on_modified)
        self.editor.bind('<Control-s>', lambda e: self.save_file())
        self.editor.bind('<Control-o>', lambda e: self.open_file())

        sample = """\
int a;
int b;
a = 5;
b = 3;

/* sum */
int sum;
sum = a + b;
print(sum);

// conditional
if (a > b) {
    int diff;
    diff = a - b;
    print(diff);
}

// loop
int i;
i = 0;
while (i < 4) {
    int val;
    val = i * 3;
    print(val);
    i = i + 1;
}"""
        self.editor.insert('1.0', sample)
        self.highlighter.highlight()
        self._update_lines()
        self.file_modified = False

    # ── OUTPUT NOTEBOOK ── smaller tab labels ─────────────────────────────────
    def _build_output(self, parent):
        hdr = tk.Frame(parent, bg=C['bg2'], height=28)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text='  OUTPUT', font=FONT_UI_B,
                 bg=C['bg2'], fg=C['accent2']).pack(side=tk.LEFT)
        tk.Frame(hdr, bg=C['accent2'], height=2).pack(side=tk.BOTTOM, fill=tk.X)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Cyber.TNotebook',
                        background=C['bg2'],
                        borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure('Cyber.TNotebook.Tab',
                        background=C['bg2'],
                        foreground=C['text_dim'],
                        # ── SMALLER tab padding & font ──
                        padding=[10, 4],
                        borderwidth=0,
                        font=('Consolas', 8, 'bold'))
        style.map('Cyber.TNotebook.Tab',
                  background=[('selected', C['bg3'])],
                  foreground=[('selected', C['accent2'])],
                  expand=[('selected', [1, 0, 1, 0])])

        nb = ttk.Notebook(parent, style='Cyber.TNotebook')
        nb.pack(fill=tk.BOTH, expand=True)

        tabs = [
            ('TOKENS',   'tok_view'),
            ('SYNTAX',   'syn_view'),
            ('SYMBOLS',  'var_view'),
            ('SEMANTIC', 'sem_view'),
            ('IR CODE',  'ir_view'),
            ('ASM',      'asm_view'),
            ('PROBLEMS', 'err_view'),
        ]
        for label, attr in tabs:
            frame = tk.Frame(nb, bg=C['bg3'])
            nb.add(frame, text=f' {label} ')   # single space padding (was double)

            tv = scrolledtext.ScrolledText(
                frame,
                font=FONT_MONO_S,
                bg=C['bg3'],
                fg=C['text'],
                insertbackground=C['accent'],
                selectbackground=C['selection'],
                relief='flat', bd=0,
                padx=0, pady=0,
                wrap=tk.NONE,
            )
            tv.pack(fill=tk.BOTH, expand=True)
            tv.vbar.config(bg=C['bg2'], troughcolor=C['bg3'], width=6,
                           relief='flat', bd=0)
            setattr(self, attr, tv)
            setup_output_tags(tv)

        self.nb = nb

    # ── SNIPPET BAR ───────────────────────────────────────────────────────────
    def _snippet_bar(self):
        tk.Frame(self.root, bg=C['border2'], height=1).pack(fill=tk.X, side=tk.BOTTOM)
        outer = tk.Frame(self.root, bg=C['bg2'], height=32)
        outer.pack(fill=tk.X, side=tk.BOTTOM)
        outer.pack_propagate(False)

        tk.Label(outer, text='  SNIPPETS', font=('Segoe UI', 8, 'bold'),
                 bg=C['bg2'], fg=C['text_dim']).pack(side=tk.LEFT, padx=(8, 6))
        tk.Frame(outer, bg=C['border2'], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=6)

        canvas = tk.Canvas(outer, bg=C['bg2'], height=30,
                           highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

        inner = tk.Frame(canvas, bg=C['bg2'])
        canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_frame_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
        inner.bind('<Configure>', _on_frame_configure)

        def _on_wheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', _on_wheel)
        inner.bind('<MouseWheel>', _on_wheel)

        for name, code in SNIPPETS:
            def make_cmd(n=name, c=code):
                def _load():
                    if messagebox.askyesno('Load Snippet',
                                           f'Replace editor with "{n}"?',
                                           parent=self.root):
                        self.editor.delete('1.0', tk.END)
                        self.editor.insert('1.0', c)
                        self.highlighter.highlight()
                        self._update_lines()
                        self.file_modified = True
                        self._update_title()
                        self.status.config(text=f'Snippet: {n}', fg=C['accent4'])
                return _load
            SnippetButton(inner, name, make_cmd()).pack(side=tk.LEFT, padx=3, pady=5)

    # ── STATUS BAR ────────────────────────────────────────────────────────────
    def _status_bar(self):
        bar = tk.Frame(self.root, bg=C['bg2'], height=20)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        tk.Frame(bar, bg=C['accent'], width=3).pack(side=tk.LEFT, fill=tk.Y)

        self.status = tk.Label(bar, text='READY', font=('Consolas', 8),
                               bg=C['bg2'], fg=C['accent'])
        self.status.pack(side=tk.LEFT, padx=10)

        tk.Label(bar, text='UTF-8  ·  C-like  ·  MAMUN_SYS',
                 font=('Consolas', 7), bg=C['bg2'],
                 fg=C['text_dim']).pack(side=tk.RIGHT, padx=12)

        self._cursor_lbl = tk.Label(bar, text='▋', font=('Consolas', 8),
                                    bg=C['bg2'], fg=C['accent'])
        self._cursor_lbl.pack(side=tk.RIGHT, padx=4)
        self._blink()

    def _blink(self):
        cur = self._cursor_lbl.cget('fg')
        self._cursor_lbl.config(fg=C['accent'] if cur == C['bg2'] else C['bg2'])
        self._blink_id = self.root.after(530, self._blink)

    # ── EDITOR HELPERS ────────────────────────────────────────────────────────
    def _on_key(self, _=None):
        self._update_lines()
        self.highlighter.highlight()

    def _on_modified(self, _=None):
        if self.editor.edit_modified():
            self.file_modified = True
            self._update_title()
            self.editor.edit_modified(False)

    def _update_lines(self, _=None):
        count = self.editor.get('1.0', 'end-1c').count('\n') + 1
        nums  = '\n'.join(str(i) for i in range(1, count + 1))
        self.line_nums.config(state='normal')
        self.line_nums.delete('1.0', 'end')
        self.line_nums.insert('1.0', nums)
        self.line_nums.config(state='disabled')

    def _update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else 'untitled'
        dot  = ' ●' if self.file_modified else ''
        self.file_label.config(text=f'{name}{dot}',
                               fg=C['accent4'] if self.file_modified else C['text_dim'])
        self.root.title(f'COMPILER // {name}{dot}')

    # ── FILE OPS ──────────────────────────────────────────────────────────────
    def open_file(self):
        path = filedialog.askopenfilename(
            title='Open Source File',
            filetypes=[('C Source','*.c'),('Text','*.txt'),('All','*.*')],
            initialdir=os.getcwd())
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.delete('1.0', tk.END)
                self.editor.insert('1.0', content)
                self.highlighter.highlight()
                self.current_file = path
                self.file_modified = False
                self._update_title()
                self._update_lines()
                self.status.config(text=f'Opened: {os.path.basename(path)}', fg=C['accent'])
            except Exception as e:
                messagebox.showerror('Error', str(e))

    def save_file(self):
        if not self.current_file:
            self._save_as(); return
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.get('1.0', 'end-1c'))
            self.file_modified = False
            self._update_title()
            self.status.config(text=f'Saved: {os.path.basename(self.current_file)}',
                               fg=C['accent4'])
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title='Save As', defaultextension='.c',
            filetypes=[('C Source','*.c'),('Text','*.txt'),('All','*.*')],
            initialdir=os.getcwd())
        if path:
            self.current_file = path
            self.save_file()

    # ── LL(1) WINDOW ──────────────────────────────────────────────────────────
    def open_ll1_window(self):
        if self._ll1_win and self._ll1_win.winfo_exists():
            self._ll1_win.lift()
            self._ll1_win.focus_force()
        else:
            self._ll1_win = LL1Window(self.root)
            self._ll1_win.focus_force()

    # ── COMPILATION ───────────────────────────────────────────────────────────
    def run_compilation(self):
        self.status.config(text='Compiling…', fg=C['accent4'])
        self.root.update()

        src = self.editor.get('1.0', tk.END)
        for attr in ('tok_view','syn_view','var_view','sem_view','ir_view','asm_view','err_view'):
            getattr(self, attr).delete('1.0', tk.END)
        self.processor.registry.clear()

        # ── TOKENS ────────────────────────────────────────────────────────
        tokens, lex_errs = self.scanner.scan(src)
        tv = self.tok_view

        tok_total = len(tokens)
        keywords  = sum(1 for t in tokens if t['kind'] in
                        ('KEYWORD','IF','ELSE','WHILE','INT','VOID','FLOAT','PRINT','RETURN','FOR'))
        idents    = sum(1 for t in tokens if t['kind'] in ('ID','IDENTIFIER'))
        numbers   = sum(1 for t in tokens if t['kind'] in ('NUMBER','NUM','INTEGER','DECIMAL'))
        operators = sum(1 for t in tokens if t['kind'] in
                        ('OP','ASSIGN','RELOP','EQUALS','EQUAL_TO','NOT_EQUAL',
                         'LESS','LESS_EQ','GREATER','GREATER_EQ',
                         'PLUS','MINUS','MULTIPLY','DIVIDE','MOD'))

        _insert_stat_cards(tv, [
            (tok_total, 'TOTAL TOKENS', C['accent2']),
            (keywords,  'KEYWORDS',     C['pink']),
            (idents,    'IDENTIFIERS',  C['accent2']),
            (numbers,   'NUMBERS',      C['purple']),
            (operators, 'OPERATORS',    C['accent4']),
        ])

        tv.insert('end', '\n', 'separator')

        # ── colour tag sets ───────────────────────────────────────────────
        kw_set = {'KEYWORD','IF','ELSE','WHILE','INT','VOID','FLOAT','PRINT','RETURN','FOR'}
        nu_set = {'NUMBER','NUM','INTEGER','DECIMAL','INT_LITERAL'}
        id_set = {'ID','IDENTIFIER'}
        op_set = {'OP','ASSIGN','RELOP','EQUALS','EQUAL_TO','NOT_EQUAL',
                  'LESS','LESS_EQ','GREATER','GREATER_EQ',
                  'PLUS','MINUS','MULTIPLY','DIVIDE','MOD'}

        def _kind_tag(k):
            if k in kw_set: return 'row_kw'
            if k in nu_set: return 'row_num'
            if k in id_set: return 'row_id'
            if k in op_set: return 'row_op'
            return 'row_other'

        # ── column header — ONE embedded Frame (just the header) ──────────
        HDR_BG   = '#1A1B26'
        HDR_FONT = ('Consolas', 11, 'bold')

        col_hdr = tk.Frame(tv, bg=HDR_BG)
        for lbl, w in [('  #', 6), ('  TYPE', 20), ('  VALUE', 20), ('  LINE', 8)]:
            tk.Label(col_hdr, text=lbl, width=w, anchor='w',
                     bg=HDR_BG, fg=C['text_dim'], font=HDR_FONT,
                     padx=6, pady=5, relief='flat', bd=0).pack(side=tk.LEFT)
            tk.Frame(col_hdr, bg=C['border2'], width=1).pack(
                side=tk.LEFT, fill=tk.Y, pady=3)
        tk.Frame(col_hdr, bg=HDR_BG).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Frame(col_hdr, bg=C['border2'], height=1).pack(fill=tk.X, side=tk.BOTTOM)
        tv.window_create('end', window=col_hdr, stretch=True)
        tv.insert('end', '\n')

        # ── FAST pure-text token rows (zero widgets per row) ──────────────
        # Uses text tags for colour — scrolls instantly even with 1000+ tokens
        ROW_FONT = ('Consolas', 12)
        tv.config(font=ROW_FONT)   # base font for all inserted text

        for idx, tok in enumerate(tokens, 1):
            k, v, ln = tok['kind'], str(tok['val']), str(tok['ln'])
            tag = _kind_tag(k)

            tv.insert('end', f'  {idx:<5}', 'row_idx')
            tv.insert('end', f'  {k:<22}', tag)
            tv.insert('end', f'  {v:<22}', 'row_val')
            tv.insert('end', f'  {ln}\n',  'row_idx')

        # ── SYNTAX ANALYSIS ───────────────────────────────────────────────
        syn_result = run_syntax_analysis(self.processor, src)
        syn_result['_ast_raw'] = self.processor.ast   # pass raw AST for tree render
        render_syntax(self.syn_view, syn_result)

        # ── SYMBOLS ───────────────────────────────────────────────────────
        self.processor.process(src)
        sv = self.var_view

        all_entries = self.processor.registry.all_entries()
        max_level   = max((e['scope_level'] for e in all_entries), default=0)
        scopes_list = [{} for _ in range(max_level + 1)]
        addr_counters = {}
        for e in all_entries:
            lvl = e['scope_level']
            nm  = e['id']
            if nm not in scopes_list[lvl]:
                if lvl not in addr_counters:
                    addr_counters[lvl] = 0x1000 if lvl == 0 else (0xBF00 - lvl * 0x100)
                cur_addr = addr_counters[lvl]
                sz = 4 if e['dtype'] in ('int','float') else 1 if e['dtype']=='char' else 0
                addr_counters[lvl] += sz
                kind = e.get('ctx', 'variable')
                if kind not in ('variable','function','param'):
                    kind = 'variable'
                scopes_list[lvl][nm] = {
                    'name':        nm,
                    'type':        e['dtype'],
                    'kind':        kind,
                    'scope':       lvl,
                    'addr':        cur_addr,
                    'initialized': e['val'] is not None,
                }
        sym_data = {'scopes': scopes_list, 'errors': []}
        render_symbol_table(sv, sym_data)

        # ── SEMANTIC ──────────────────────────────────────────────────────
        sem_errors = self.processor.issues[:]
        render_semantic(self.sem_view, sem_errors)

        # ── IR CODE ───────────────────────────────────────────────────────
        render_ir(self.ir_view, self.processor.ir_instructions)

        # ── ASM ───────────────────────────────────────────────────────────
        AsmRenderer(self.asm_view).render(
            self.translator.translate(self.processor.ir_instructions))

        # ── PROBLEMS ──────────────────────────────────────────────────────
        ev = self.err_view
        all_errs = lex_errs + self.processor.issues
        if all_errs:
            _insert_stat_cards(ev, [
                (len(all_errs), 'PROBLEMS FOUND', C['accent3']),
                (len(lex_errs), 'LEX ERRORS',     C['accent3']),
                (len(self.processor.issues), 'PARSE/SEMANTIC', C['accent4']),
            ])
            ev.insert('end', '\n', 'separator')
            for i, err in enumerate(all_errs, 1):
                ev.insert('end', f'  [{i:02d}]  ', 'err_icon')
                ev.insert('end', f'{err}\n\n', 'err_text')
            self.status.config(text=f'  {len(all_errs)} error(s)', fg=C['accent3'])
            self.nb.select(6)
        else:
            _insert_stat_cards(ev, [
                (0, 'ERRORS', C['accent']),
            ])
            ev.insert('end', '\n  ✓  Build successful — no problems detected.\n', 'ok_icon')
            self.status.config(text='Build OK', fg=C['accent'])

    # ── RESET ─────────────────────────────────────────────────────────────────
    def reset_all(self):
        if self.file_modified:
            resp = messagebox.askyesnocancel('Unsaved Changes', 'Save before clearing?')
            if resp is True:   self.save_file()
            elif resp is None: return
        self.editor.delete('1.0', tk.END)
        for attr in ('tok_view','syn_view','var_view','sem_view','ir_view','asm_view','err_view'):
            getattr(self, attr).delete('1.0', tk.END)
        self.processor.registry.clear()
        self.current_file  = None
        self.file_modified = False
        self._update_title()
        self._update_lines()
        self.status.config(text='Ready', fg=C['accent'])


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = CompilerInterface(root)
    root.mainloop()