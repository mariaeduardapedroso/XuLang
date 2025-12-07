"""
xu_compiler.py
Compilador simples de XuLang -> C usando PLY (lex + yacc).

Como usar:
    python xu_compiler.py entrada.xu > saida.c
    gcc saida.c -o programa
    ./programa

Funcionalidades:
 - Lexer com mensagens de erro léxico (linha, caractere)
 - Parser com mensagens de erro sintático (linha)
 - Tabela de símbolos e checagem semântica (variáveis não declaradas, tipos incompatíveis)
 - Geração de código C (int main() { ... return 0; })
 - Comentários e mensagens descritivas
 - Conversão de tipos:
     INTEIRO -> int
     REAL    -> double
     TEXTO   -> char nome[256];
     LOGICO  -> int (0 ou 1)
"""

import sys
import ply.lex as lex
import ply.yacc as yacc

# ------------------------------
# LEXER
# ------------------------------

# Lista de tokens
tokens = (
    # Tokens básicos
    'NAME',
    'NUMINT',
    'NUMREAL',
    'CADEIA',
    'OP_REL',
    'ATRIB',
    'PC',
    'COMMENT',

    # Palavras reservadas
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

    # Booleanos
    'E_BOOL',
    'OU_BOOL'
)

# Operadores aritméticos e parênteses serão tratados como literais
literals = ['+', '-', '*', '/', '(', ')']

# Palavras reservadas (keywords) da XuLang (mantemos uppercase)
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
    'OU': 'OU_BOOL',
}

# Atribuição "<-"
def t_ATRIB(t):
    r'\<\-'
    return t
# t_ATRIB = r'\<\-'  # token ATRIB

# Delimitador ':' (chamei de PC porque estava assim no original)
t_PC = r':'

# Não ignorar newline — vamos tratá-lo explicitamente
t_ignore = " \t"

# Regra para Números Reais (têm ponto)
def t_NUMREAL(t):
    r'\d+\.\d+'
    try:
        t.value = float(t.value)
    except ValueError:
        t.value = 0.0
    return t

