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
import os # NOVO: Para operações de arquivo
from pathlib import Path # NOVO: Para manipulação de caminhos e nomes de arquivo

# ------------------------------
# LEXER (Analisador Léxico)
# Responsável por transformar a sequência de caracteres (código XuLang)
# em uma sequência de tokens (unidades significativas).
# ------------------------------

# Lista de tokens que o Lexer reconhece.
tokens = (
    # Tokens básicos (que representam dados ou símbolos)
    'NAME',         # Identificadores de variáveis (ex: 'x', 'nome_usuario')
    'NUMINT',       # Números inteiros (ex: 10, 42)
    'NUMREAL',      # Números de ponto flutuante (ex: 3.14, 0.5)
    'CADEIA',       # Strings literais entre aspas (ex: "Olá mundo")
    'OP_REL',       # Operadores relacionais (ex: <=, >=, ==, !=, <, >)
    'ATRIB',        # Operador de atribuição (<-)
    'PC',           # Ponto e vírgula/Delimitador (:)
    'COMMENT',      # Linha de comentário (#...)

    # Palavras reservadas (keywords) da XuLang
    'DECLARACOES',  # Início da seção de declaração de variáveis
    'PROGRAMA',     # Início do corpo principal do programa
    'INTEIRO',      # Tipo de dado inteiro
    'REAL',         # Tipo de dado real (ponto flutuante)
    'TEXTO',        # Tipo de dado para strings
    'LOGICO',       # Tipo de dado booleano
    'LEIA',         # Comando de entrada de dados (input)
    'ESCREVA',      # Comando de saída de dados (output)
    'SE',           # Início da estrutura condicional (if)
    'SENAO',        # Cláusula alternativa (else)
    'ENTAO',        # Separa a condição do bloco de código (then)
    'ENQUANTO',     # Início da estrutura de repetição (while)
    'INICIO',       # Início de um bloco de comandos
    'FIM',          # Fim de uma estrutura ou bloco

    # Booleanos
    'E_BOOL',       # Operador lógico E (AND)
    'OU_BOOL'       # Operador lógico OU (OR)
)

# Operadores aritméticos e parênteses serão tratados como literais
# O PLY reconhece esses caracteres automaticamente como tokens únicos.
literals = ['+', '-', '*', '/', '(', ')']

# Mapeamento das palavras reservadas para seus respectivos tokens.
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
    'E': 'E_BOOL',  # Palavra 'E' para AND lógico
    'OU': 'OU_BOOL', # Palavra 'OU' para OR lógico
}

# Definição do token ATRIB (atribuição) usando expressão regular
def t_ATRIB(t):
    r'\<\-' # Corresponde exatamente à sequência de caracteres "<-"
    return t

# Delimitador PC (Dois Pontos)
t_PC = r':'

# Caracteres a ignorar: espaços e tabulações
t_ignore = " \t"

# Regra para Números Reais (têm ponto decimal)
def t_NUMREAL(t):
    r'\d+\.\d+' # Pelo menos um dígito, um ponto, e mais um dígito
    try:
        t.value = float(t.value) # Converte o valor para float em Python
    except ValueError:
        t.value = 0.0
    return t

# Regra para Inteiros
def t_NUMINT(t):
    r'\d+' # Sequência de um ou mais dígitos
    try:
        t.value = int(t.value) # Converte o valor para int em Python
    except ValueError:
        t.value = 0
    return t

# Comentário: # até o fim da linha. O token COMMENT é retornado mas
# o parser o ignora, transformando em comentário C.
def t_COMMENT(t):
    r'\#.*' # Corresponde a '#' seguido de qualquer coisa até a quebra de linha
    t.value = t.value
    # Não atualizamos a linha aqui, pois a regra t_NEWLINE fará isso.
    return t

# String literal (CADEIA)
def t_CADEIA(t):
    r'\"([^\\\n]|(\\.))*?\"' # Regex para strings entre aspas, permitindo escapes
    # mantém com as aspas (útil para impressão direta em printf)
    return t

# Operadores relacionais multi-char (<=, >=, ==, !=) e single-char (<, >)
def t_OP_REL(t):
    r'<=|>=|==|!=|<|>'
    t.value = t.value # O valor é o próprio operador (ex: '==')
    return t

