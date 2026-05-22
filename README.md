# ⚡ Mini Compiler

<div align="center">

![Compiler](https://img.shields.io/badge/Compiler-C--Like-purple?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![PLY](https://img.shields.io/badge/Parser-PLY%20LALR(1)-orange?style=for-the-badge)
![GUI](https://img.shields.io/badge/GUI-Tkinter-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A modern, VS Code–styled mini compiler with full pipeline: Lexer → Parser → Semantic → IR → Assembly**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture) • [Syntax Reference](#-supported-syntax) • [Screenshots](#-screenshots)

</div>

---

## ✨ Features

### 🎨 Modern VS Code–Styled Interface

- **Dracula Dark Theme** — hand-tuned `#282A36` palette matching VS Code Dark+
- **Syntax Highlighting** — real-time coloring for keywords, numbers, operators, and comments
- **Split-Panel Layout** — editor on the left, tabbed output on the right
- **Smart Tab System** — 7 output tabs: Tokens · Syntax · Symbols · Semantic · IR · Assembly · Problems
- **Code Snippets Menu** — 10 built-in programs (Factorial, FizzBuzz, Bubble Sort, Power, …)

### 🔧 Full Compiler Pipeline

| Phase | Module | Description |
|-------|--------|-------------|
| **Lexical Analysis** | `lexer.py` | PLY-based tokenizer; handles keywords, identifiers, literals, operators, single- and multi-line comments |
| **Syntax Analysis** | `parser.py` + `syntax_analysis.py` | LALR(1) parser (PLY `yacc`); builds AST, fires grammar rules, reports parse errors with recovery |
| **Symbol Table** | `symbol_table.py` | Nested-scope stack; tracks type, value, scope level, and address for every variable |
| **Semantic Analysis** | `semantic.py` | Re-uses parser errors; checks undeclared variables, duplicate declarations, and type compatibility |
| **IR Generation** | `parser.py` | Emits three-address code (TAC) instructions as dicts during parsing |
| **Code Generation** | `code_generator.py` | Translates TAC to pseudo-x86 NASM assembly; proper `IDIV`/`CDQ`, `SETcc`, `MOVZX` sequences |
| **LL(1) Tool** | `grammar_utils.py` + `grammar_tool.py` | Standalone LL(1) analyser: left-recursion removal, left factoring, FIRST/FOLLOW sets, LL(1) parsing table |

### 💡 Developer Experience

- **File Management** — Open / Save with `Ctrl+O` / `Ctrl+S`
- **Line Numbers** — auto-updating gutter
- **Modified Indicator** — `●` in title bar for unsaved changes
- **Status Bar** — live compilation status (Build OK / error count)
- **LL(1) Grammar Window** — separate floating window for grammar transformation experiments

---

## 🚀 Installation

### Prerequisites

```
Python 3.8 or higher
tkinter  (bundled with most Python distributions)
PLY      (pip install ply)
```

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/mini-compiler.git
cd mini-compiler

# Install the only required third-party dependency
pip install ply

# Run the compiler
python main.py
```

> **Note:** `requirements.txt` lists every package in the development environment.  
> The only runtime dependency is **`ply`**. Everything else is standard-library.

---

## 📖 Usage

### Starting the Compiler

```bash
python main.py
```

### Basic Workflow

1. **Write or open code** in the left editor panel (syntax highlighting updates live)
2. **Click ▶ Run** (or press `F5`) to compile
3. **Inspect results** in the seven output tabs:

| Tab | Content |
|-----|---------|
| **Tokens** | Token type, value, and line number for every lexeme |
| **Syntax** | Fired grammar rules, AST node labels, parse-tree text, and stats |
| **Symbols** | Variable registry with type, scope level, address, and init status |
| **Semantic** | Pass/fail checklist for each semantic rule; any errors listed below |
| **IR Code** | Three-address instructions: `op`, `src1`, `src2`, `dst` |
| **Assembly** | Pseudo-x86 NASM output with proper register allocation |
| **Problems** | Unified lexical + parse/semantic error list |

### LL(1) Grammar Tool

Click **LL(1)** in the toolbar to open the grammar window.  
Enter productions interactively; the tool applies left-recursion removal, left factoring, then shows FIRST/FOLLOW sets and the LL(1) parsing table.

You can also run it from the terminal:

```bash
python grammar_tool.py
```

---

## 📝 Supported Syntax

```c
// ── Variable declarations ───────────────────────────────
int x;
float y = 3.14;

// ── Assignments ─────────────────────────────────────────
x = 10;
y = x + 2;

// ── Arithmetic (all five operators) ─────────────────────
int a;
a = (x * 3 + y) / 2 % 5;

// ── Output ──────────────────────────────────────────────
print(a);

// ── If / If-Else ────────────────────────────────────────
if (x < y) {
    int diff;
    diff = y - x;
    print(diff);
} else {
    print(x);
}

// ── While loop ──────────────────────────────────────────
int counter;
counter = 0;
while (counter < 5) {
    print(counter);
    counter = counter + 1;
}

// ── Comments ────────────────────────────────────────────
// single-line comment
/* multi-line
   comment */
```

### Supported Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+`  `-`  `*`  `/`  `%` |
| Relational | `<`  `<=`  `>`  `>=`  `==`  `!=` |
| Assignment | `=` |

### Data Types

`int` · `float`

---

## 🏗️ Architecture

### Project Structure

```
mini-compiler/
├── main.py              # Entry point — launches Tkinter root + CompilerInterface
├── gui.py               # VS Code–styled GUI (CompilerInterface, renderers, LL1Window)
├── lexer.py             # Lexical analyser   — TokenScanner  (PLY lex)
├── parser.py            # Syntax analyser    — SyntaxProcessor (PLY yacc, TAC emitter)
├── syntax_analysis.py   # Syntax result builder — wraps SyntaxProcessor, builds AST view
├── symbol_table.py      # Symbol table       — VariableRegistry (nested scope stack)
├── semantic.py          # Semantic checks    — semantic_analysis()
├── code_generator.py    # Code generator     — AssemblyTranslator (TAC → pseudo-x86)
├── grammar_utils.py     # LL(1) utilities    — left-recursion removal, left factoring,
│                        #                      FIRST/FOLLOW, LL(1) table, formatters
├── grammar_tool.py      # LL(1) CLI          — interactive terminal interface
├── parsetab.py          # Auto-generated PLY parse table (do not edit)
└── parser.out           # PLY parser debug log (auto-generated)
```

### Compilation Pipeline

```
Source Code
    │
    ▼
┌─────────────┐
│   Lexer     │  TokenScanner (PLY lex)
│  lexer.py   │  → token stream
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│     Parser      │  SyntaxProcessor (PLY yacc LALR(1))
│   parser.py     │  → AST  +  three-address IR  +  symbol table
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌──────────────┐
│Symbol  │  │  IR Code     │
│ Table  │  │ (TAC dicts)  │
└────────┘  └──────┬───────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Code Generator  │  AssemblyTranslator
          │code_generator.py│  → pseudo-x86 NASM assembly
          └─────────────────┘
```

### Key Design Decisions

- **PLY LALR(1)** for the parser — generates the parse table once (`parsetab.py`) and reuses it on every compilation run for speed.
- **Marker productions** (`if_jump`, `else_jump`, `if_end`, `while_start`, `while_body`, `while_end`) allow back-patching labels into the IR without a separate IR-rewrite pass.
- **Round-robin register allocator** in `AssemblyTranslator` maps temporaries to `EBX/ECX/ESI/EDI`; `EAX/EDX` are used as scratch for arithmetic and division.
- **LL(1) tool** is completely independent of the LALR compiler — it is a teaching aid for grammar analysis.

---

## 🎨 Assembly Output Details

The `AssemblyTranslator` produces NASM-compatible pseudo-assembly:

```nasm
; ── Generated Assembly ─────────────────────────────
section .data
    fmt_int  db "%d", 10, 0
section .text
    global main
    extern printf

main:
    PUSH    EBP
    MOV     EBP, ESP
    ; ... generated instructions ...
    MOV     EAX, EBX
    CDQ
    IDIV    ECX          ; division with sign-extend
    MOV     ESI, EAX     ; quotient
    CMP     EBX, ECX
    SETLE   AL
    MOVZX   EAX, AL      ; boolean result
    MOV     EDI, EAX
.exit:
    XOR     EAX, EAX
    MOV     ESP, EBP
    POP     EBP
    RET
```

---

## 📸 Screenshots

### Main Interface

<img width="1396" height="795" alt="Main Interface" src="https://github.com/user-attachments/assets/33812444-7d60-4e42-9990-8f75c5b9acb9" />

*Dracula-themed editor with live syntax highlighting and split-panel output*

### Compilation Results

<img width="1392" height="634" alt="Compilation Results" src="https://github.com/user-attachments/assets/5bb4986a-ea2b-4477-bebb-1c23a80f80b9" />

*Token analysis, symbol table, IR code, and assembly output across seven tabs*

---

## 🎯 Syntax Highlighting Reference

### Code Editor

| Element | Color |
|---------|-------|
| Keywords (`int`, `if`, `while`, …) | `#FF7B72` Red-orange |
| Numbers (`10`, `3.14`) | `#BC8CFF` Purple |
| Comments (`//`, `/* */`) | `#484F58` Grey italic |
| Operators (`+`, `-`, `*`, …) | `#FF7B72` Red-orange |
| Functions (`print`) | `#3FB950` Green bold |
| Variables / identifiers | `#C9D1D9` Light grey |

### Output Panels (Dracula palette)

| Element | Color |
|---------|-------|
| Instructions / keywords | `#8BE9FD` Cyan |
| Registers | `#FFB86C` Orange |
| Labels | `#F1FA8C` Yellow |
| Errors | `#FF5555` Red |
| Success / OK | `#50FA7B` Green |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + S` | Save file |
| `Ctrl + O` | Open file |
| `F5` | Run compilation |

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| **Python 3.8+** | Core language |
| **Tkinter** | GUI framework |
| **PLY 3.11** | Lexer (`lex`) and LALR(1) parser (`yacc`) |
| **`re` module** | Syntax highlighting pattern matching |
| **`collections.OrderedDict`** | Grammar ordering in LL(1) utilities |

---

## 👨‍💻 Author

**Abdullah Al-Mamun**

Built with ❤️ for Compiler Design final lab project

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with Python · PLY · Tkinter

</div>#   M i n i _ C o m p i l e r  
 