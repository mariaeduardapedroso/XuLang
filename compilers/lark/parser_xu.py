# Xu Parser Comentado
# Contém as regras da gramática (PLY - yacc) com a GRAMÁTICA
# escrita acima de cada função e explicações técnicas por bloco.

"""
Este documento contém apenas o parser (análise sintática) do
compilador XuLang. Cada função p_* possui a gramática em comentário
acima e uma explicação técnica sobre o que a regra faz e quais
ações semânticas executa (atualizar tabela de símbolos, gerar
pequenos trechos de C, etc.).

Estrutura:
 - Precedência
 - Regra inicial: Programa
 - Declarações
 - Comandos (atribuição, leitura, escrita, se/enquanto)
 - Expressões aritméticas
 - Expressões relacionais/booleanas
 - Tratamento de erros sintáticos

As ações do parser devem produzir estruturas simples (strings de
código C) e também fazer checagens semânticas mínimas.
"""

import sys
import ply.yacc as yacc

# Observação: este parser assume que o lexer "Xu Lexer Comentado"
# já foi criado e exporta os tokens esperados.

# Precedência para operadores (igual ao que usamos no lexer)
precedence = (
    ('left', 'E_BOOL', 'OU_BOOL'),
    ('left', 'OP_REL'),
    ('left', '+', '-'),
    ('left', '*', '/'),
)

# ==============================================================
# GRAMÁTICA: Programa
#   Programa : ':' DECLARACOES ListaDeclaracoes ':' PROGRAMA ListaComandos
# AÇÃO: monta o cabeçalho do arquivo C (includes, main, declarações
#       e corpo do programa). p[6] contém a lista de comandos.
# ==============================================================
def p_Programa(p):
    'Programa : PC DECLARACOES ListaDeclaracoes PC PROGRAMA ListaComandos'
    # p[6] -> ListaComandos (lista de strings com código C)
    c_out = []
    c_out.append('/* Código gerado automaticamente por Xu */')
    c_out.append('#include <stdio.h>')
    c_out.append('#include <stdlib.h>')
    c_out.append('#include <string.h>')
    c_out.append('')
    c_out.append('int main() {')
    # As declarações globais (preenchidas por p_Declaracao) devem
    # estar em uma lista global c_decls fornecida pelo módulo principal.
    try:
        from xu_semantic_comentado import c_decls
        if c_decls:
            c_out.append('    /* Declarações */')
            for d in c_decls:
                c_out.append('    ' + d)
            c_out.append('')
    except Exception:
        # se o módulo não existir, apenas continue
        pass

    c_out.append('    /* Programa */')
    for line in p[6]:
        c_out.append('    ' + line)
    c_out.append('')
    c_out.append('    return 0;')
    c_out.append('}')

    print('\n'.join(c_out))

# ==============================================================
# GRAMÁTICA: ListaDeclaracoes : Declaracao OutrasDeclaracoes
# ==============================================================
def p_ListaDeclaracoes(p):
    'ListaDeclaracoes : Declaracao OutrasDeclaracoes'
    p[0] = p[1] + p[2]

# ==============================================================
# GRAMÁTICA: OutrasDeclaracoes : ListaDeclaracoes | ε
# ==============================================================
def p_OutrasDeclaracoes_recursive(p):
    'OutrasDeclaracoes : ListaDeclaracoes'
    p[0] = p[1]

def p_OutrasDeclaracoes_empty(p):
    'OutrasDeclaracoes : '
    p[0] = ''

# ==============================================================
# GRAMÁTICA: Declaracao : NAME ':' TipoVar
# AÇÃO: adiciona a variável à tabela de símbolos (módulo semântico)
#       e gera a declaração C correspondente via c_decl_for
# ==============================================================
def p_Declaracao(p):
    'Declaracao : NAME PC TipoVar'
    name = p[1]
    xtype = p[3]
    # ação semântica: registrar variável (delegado ao módulo de semântica)
    try:
        from xu_semantic_comentado import symbols, c_decls, c_decl_for, semantic_errors
        if name in symbols:
            semantic_errors.append(f"Erro semântico: variável '{name}' já declarada.")
        else:
            symbols[name] = {'type': xtype}
            decl = c_decl_for(name, xtype)
            c_decls.append(decl)
            p[0] = decl + '\n'
    except Exception:
        # fallback simples se o módulo de semântica não tiver sido carregado
        p[0] = f'/* decl {name}:{xtype} */\n'

# ==============================================================
# GRAMÁTICA: TipoVar : INTEIRO | REAL | TEXTO | LOGICO
# ==============================================================
def p_TipoVar(p):
    'TipoVar : INTEIRO | REAL | TEXTO | LOGICO'
    p[0] = p[1]