# NAME e palavras reservadas. Identificadores (variáveis)
def t_NAME(t):
    r'[A-Za-z_][A-Za-z0-9_]*' # Começa com letra ou underscore, seguido de letras/dígitos/underscores
    up = t.value.upper()
    if up in reserved:
        # Se for uma palavra reservada (em MAIÚSCULAS)
        t.type = reserved[up] # Define o tipo de token como a palavra reservada (ex: 'PROGRAMA')
        # armazenamos valor upper para facilitar parsing (keywords em maiúsculas)
        t.value = up
    else:
        # Se for um identificador de variável
        t.type = 'NAME'
        # variável - mantemos o nome original (case-sensitive em XuLang, que será mapeado para C)
    return t

# Newline - para contar linhas e manter o controle da posição
def t_NEWLINE(t):
    r'\n+' # Captura uma ou mais quebras de linha
    t.lexer.lineno += len(t.value) # Incrementa o contador de linha do lexer
    # retornamos o token NEWLINE (caso a gramática precise), mas aqui optamos por ignorar (pass)
    pass

# Handler de erro léxico
def t_error(t):
    # Imprime uma mensagem de erro indicando o caractere ilegal e a linha.
    print(f"Erro léxico: caractere ilegal '{t.value[0]}' na linha {t.lexer.lineno}", file=sys.stderr)
    t.lexer.skip(1) # Ignora o caractere e tenta continuar a análise

# Construir o lexer
lexer = lex.lex()
lexer.lineno = 1
lexer.comment = None # Variável auxiliar para lidar com comentários multi-linhas (não usada aqui)

# ------------------------------
# ESTRUTURAS PARA GERAÇÃO DE C E TABELA DE SÍMBOLOS
# São estruturas de dados usadas para a análise semântica e a geração de código intermediário/final.
# ------------------------------

# Tabela de símbolos: armazena informações sobre as variáveis declaradas.
# Formato: nome_variavel -> {'type': 'INTEIRO'|'REAL'|'TEXTO'|'LOGICO'}
symbols = {}

# Lista de declarações C geradas (ex: 'int x;', 'double y;')
c_decls = []

# Mantém erros semânticos encontrados durante a análise (ex: variável não declarada, tipo incompatível)
semantic_errors = []

# Auxiliar para gerar nomes temporários se necessário (não usado extensivamente aqui)
temp_count = 0
def new_temp():
    global temp_count
    temp_count += 1
    return f"_tmp{temp_count}"

# Helper para mapear tipos XuLang -> C
def map_type_to_c(xutype):
    # Mapeia os tipos de dados da linguagem XuLang para os tipos correspondentes em C.
    if xutype == 'INTEIRO':
        return 'int'
    if xutype == 'REAL':
        return 'double'
    if xutype == 'TEXTO':
        # Em C, a string é um array de caracteres (char nome[256];)
        return 'char'
    if xutype == 'LOGICO':
        return 'int' # Booleanos em C são representados por inteiros (0 para falso, !=0 para verdadeiro)
    return None

# Helper para gerar declaração C para cada variável
def c_decl_for(varname, xutype):
    ctype = map_type_to_c(xutype)
    if ctype == 'char':
        return f'char {varname}[256];' # Declaração especial para strings (TEXTO)
    else:
        return f'{ctype} {varname};' # Declaração padrão para outros tipos

# Checagem de compatibilidade de atribuição simples
def check_assignment(target_type, expr_type, lineno):
    # Implementa as regras de coerção de tipos para a atribuição:
    if target_type == expr_type:
        return True # Tipos idênticos, OK
    if target_type == 'REAL' and expr_type == 'INTEIRO':
        return True  # Promoção permitida (Inteiro para Real), sem perda de dados
    if target_type == 'INTEIRO' and expr_type == 'REAL':
        # Erro: atribuição de Real para Inteiro pode perder a parte decimal (precisão).
        semantic_errors.append(f"Erro semântico (linha {lineno}): atribuição de REAL para INTEIRO pode perder precisão.")
        return False
    # permitir incompatibilidades envolvendo TEXTO apenas com CADEIA/TEXTO
    if target_type == 'TEXTO' and expr_type == 'TEXTO':
        return True
    # LOGICO <-> INTEIRO (aceitamos comparisons producing LOGICO)
    if target_type == 'LOGICO' and expr_type in ('LOGICO','INTEIRO'):
        return True
    # caso padrão: qualquer outra incompatibilidade
    semantic_errors.append(f"Erro semântico (linha {lineno}): tipo incompatível na atribuição ({target_type} <- {expr_type}).")
    return False

