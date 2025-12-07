###############################################
# XU LEXER — ANALISADOR LÉXICO (PLY - LEX)
###############################################

import ply.lex as lex
import sys

###############################################################
# LISTA DE TOKENS
###############################################################

tokens = (
    'NAME',
    'NUMINT',
    'NUMREAL',
    'CADEIA',
    'OP_REL',
    'ATRIB',
    'PC',
    'COMMENT',

    'DECLARACOES',
    'PROGRAMA',
    'INTEIRO',
    'REAL',
    'TEXTO',
    'LOGICO',

    'LEIA',
    'ESCREVA',

    'SE',
    'SENAO',
    'ENTAO',

    'ENQUANTO',
    'INICIO',
    'FIM',

    'E_BOOL',
    'OU_BOOL',
)

###############################################################
# LITERAIS (caracteres únicos)
###############################################################

literals = ['+', '-', '*', '/', '(', ')']

###############################################################
# PALAVRAS RESERVADAS
###############################################################

reserved = {
    'DECLARACOES': 'DECLARACOES',
    'PROGRAMA': 'PROGRAMA',
    'INTEIRO': 'INTEIRO',
    'REAL': 'REAL',
    'TEXTO': 'TEXTO',
    'LOGICO': 'LOGICO',
    'LEIA': 'LEIA',
    'ESCREVA': 'ESCREVA',
    'SE': 'SE',
    'SENAO': 'SENAO',
    'ENTAO': 'ENTAO',
    'ENQUANTO': 'ENQUANTO',
    'INICIO': 'INICIO',
    'FIM': 'FIM',
    'E': 'E_BOOL',
    'OU': 'OU_BOOL'
}

###############################################################
# TOKENS VIA REGEX
###############################################################

# Dois-pontos
t_PC = r':'

# Ignorar espaços e TAB
t_ignore = " \t"

# Operador de atribuição "<-"
def t_ATRIB(t):
    r'\<\-'
    return t

# Número real
def t_NUMREAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

# Número inteiro
def t_NUMINT(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Cadeias de texto entre aspas
def t_CADEIA(t):
    r'"([^\\\n]|(\\.))*?"'
    return t

# Comentários
def t_COMMENT(t):
    r'\#.*'
    return t

# Operadores relacionais
def t_OP_REL(t):
    r'<=|>=|==|!=|<|>'
    return t

###############################################################
# NAMES (identificadores + palavras reservadas)
###############################################################
def t_NAME(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    up = t.value.upper()
    if up in reserved:
        t.type = reserved[up]
        t.value = up
    return t

###############################################################
# CONTAGEM DE LINHAS
###############################################################
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

###############################################################
# ERROS LÉXICOS
###############################################################
def t_error(t):
    print(
        f"Erro léxico: caractere ilegal '{t.value[0]}' na linha {t.lexer.lineno}",
        file=sys.stderr
    )
    t.lexer.skip(1)

###############################################################
# CRIAÇÃO DO LEXER
###############################################################
lexer = lex.lex()
lexer.lineno = 1