# ==============================================================
# GRAMÁTICA: ListaComandos : Comando ListaComandos | ε
# ==============================================================
def p_ListaComandos(p):
    'ListaComandos : Comando ListaComandos'
    p[0] = [p[1]] + p[2]

def p_ListaComandos_empty(p):
    'ListaComandos : '
    p[0] = []

# ==============================================================
# GRAMÁTICA: Comando (vários tipos)
# ==============================================================
def p_Comando(p):
    '''Comando : ComandoAtribuicao
               | ComandoEntrada
               | ComandoSaida
               | ComandoCondicao
               | ComandoRepeticao
               | SubAlgoritmo
               | ComandoComentario'''
    p[0] = p[1]

# ==============================================================
# GRAMÁTICA: Comentario : COMMENT
# AÇÃO: converte comentário Xu -> comentário C
# ==============================================================
def p_ComandoComentario(p):
    'ComandoComentario : COMMENT'
    # transformar '# texto' -> '// texto' para inserir no C
    p[0] = f"//{p[1][1:].lstrip()}"

# ==============================================================
# GRAMÁTICA: ComandoAtribuicao : NAME ATRIB ExpressaoAritmetica
# AÇÃO: checa se variável existe (módulo semântico) e gera atribuição C
# ==============================================================
def p_ComandoAtribuicao(p):
    'ComandoAtribuicao : NAME ATRIB ExpressaoAritmetica'
    name = p[1]
    lineno = p.lineno(1)
    expr_code, expr_type = p[3]
    try:
        from xu_semantic_comentado import symbols, check_assignment, semantic_errors
        if name not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' não declarada.")
            p[0] = f'/* erro: {name} não declarado */'
            return
        target = symbols[name]['type']
        ok = check_assignment(target, expr_type, lineno)
        if not ok:
            p[0] = f'/* erro tipo: {target} <- {expr_type} */'
            return
        # se TEXTO usamos strcpy
        if target == 'TEXTO' and expr_type == 'TEXTO':
            p[0] = f'strcpy({name}, {expr_code});'
        else:
            p[0] = f'{name} = {expr_code};'
    except Exception:
        p[0] = f'{name} = {expr_code};'

# ==============================================================
# GRAMÁTICA: ComandoEntrada : LEIA NAME
# AÇÃO: gerar scanf/fgets conforme tipo
# ==============================================================
def p_ComandoEntrada(p):
    'ComandoEntrada : LEIA NAME'
    name = p[2]
    try:
        from xu_semantic_comentado import symbols, semantic_errors
        if name not in symbols:
            semantic_errors.append(f"Erro semântico: variável '{name}' não declarada para LEIA.")
            p[0] = f'/* erro leitura: {name} não declarado */'
            return
        xtype = symbols[name]['type']
        if xtype == 'INTEIRO': p[0] = f'scanf("%d", &{name});'
        elif xtype == 'REAL':  p[0] = f'scanf("%lf", &{name});'
        elif xtype == 'TEXTO': p[0] = f'fgets({name}, 256, stdin);'
        elif xtype == 'LOGICO': p[0] = f'scanf("%d", &{name});'
    except Exception:
        p[0] = f'/* LEIA {name} */'

# ==============================================================
# GRAMÁTICA: TipoSaida : NAME | CADEIA
# GRAMÁTICA: ComandoSaida : ESCREVA TipoSaida
# ==============================================================
def p_TipoSaida_var(p):
    'TipoSaida : NAME'
    p[0] = ('var', p[1])

def p_TipoSaida_cadeia(p):
    'TipoSaida : CADEIA'
    p[0] = ('str', p[1])


def p_ComandoSaida(p):
    'ComandoSaida : ESCREVA TipoSaida'
    kind, val = p[2]
    try:
        from xu_semantic_comentado import symbols, semantic_errors
        if kind == 'var':
            if val not in symbols:
                semantic_errors.append(f"Erro semântico: variável '{val}' não declarada para ESCREVA.")
                p[0] = '/* erro escrita */'
                return
            xtype = symbols[val]['type']
            if xtype == 'INTEIRO': p[0] = f'printf("%d\\n", {val});'
            elif xtype == 'REAL': p[0] = f'printf("%f\\n", {val});'
            elif xtype == 'TEXTO': p[0] = f'printf("%s\\n", {val});'
            elif xtype == 'LOGICO': p[0] = f'printf("%d\\n", {val});'
        else:
            # string literal
            p[0] = f'printf({val} "\\n");'
    except Exception:
        p[0] = '/* ESCREVA */'