# ------------------------------
# PARSER (YACC) - Analisador Sintático
# Responsável por verificar se a sequência de tokens obedece à gramática da XuLang
# e, simultaneamente, realizar a análise semântica e a geração de código C.
# ------------------------------

# Precedência e associatividade dos operadores para resolver ambiguidades na gramática
precedence = (
    ('left', 'E_BOOL', 'OU_BOOL'),  # E/OU têm a menor precedência
    ('left', 'OP_REL'),             # Operadores relacionais
    ('left', '+', '-'),             # Adição/Subtração
    ('left', '*', '/'),             # Multiplicação/Divisão (maior precedência)
)

# Programa -> : DECLARACOES ListaDeclaracoes : PROGRAMA ListaComandos
def p_Programa(p):
    'Programa : PC DECLARACOES ListaDeclaracoes PC PROGRAMA ListaComandos'
    # Esta é a regra de topo (Root Rule). Ela encapsula todo o código C.
    c_out = []
    c_out.append('/* Código gerado automaticamente por xu_compiler.py */')
    # Inclusão de bibliotecas C necessárias
    c_out.append('#include <stdio.h>')
    c_out.append('#include <stdlib.h>')
    c_out.append('#include <string.h>') # Necessária para funções como strcpy (para TEXTO)
    c_out.append('')
    c_out.append('int main() {') # Início da função principal em C
    # Adiciona as declarações de variáveis geradas (armazenadas em c_decls)
    if c_decls:
        c_out.append('    /* Declarações */')
        for d in c_decls:
            c_out.append('    ' + d)
        c_out.append('')
    # Adiciona o corpo do programa (comandos executáveis)
    c_out.append('    /* Programa */')
    c_body = p[6]  # p[6] é o resultado da regra 'ListaComandos'
    for line in c_body:
        # cada line já vem indentado corretamente
        c_out.append('    ' + line)
    c_out.append('')
    c_out.append('    return 0;') # Fim da função principal
    c_out.append('}')
    # imprimir código resultante (para redirecionamento > arquivo.c)
    print('\n'.join(c_out))
    # Armazena o código C gerado no objeto parser (p.parser) para uso posterior na main
    p.parser.c_output_code = '\n'.join(c_out)

# ListaDeclaracoes -> Declaracao OutrasDeclaracoes
def p_ListaDeclaracoes(p):
    'ListaDeclaracoes : Declaracao OutrasDeclaracoes'
    # Concatena as declarações e repassa o resultado.
    p[0] = p[1] + p[2] # apenas repassa

# OutrasDeclaracoes -> ListaDeclaracoes | empty
def p_OutrasDeclaracoes_recursive(p):
    'OutrasDeclaracoes : ListaDeclaracoes'
    p[0] = p[1]   # apenas repassa (continuação da lista de declarações)

def p_OutrasDeclaracoes_empty(p):
    'OutrasDeclaracoes : '
    p[0] = '' # Se não houver mais declarações, o resultado é vazio

# Declaracao -> VARIAVEL : TipoVar
def p_Declaracao(p):
    'Declaracao : NAME PC TipoVar'
    varname = p[1] # Nome da variável
    xtype = p[3]   # Tipo da variável (ex: 'INTEIRO')
    lineno = p.lineno(1)
    if varname in symbols:
        # Checagem semântica: variável já declarada
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{varname}' já declarada.")
    else:
        # Adiciona a variável à tabela de símbolos
        symbols[varname] = {'type': xtype}
        # Gera a declaração C correspondente
        decl = c_decl_for(varname, xtype)
        p[0] = decl + '\n'
        c_decls.append(decl) # Armazena a declaração para o cabeçalho C