# Regra para Inteiros
def t_NUMINT(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        t.value = 0
    return t

# Comentário: # até fim da linha. Ignoramos o comentário
def t_COMMENT(t):
    r'\#.*'
    t.value = t.value
    return t

# String literal (CADEIA)
def t_CADEIA(t):
    r'\"([^\\\n]|(\\.))*?\"'
    # mantém com as aspas (para impressão direta em printf)
    return t

# Operadores relacionais multi-char e single-char
def t_OP_REL(t):
    r'<=|>=|==|!=|<|>'
    t.value = t.value
    return t

# NAME e palavras reservadas. Variáveis seguem padrão: letras e dígitos e underscores.
def t_NAME(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    up = t.value.upper()
    if up in reserved:
        t.type = reserved[up]
        # armazenamos valor upper para facilitar parsing (keywords em maiúsculas)
        t.value = up
    else:
        # variável - mantemos o nome original (case-sensitive)
        t.type = 'NAME'
    return t

# Newline - para contar linhas
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    # retornamos o token NEWLINE (caso a gramática precise)
    pass

# Handler de erro léxico
def t_error(t):
    print(f"Erro léxico: caractere ilegal '{t.value[0]}' na linha {t.lexer.lineno}", file=sys.stderr)
    t.lexer.skip(1)

# Construir o lexer
lexer = lex.lex()
lexer.lineno = 1
lexer.comment = None

# ------------------------------
# ESTRUTURAS PARA GERAÇÃO DE C E TABELA DE SÍMBOLOS
# ------------------------------

# Tabela de símbolos: nome -> {'type': 'INTEIRO'|'REAL'|'TEXTO'|'LOGICO', 'c_decl': 'int x;'}
symbols = {}

# Lista de declarações C geradas
c_decls = []

# Mantém erros semânticos encontrados
semantic_errors = []

# Auxiliar para gerar nomes temporários se necessário (não usado extensivamente aqui)
temp_count = 0
def new_temp():
    global temp_count
    temp_count += 1
    return f"_tmp{temp_count}"

# Helper para mapear tipos XuLang -> C
def map_type_to_c(xutype):
    if xutype == 'INTEIRO':
        return 'int'
    if xutype == 'REAL':
        return 'double'
    if xutype == 'TEXTO':
        # vamos declarar char nome[256];
        return 'char'
    if xutype == 'LOGICO':
        return 'int'
    return None

# Helper para gerar declaração C para cada variável
def c_decl_for(varname, xutype):
    ctype = map_type_to_c(xutype)
    if ctype == 'char':
        return f'char {varname}[256];'
    else:
        return f'{ctype} {varname};'

# Checagem de compatibilidade de atribuição simples
def check_assignment(target_type, expr_type, lineno):
    # regras simples:
    # - INTEIRO <- REAL  => error (explicit cast required): proibimos
    # - REAL <- INTEIRO  => permitido (promoção)
    # - LOGICO tratado como int (0/1). Permitimos atribuir comparações (booleanas) a LOGICO
    if target_type == expr_type:
        return True
    if target_type == 'REAL' and expr_type == 'INTEIRO':
        return True  # promoção permitida
    if target_type == 'INTEIRO' and expr_type == 'REAL':
        semantic_errors.append(f"Erro semântico (linha {lineno}): atribuição de REAL para INTEIRO pode perder precisão.")
        return False
    # permitir atribuir NUMINT/NUMREAL literais conforme tipos
    # permitir incompatibilidades envolvendo TEXTO apenas com CADEIA/TEXTO
    if target_type == 'TEXTO' and expr_type == 'TEXTO':
        return True
    # LOGICO <-> INTEIRO (aceitamos comparisons producing LOGICO)
    if target_type == 'LOGICO' and expr_type in ('LOGICO','INTEIRO'):
        return True
    # caso padrão
    semantic_errors.append(f"Erro semântico (linha {lineno}): tipo incompatível na atribuição ({target_type} <- {expr_type}).")
    return False

# ------------------------------
# PARSER (YACC)
# ------------------------------

# Precedência para evitar ambiguidades em expressões
precedence = (
    ('left', 'E_BOOL', 'OU_BOOL'),
    ('left', 'OP_REL'),
    ('left', '+', '-'),
    ('left', '*', '/'),
)

# Programa -> : DECLARACOES ListaDeclaracoes : PROGRAMA ListaComandos
def p_Programa(p):
    'Programa : PC DECLARACOES ListaDeclaracoes PC PROGRAMA ListaComandos'
    # Ao final do parsing geramos o cabeçalho C + declarações e corpo
    c_out = []
    c_out.append('/* Código gerado automaticamente por xu_compiler.py */')
    c_out.append('#include <stdio.h>')
    c_out.append('#include <stdlib.h>')
    c_out.append('#include <string.h>')
    c_out.append('')
    c_out.append('int main() {')
    # declarações
    if c_decls:
        c_out.append('    /* Declarações */')
        for d in c_decls:
            c_out.append('    ' + d)
        c_out.append('')
    # corpo
    c_out.append('    /* Programa */')
    c_body = p[6]  # comandos do programa
    for line in c_body:
        # cada line já vem indentado corretamente
        c_out.append('    ' + line)
    c_out.append('')
    c_out.append('    return 0;')
    c_out.append('}')
    # imprimir código resultante (para redirecionamento > arquivo.c)
    print('\n'.join(c_out))

# ListaDeclaracoes -> Declaracao OutrasDeclaracoes
def p_ListaDeclaracoes(p):
    'ListaDeclaracoes : Declaracao OutrasDeclaracoes'
    p[0] = p[1] + p[2] # apenas repassa

# OutrasDeclaracoes -> ListaDeclaracoes | empty
def p_OutrasDeclaracoes_recursive(p):
    'OutrasDeclaracoes : ListaDeclaracoes'
    p[0] = p[1]   # apenas repassa

def p_OutrasDeclaracoes_empty(p):
    'OutrasDeclaracoes : '
    p[0] = ''

# Declaracao -> VARIAVEL : TipoVar
def p_Declaracao(p):
    'Declaracao : NAME PC TipoVar'
    varname = p[1]
    xtype = p[3]
    lineno = p.lineno(1)
    if varname in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{varname}' já declarada.")
    else:
        symbols[varname] = {'type': xtype}
        decl = c_decl_for(varname, xtype)
        p[0] = decl + '\n'
        c_decls.append(decl)

# TipoVar -> INTEIRO | REAL | TEXTO | LOGICO
def p_TipoVar(p):
    '''TipoVar : INTEIRO
               | REAL
               | TEXTO
               | LOGICO'''
    p[0] = p[1]

# ------------------------------
# COMANDOS / BLOCOS
# ListaComandos -> Comando OutrosComandos
# ------------------------------
def p_ListaComandos(p):
    'ListaComandos : Comando ListaComandos'
    p[0] = [p[1]] + p[2]

def p_ListaComandos_empty(p):
    'ListaComandos : '
    p[0] = []


# Comando -> varios
def p_Comando(p):
    '''Comando : ComandoAtribuicao 
               | ComandoEntrada 
               | ComandoSaida 
               | ComandoCondicao
               | ComandoRepeticao
               | SubAlgoritmo
               | ComandoComentario
    '''
    p[0] = p[1] # para comandos compostos que retornam código

def p_ComandoComentario(p):
    'ComandoComentario : COMMENT'
    p[0] = f'//{p[1][1:].lstrip()}'  # transforma comentário XuLang em comentário C

# Comando de atribuição: VARIAVEL <- ExpressaoAritmetica
def p_ComandoAtribuicao(p):
    'ComandoAtribuicao : NAME ATRIB ExpressaoAritmetica'
    var = p[1]
    lineno = p.lineno(1)
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada.")
        target_type = None
    else:
        target_type = symbols[var]['type']
    expr_code, expr_type = p[3]  # ExpressaoAritmetica retorna (code_str, type)
    if target_type:
        ok = check_assignment(target_type, expr_type, lineno)
        # gerar código C de atribuição (tratando TEXTO com strcpy)
        if target_type == 'TEXTO':
            # se expressão for literal cadeia ou variável TEXTO -> usar strcpy
            if expr_type == 'TEXTO':
                p[0] = f'strcpy({var}, {expr_code});'
            else:
                semantic_errors.append(f"Erro semântico (linha {lineno}): não é possível atribuir tipo {expr_type} a TEXTO.")
        else:
            p[0] = f'{var} = {expr_code};'
            # se destino REAL e expr int, em C a promoção é automática

# ComandoEntrada -> LEIA VARIAVEL
def p_ComandoEntrada(p):
    'ComandoEntrada : LEIA NAME'
    var = p[2]
    lineno = p.lineno(2)
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para LEIA.")
        return
    xtype = symbols[var]['type']
    # Gerar scanf apropriado
    if xtype == 'INTEIRO':
        p[0] = f'scanf("%d", &{var});'
    elif xtype == 'REAL':
        p[0] = f'scanf("%lf", &{var});'
    elif xtype == 'TEXTO':
        p[0] = f'scanf("%255s", {var});'
        # lê string (sem espaços) - para ler linhas completas seria mais trabalho
    elif xtype == 'LOGICO':
        p[0] = f'scanf("%d", &{var});'
    else:
        semantic_errors.append(f"Erro semântico (linha {lineno}): tipo desconhecido em LEIA para '{var}'.")

# TipoSaida -> VARIAVEL | CADEIA
def p_TipoSaida_var(p):
    'TipoSaida : NAME'
    p[0] = ('var', p[1])

def p_TipoSaida_cadeia(p):
    'TipoSaida : CADEIA'
    p[0] = ('str', p[1])

# ComandoSaida -> ESCREVA TipoSaida
def p_ComandoSaida(p):
    'ComandoSaida : ESCREVA TipoSaida'
    kind, val = p[2]
    if kind == 'var':
        var = val
        lineno = p.lineno(2)
        if var not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para ESCREVA.")
            return
        xtype = symbols[var]['type']
        if xtype == 'INTEIRO':
            p[0] = f'printf("%d\\n", {var});'
        elif xtype == 'REAL':
            p[0] = f'printf("%f\\n", {var});'
        elif xtype == 'TEXTO':
            p[0] = f'printf("%s\\n", {var});'
        elif xtype == 'LOGICO':
            p[0] = f'printf("%d\\n", {var});'
        else:
            semantic_errors.append(f"Erro semântico: tipo desconhecido para ESCREVA '{var}'.")
    else:
        # string literal (CADEIA em p[2])
        text = val  # mantém as aspas
        # Em C, "a" "\n" é concatenado em tempo de compilação
        p[0] = f'printf({text} "\\n");'

def indent(lines, spaces=4):
    return "\n".join(" " * spaces + line for line in lines)

# ComandoCondicao -> SE ExpressaoRelacional ENTAO Comando ContraCondicao
def p_ComandoCondicao(p):
    'ComandoCondicao : SE ExpressaoRelacional ENTAO ListaComandos ContraCondicao FIM'
    expr_code, expr_type = p[2]
    comando_if = "\n".join(" " * 4 + line for line in p[4])       # já é string do comando
    contra = p[5]             # string (else { ... } ou '')

    # monta o código
    codigo = f"if ({expr_code}) {{\n{comando_if}\n}}"
    if contra != '':
        codigo += f"\n{contra}"

    # devolve para cima
    p[0] = codigo


# ContraCondicao -> SENAO Comando | empty
def p_ContraCondicao_senao(p):
    'ContraCondicao : SENAO Comando'
    comando_else = p[2]
    p[0] = f'else {{\n{comando_else}\n}}'

def p_ContraCondicao_empty(p):
    'ContraCondicao : '
    p[0] = ''


# ComandoRepeticao -> ENQUANTO ExpressaoRelacional Comando
def p_ComandoRepeticao(p):
    'ComandoRepeticao : ENQUANTO ExpressaoRelacional ListaComandos FIM'
    expr_code, expr_type = p[2]

    expr_code, expr_type = p[2]
    cmd_code = "\n".join(" " * 4 + line for line in p[3])  # código do comando interno

    code = f"while ({expr_code}) {{\n{cmd_code}\n}}"
    p[0] = code

# SubAlgoritmo -> INICIO ListaComandos FIM
def p_SubAlgoritmo(p):
    'SubAlgoritmo : INICIO ListaComandos FIM'
    # abrir e fechar chaves
    cmds = p[2]  # string com todos os comandos dentro do bloco
    p[0] = "{\n" + cmds + "\n}"
# ------------------------------
# EXPRESSÕES ARITMÉTICAS E RELACIONAIS
# Vamos fazer com retorno de (c_code, tipo)
# ------------------------------

# ExpressaoAritmetica -> TermoAritmetico SentencaAritmetica
def p_ExpressaoAritmetica(p):
    'ExpressaoAritmetica : TermoAritmetico SentencaAritmetica'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        expr_code = left_code + p[2]
        # heurística simples para tipo
        res_type = left_type if left_type is not None else 'INTEIRO'
        p[0] = (expr_code, res_type)

# SentencaAritmetica -> + Termo Sentenca | - Termo Sentenca | epsilon
def p_SentencaAritmetica_plus(p):
    'SentencaAritmetica : \'+\' TermoAritmetico SentencaAritmetica'
    right_code, right_type = p[2]
    suffix = f' + {right_code}'
    if p[3]:
        suffix = suffix + p[3]
    p[0] = suffix

def p_SentencaAritmetica_minus(p):
    'SentencaAritmetica : \'-\' TermoAritmetico SentencaAritmetica'
    right_code, right_type = p[2]
    suffix = f' - {right_code}'
    if p[3]:
        suffix = suffix + p[3]
    p[0] = suffix

def p_SentencaAritmetica_empty(p):
    'SentencaAritmetica : '
    p[0] = ''

# TermoAritmetico -> Fator ProposicaoAritmetica
def p_TermoAritmetico(p):
    'TermoAritmetico : FatorAritmetico ProposicaoAritmetica'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        expr_code = left_code + p[2]
        res_type = 'REAL' if left_type == 'REAL' else 'INTEIRO'
        p[0] = (expr_code, res_type)

def p_ProposicaoAritmetica_mult(p):
    'ProposicaoAritmetica : \'*\' FatorAritmetico ProposicaoAritmetica'
    right_code, right_type = p[2]
    suffix = f' * {right_code}'
    if p[3]:
        suffix = suffix + p[3]
    p[0] = suffix

def p_ProposicaoAritmetica_div(p):
    'ProposicaoAritmetica : \'/\' FatorAritmetico ProposicaoAritmetica'
    right_code, right_type = p[2]
    suffix = f' / {right_code}'
    if p[3]:
        suffix = suffix + p[3]
    p[0] = suffix

def p_ProposicaoAritmetica_empty(p):
    'ProposicaoAritmetica : '
    p[0] = ''

# FatorAritmetico -> NUMINT | NUMREAL | VARIAVEL | '(' ExpressaoAritmetica ')'
def p_FatorAritmetico_numint(p):
    'FatorAritmetico : NUMINT'
    p[0] = (str(p[1]), 'INTEIRO')

def p_FatorAritmetico_numreal(p):
    'FatorAritmetico : NUMREAL'
    p[0] = (str(p[1]), 'REAL')

def p_FatorAritmetico_var(p):
    'FatorAritmetico : NAME'
    var = p[1]
    lineno = p.lineno(1)
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' usada antes de declaração.")
        p[0] = (var, 'INDEFINIDO')
    else:
        p[0] = (var, symbols[var]['type'])

def p_FatorAritmetico_group(p):
    'FatorAritmetico : \'(\' ExpressaoAritmetica \')\''
    inner_code, inner_type = p[2]
    p[0] = (f'({inner_code})', inner_type)

# ------------------------------
# EXPRESSÕES RELACIONAIS / BOOLEANS
# ------------------------------

def p_ExpressaoRelacional(p):
    'ExpressaoRelacional : TermoRelacional SentencaRelacional'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type)
    else:
        p[0] = (left_code + p[2], 'LOGICO')

def p_TermoRelacional_comp(p):
    'TermoRelacional : ExpressaoAritmetica OP_REL ExpressaoAritmetica'
    left_code, left_type = p[1]
    op = p[2]
    right_code, right_type = p[3]
    code = f'({left_code} {op} {right_code})'
    p[0] = (code, 'LOGICO')

def p_TermoRelacional_group(p):
    'TermoRelacional : \'(\' ExpressaoRelacional \')\''
    inner_code, inner_type = p[2]
    p[0] = (f'({inner_code})', inner_type)

def p_SentencaRelacional_bool(p):
    'SentencaRelacional : E_BOOL TermoRelacional SentencaRelacional'
    right_code, right_type = p[2]
    suffix = f' && {right_code}'
    if p[3]:
        suffix += p[3]
    p[0] = suffix

def p_SentencaRelacional_bool_ou(p):
    'SentencaRelacional : OU_BOOL TermoRelacional SentencaRelacional'
    right_code, right_type = p[2]
    suffix = f' || {right_code}'
    if p[3]:
        suffix += p[3]
    p[0] = suffix

def p_SentencaRelacional_empty(p):
    'SentencaRelacional : '
    p[0] = ''

# ------------------------------
# Tratamento de erro sintático
# ------------------------------
def p_error(p):
    if p:
        print(f"Erro sintático: token inesperado '{p.value}' na linha {p.lineno}", file=sys.stderr)
    else:
        print("Erro sintático: fim de arquivo inesperado", file=sys.stderr)

# ------------------------------
# Função principal: leitura do arquivo de entrada e parse
# ------------------------------
def main():
    if len(sys.argv) < 2:
        print("Uso: python xu_compiler.py <arquivo.xu>")
        return
    fname = sys.argv[1]
    data = open(fname, 'r', encoding='utf-8').read()
    # Forçar newline final para facilitar comentários e regras baseadas em linhas
    if not data.endswith('\n'):
        data += '\n'
    # Parse
    parser = yacc.yacc()
    parser.parse(data, lexer=lexer)
    # Ao final, reportar erros semânticos (se houver)
    if semantic_errors:
        sys.stderr.write("Erros semânticos detectados:\n")
        for e in semantic_errors:
            sys.stderr.write(e + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