# ==============================================================
# EXPRESSÕES ARITMÉTICAS
#   ExpressaoAritmetica : TermoAritmetico SentencaAritmetica
#   SentencaAritmetica : + TermoAritmetico SentencaAritmetica | - ... | ε
# AÇÃO: construir código C da expressão e inferir tipo simples
# ==============================================================

def p_ExpressaoAritmetica(p):
    'ExpressaoAritmetica : TermoAritmetico SentencaAritmetica'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        p[0] = (left_code + p[2], left_type)


def p_SentencaAritmetica_plus(p):
    "SentencaAritmetica : '+' TermoAritmetico SentencaAritmetica"
    right_code, right_type = p[2]
    suffix = f' + {right_code}'
    if p[3]: suffix += p[3]
    p[0] = suffix

def p_SentencaAritmetica_minus(p):
    "SentencaAritmetica : '-' TermoAritmetico SentencaAritmetica"
    right_code, right_type = p[2]
    suffix = f' - {right_code}'
    if p[3]: suffix += p[3]
    p[0] = suffix

def p_SentencaAritmetica_empty(p): 'SentencaAritmetica : '; p[0]=''

# ==============================================================
# TERMOS E FATORES
#   TermoAritmetico : FatorAritmetico ProposicaoAritmetica
#   ProposicaoAritmetica : '*' FatorAritmetico ... | '/' ... | ε
#   FatorAritmetico : NUMINT | NUMREAL | NAME | '(' ExpressaoAritmetica ')'
# ==============================================================

def p_TermoAritmetico(p):
    'TermoAritmetico : FatorAritmetico ProposicaoAritmetica'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        p[0] = (left_code + p[2], left_type)

def p_ProposicaoAritmetica_mult(p):
    "ProposicaoAritmetica : '*' FatorAritmetico ProposicaoAritmetica"
    right_code, right_type = p[2]
    suffix = f' * {right_code}'
    if p[3]: suffix += p[3]
    p[0] = suffix

def p_ProposicaoAritmetica_div(p):
    "ProposicaoAritmetica : '/' FatorAritmetico ProposicaoAritmetica"
    right_code, right_type = p[2]
    suffix = f' / {right_code}'
    if p[3]: suffix += p[3]
    p[0] = suffix

def p_ProposicaoAritmetica_empty(p): 'ProposicaoAritmetica : '; p[0]=''

def p_FatorAritmetico_numint(p): 'FatorAritmetico : NUMINT'; p[0]=(str(p[1]), 'INTEIRO')
def p_FatorAritmetico_numreal(p): 'FatorAritmetico : NUMREAL'; p[0]=(str(p[1]), 'REAL')
def p_FatorAritmetico_var(p): 'FatorAritmetico : NAME'; p[0]=(p[1], 'VAR')
def p_FatorAritmetico_group(p): 'FatorAritmetico : ( ExpressaoAritmetica )' ; p[0]=(f'({p[2][0]})', p[2][1])

# ==============================================================
# EXPRESSÕES RELACIONAIS E BOOLEANAS
#   TermoRelacional : ExpressaoAritmetica OP_REL ExpressaoAritmetica
#   SentencaRelacional : E_BOOL TermoRelacional SentencaRelacional | OU_BOOL ... | ε
# ==============================================================

def p_ExpressaoRelacional(p):
    'ExpressaoRelacional : TermoRelacional SentencaRelacional'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        p[0] = (left_code + p[2], 'LOGICO')

def p_TermoRelacional_comp(p):
    'TermoRelacional : ExpressaoAritmetica OP_REL ExpressaoAritmetica'
    lcode,ltype = p[1]
    op = p[2]
    rcode,rtype = p[3]
    p[0] = (f'({lcode} {op} {rcode})', 'LOGICO')

def p_TermoRelacional_group(p): 'TermoRelacional : ( ExpressaoRelacional )' ; p[0]=(f'({p[2][0]})', p[2][1])

def p_SentencaRelacional_bool(p): 'SentencaRelacional : E_BOOL TermoRelacional SentencaRelacional'; p[0]=f' && {p[2][0]}'
def p_SentencaRelacional_bool_ou(p): 'SentencaRelacional : OU_BOOL TermoRelacional SentencaRelacional'; p[0]=f' || {p[2][0]}'

def p_SentencaRelacional_empty(p): 'SentencaRelacional : '; p[0]=''

# ==============================================================
# ERRO SINTÁTICO
# ==============================================================
def p_error(p):
    if p:
        print(f"Erro sintático: token inesperado '{p.value}' na linha {p.lineno}", file=sys.stderr)
    else:
        print("Erro sintático: fim de arquivo inesperado", file=sys.stderr)

# ==============================================================
# FIM DO PARSER
# ==============================================================