# TipoVar -> INTEIRO | REAL | TEXTO | LOGICO
def p_TipoVar(p):
    '''TipoVar : INTEIRO
               | REAL
               | TEXTO
               | LOGICO'''
    p[0] = p[1] # Retorna a string do tipo (ex: 'INTEIRO')

# ------------------------------
# COMANDOS / BLOCOS
# ListaComandos -> Comando OutrosComandos (Comandos de execução)
# ------------------------------
# ListaComandos é recursiva à direita, agrupando todos os comandos sequencialmente
def p_ListaComandos(p):
    'ListaComandos : Comando ListaComandos'
    # O resultado é uma lista de strings de código C (uma linha por comando principal)
    p[0] = [p[1]] + p[2]

def p_ListaComandos_empty(p):
    'ListaComandos : '
    p[0] = [] # Lista vazia se não houver mais comandos


# Comando -> varios (Regra que unifica todos os tipos de comandos)
def p_Comando(p):
    '''Comando : ComandoAtribuicao 
               | ComandoEntrada 
               | ComandoSaida 
               | ComandoCondicao
               | ComandoRepeticao
               | SubAlgoritmo
               | ComandoComentario
    '''
    p[0] = p[1] # Retorna o código C gerado pelo comando específico

def p_ComandoComentario(p):
    'ComandoComentario : COMMENT'
    # Transforma o comentário de XuLang (#...) em comentário de C (//...)
    p[0] = f'//{p[1][1:].lstrip()}'  # remove o '#' inicial e espaços em branco

# Comando de atribuição: VARIAVEL <- ExpressaoAritmetica
def p_ComandoAtribuicao(p):
    'ComandoAtribuicao : NAME ATRIB ExpressaoAritmetica'
    var = p[1]
    lineno = p.lineno(1)
    # Checagem Semântica: A variável foi declarada?
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada.")
        target_type = None
    else:
        target_type = symbols[var]['type'] # Pega o tipo declarado da variável
    expr_code, expr_type = p[3]  # ExpressaoAritmetica retorna (código C, tipo XuLang)

    if target_type:
        ok = check_assignment(target_type, expr_type, lineno) # Checa a compatibilidade de tipos
        # Geração de código C:
        if target_type == 'TEXTO':
            # Strings (TEXTO) usam strcpy() em C, não o operador '='
            if expr_type == 'TEXTO':
                p[0] = f'strcpy({var}, {expr_code});' # Uso de strcpy para strings
            else:
                semantic_errors.append(f"Erro semântico (linha {lineno}): não é possível atribuir tipo {expr_type} a TEXTO.")
                p[0] = f'/* ERRO: Atribuição inválida para {var} */'
        elif ok:
            p[0] = f'{var} = {expr_code};' # Atribuição padrão para INTEIRO, REAL, LOGICO
        else:
            p[0] = f'/* ERRO: Atribuição incompatível para {var} */'
    else:
        p[0] = f'/* ERRO: Variável não declarada {var} */'

# ComandoEntrada -> LEIA VARIAVEL
def p_ComandoEntrada(p):
    'ComandoEntrada : LEIA NAME'
    var = p[2]
    lineno = p.lineno(2)
    # Checagem Semântica
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para LEIA.")
        return
    xtype = symbols[var]['type'] # Pega o tipo da variável
    # Geração de código C usando scanf/fgets apropriado
    if xtype == 'INTEIRO':
        p[0] = f'scanf("%d", &{var});' # %d para int, & para endereço de memória
    elif xtype == 'REAL':
        p[0] = f'scanf("%lf", &{var});' # %lf para double em scanf
    elif xtype == 'TEXTO':
        # Nota: fgets é mais seguro que scanf("%s") para strings
        p[0]= f'fgets({var}, 256, stdin);'
        # Adiciona tratamento para remover o newline que fgets pode capturar
        p[0] += f'\n    {var}[strcspn({var}, "\\n")] = 0;'
    elif xtype == 'LOGICO':
        p[0] = f'scanf("%d", &{var});' # Lê 0 ou 1
    else:
        semantic_errors.append(f"Erro semântico (linha {lineno}): tipo desconhecido em LEIA para '{var}'.")

# TipoSaida -> VARIAVEL | CADEIA
def p_TipoSaida_var(p):
    'TipoSaida : NAME'
    p[0] = ('var', p[1]) # Retorna (tipo, nome_da_variavel)

def p_TipoSaida_cadeia(p):
    'TipoSaida : CADEIA'
    p[0] = ('str', p[1]) # Retorna (tipo, string_literal_com_aspas)

# ComandoSaida -> ESCREVA TipoSaida
def p_ComandoSaida(p):
    'ComandoSaida : ESCREVA TipoSaida'
    kind, val = p[2] # Pega o tipo de saída e o valor/nome
    if kind == 'var':
        var = val
        lineno = p.lineno(2)
        # Checagem Semântica
        if var not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para ESCREVA.")
            return
        xtype = symbols[var]['type'] # Pega o tipo da variável
        # Geração de código C usando printf apropriado
        if xtype == 'INTEIRO':
            p[0] = f'printf("%d\\n", {var});' # %d e quebra de linha
        elif xtype == 'REAL':
            p[0] = f'printf("%f\\n", {var});' # %f e quebra de linha
        elif xtype == 'TEXTO':
            p[0] = f'printf("%s\\n", {var});' # %s e quebra de linha
        elif xtype == 'LOGICO':
            p[0] = f'printf("%d\\n", {var});' # %d e quebra de linha
        else:
            semantic_errors.append(f"Erro semântico: tipo desconhecido para ESCREVA '{var}'.")
    else:
        # Geração de código C para string literal
        text = val  # mantém as aspas
        # O compilador C concatena "texto" "\n"
        p[0] = f'printf({text} "\\n");' # Imprime a string literal seguida de nova linha

# Função auxiliar para indentação (não usada diretamente no parser, mas útil para visualizar blocos)
def indent(lines, spaces=4):
    return "\n".join(" " * spaces + line for line in lines)

# ComandoCondicao -> SE ExpressaoRelacional ENTAO ListaComandos ContraCondicao
def p_ComandoCondicao(p):
    'ComandoCondicao : SE ExpressaoRelacional ENTAO ListaComandos ContraCondicao FIM'
    expr_code, expr_type = p[2] # Condição C (ex: (a > b))
    # Os comandos do bloco 'if' precisam ser indentados
    comando_if = "\n".join(" " * 4 + line for line in p[4])
    contra = p[5]             # Código C do 'else { ... }' ou string vazia

    # Monta a estrutura de controle 'if' em C
    codigo = f"if ({expr_code}) {{\n{comando_if}\n}}"
    if contra != '':
        codigo += f"\n{contra}" # Adiciona o bloco 'else' se existir

    p[0] = codigo # Retorna o bloco C completo

# ContraCondicao -> SENAO Comando | empty
def p_ContraCondicao_senao(p):
    'ContraCondicao : SENAO ListaComandos'
    # Os comandos do bloco 'else' precisam ser indentados
    comando_else = "\n".join(" " * 4 + line for line in p[2])
    # Monta o bloco 'else' em C
    p[0] = f'else {{\n{comando_else}\n}}'

def p_ContraCondicao_empty(p):
    'ContraCondicao : '
    p[0] = '' # Retorna string vazia se não houver 'SENAO'


# ComandoRepeticao -> ENQUANTO ExpressaoRelacional ListaComandos FIM
def p_ComandoRepeticao(p):
    'ComandoRepeticao : ENQUANTO ExpressaoRelacional ListaComandos FIM'
    expr_code, expr_type = p[2] # Condição C (ex: (i < 10))

    # Os comandos do bloco 'while' precisam ser indentados
    cmd_code = "\n".join(" " * 4 + line for line in p[3])

    # Monta a estrutura de repetição 'while' em C
    code = f"while ({expr_code}) {{\n{cmd_code}\n}}"
    p[0] = code

# SubAlgoritmo -> INICIO ListaComandos FIM (Bloco genérico)
def p_SubAlgoritmo(p):
    'SubAlgoritmo : INICIO ListaComandos FIM'
    # Esta regra permite agrupar comandos em um bloco (escopo) delimitado por chaves em C.
    cmds = p[2]  # Lista de comandos já com a indentação interna (feita em ListaComandos)
    # Abre e fecha chaves para o bloco em C
    p[0] = "{\n" + "\n".join(" " * 4 + cmd for cmd in cmds) + "\n}"
# ------------------------------
# EXPRESSÕES ARITMÉTICAS E RELACIONAIS
# As regras de expressão usam um retorno de tupla: (c_code, tipo_xulang)
# ------------------------------

# ExpressaoAritmetica -> TermoAritmetico SentencaAritmetica
def p_ExpressaoAritmetica(p):
    'ExpressaoAritmetica : TermoAritmetico SentencaAritmetica'
    left_code, left_type = p[1] # Código C e Tipo do Termo inicial
    if p[2] == '':
        p[0] = (left_code, left_type) # Se não houver mais (+/-) o resultado é o próprio Termo
    else:
        expr_code = left_code + p[2] # Concatena o Termo com o restante da Sentenca (+Termo...)
        # Heurística simples para o tipo resultante. Simplificada aqui.
        res_type = left_type if left_type is not None else 'INTEIRO'
        p[0] = (expr_code, res_type)

# SentencaAritmetica -> + Termo Sentenca | - Termo Sentenca | epsilon (Recursão para +/-)
def p_SentencaAritmetica_plus(p):
    'SentencaAritmetica : \'+\' TermoAritmetico SentencaAritmetica'
    right_code, right_type = p[2]
    suffix = f' + {right_code}' # Adiciona o operador e o código do Termo
    if p[3]:
        suffix = suffix + p[3] # Continua a recursão (+/- Termo...)
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
    p[0] = '' # Fim da sequência de adição/subtração

# TermoAritmetico -> Fator ProposicaoAritmetica
def p_TermoAritmetico(p):
    'TermoAritmetico : FatorAritmetico ProposicaoAritmetica'
    left_code, left_type = p[1] # Código C e Tipo do Fator inicial
    if p[2] == '':
        p[0] = (left_code, left_type) # Se não houver mais (*//) o resultado é o próprio Fator
    else:
        expr_code = left_code + p[2]
        # Regra de tipo: se houver um REAL, o resultado é REAL. Caso contrário, é INTEIRO.
        res_type = 'REAL' if left_type == 'REAL' else 'INTEIRO'
        p[0] = (expr_code, res_type)

# ProposicaoAritmetica -> * Fator Proposicao | / Fator Proposicao | epsilon (Recursão para * /)
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
    p[0] = (str(p[1]), 'INTEIRO') # Retorna o valor como string C e o tipo XuLang

def p_FatorAritmetico_numreal(p):
    'FatorAritmetico : NUMREAL'
    p[0] = (str(p[1]), 'REAL') # Retorna o valor como string C e o tipo XuLang

def p_FatorAritmetico_var(p):
    'FatorAritmetico : NAME'
    var = p[1]
    lineno = p.lineno(1)
    # Checagem Semântica: Variável usada antes de ser declarada
    if var not in symbols:
        semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' usada antes de declaração.")
        p[0] = (var, 'INDEFINIDO')
    else:
        # Retorna o nome da variável como código C e seu tipo da tabela de símbolos
        p[0] = (var, symbols[var]['type'])

def p_FatorAritmetico_group(p):
    'FatorAritmetico : \'(\' ExpressaoAritmetica \')\''
    inner_code, inner_type = p[2]
    # Encapsula o código interno com parênteses em C
    p[0] = (f'({inner_code})', inner_type)

# ------------------------------
# EXPRESSÕES RELACIONAIS / BOOLEANS
# ------------------------------

# ExpressaoRelacional -> TermoRelacional SentencaRelacional
def p_ExpressaoRelacional(p):
    'ExpressaoRelacional : TermoRelacional SentencaRelacional'
    left_code, left_type = p[1]
    if p[2] == '':
        p[0] = (left_code, left_type) # Se não houver 'E' ou 'OU'
    else:
        # Se houver operadores lógicos, o tipo resultante é LOGICO.
        p[0] = (left_code + p[2], 'LOGICO')

# TermoRelacional -> ExpressaoAritmetica OP_REL ExpressaoAritmetica
def p_TermoRelacional_comp(p):
    'TermoRelacional : ExpressaoAritmetica OP_REL ExpressaoAritmetica'
    left_code, left_type = p[1]
    op = p[2]
    right_code, right_type = p[3]
    # Cria a comparação entre parênteses em C
    code = f'({left_code} {op} {right_code})'
    p[0] = (code, 'LOGICO') # O resultado de uma comparação é sempre LOGICO

def p_TermoRelacional_group(p):
    'TermoRelacional : \'(\' ExpressaoRelacional \')\''
    inner_code, inner_type = p[2]
    p[0] = (f'({inner_code})', inner_type)

# SentencaRelacional -> E_BOOL TermoRelacional SentencaRelacional (Tradução de E para &&)
def p_SentencaRelacional_bool(p):
    'SentencaRelacional : E_BOOL TermoRelacional SentencaRelacional'
    right_code, right_type = p[2]
    suffix = f' && {right_code}' # Converte 'E' para o operador lógico C '&&'
    if p[3]:
        suffix += p[3]
    p[0] = suffix

# SentencaRelacional -> OU_BOOL TermoRelacional SentencaRelacional (Tradução de OU para ||)
def p_SentencaRelacional_bool_ou(p):
    'SentencaRelacional : OU_BOOL TermoRelacional SentencaRelacional'
    right_code, right_type = p[2]
    suffix = f' || {right_code}' # Converte 'OU' para o operador lógico C '||'
    if p[3]:
        suffix += p[3]
    p[0] = suffix

def p_SentencaRelacional_empty(p):
    'SentencaRelacional : '
    p[0] = ''

# ------------------------------
# Tratamento de erro sintático (quando a gramática é violada)
# ------------------------------
def p_error(p):
    # Relata o erro e a linha onde o token inesperado foi encontrado.
    if p:
        print(f"Erro sintático: token inesperado '{p.value}' na linha {p.lineno}", file=sys.stderr)
    else:
        print("Erro sintático: fim de arquivo inesperado", file=sys.stderr)

# ------------------------------
# Função principal: leitura do arquivo de entrada e parse
# ------------------------------
def main():
    # Verifica se o nome do arquivo foi passado como argumento
    if len(sys.argv) < 2:
        print("Uso: python xu_compiler.py <arquivo.xu>")
        return
    
    fname = sys.argv[1]
    
    # 1. Definir o nome e o caminho do arquivo de saída
    input_path = Path(fname)
    # Garante que o diretório 'resultado' exista
    output_dir = Path('resultado')
    output_dir.mkdir(exist_ok=True) # Cria a pasta se não existir
    
    # Muda a extensão de .xu para .c
    output_fname = input_path.with_suffix('.c').name
    # Cria o caminho completo para o arquivo de saída
    output_path = output_dir / output_fname

    # Lê todo o conteúdo do arquivo de entrada XuLang
    data = open(fname, 'r', encoding='utf-8').read()
    # Forçar newline final para facilitar comentários e regras baseadas em linhas
    if not data.endswith('\n'):
        data += '\n'
        
    # Constrói o parser
    parser = yacc.yacc()
    # Inicializa a variável para armazenar o código C gerado
    parser.c_output_code = None
    
    # Inicia o processo de parsing (análise léxica e sintática)
    parser.parse(data, lexer=lexer)
    
    # Ao final, reportar erros semânticos (se houver)
    if semantic_errors:
        sys.stderr.write("Erros semânticos detectados:\n")
        for e in semantic_errors:
            sys.stderr.write(e + "\n")
        sys.exit(1) # Sai com código de erro se houver problemas semânticos
    
    # 4. Salvar o código C gerado se o parse foi bem-sucedido
    if parser.c_output_code:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(parser.c_output_code)
            sys.stdout.write(f"Sucesso! Código C gerado e salvo em: {output_path}\n")
        except IOError as e:
            sys.stderr.write(f"Erro ao escrever o arquivo de saída: {e}\n")
            sys.exit(1)
            
if __name__ == '__main__':
    main()
