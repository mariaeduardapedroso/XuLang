"""xu_compiler_lark.py

Versão do compilador XuLang -> C usando Lark (grammar + Transformer).
Funcionalidades aproximam-se do original em PLY:
 - lexer/grammar em Lark
 - tabela de símbolos e checagem semântica
 - geração de código C (int main() { ... return 0; })
 - comentários convertidos para // em C
 - conversões de tipo semelhantes (INTEIRO, REAL, TEXTO, LOGICO)

Uso:
    python xu_compiler_lark.py entrada.xu > saida.c
    gcc saida.c -o programa
    ./programa

Observação: requer a biblioteca `lark-parser` (instale com `pip install lark-parser`).
"""

from lark import Lark, Transformer, v_args, Token, Tree
import sys

# ------------------------------
# Gramática Lark
# ------------------------------
grammar = r"""
start: PC "DECLARACOES" decl_list PC "PROGRAMA" stmt_list

decl_list: decl+
decl: NAME PC tipo

tipo: "INTEIRO" | "REAL" | "TEXTO" | "LOGICO"

stmt_list: stmt*

stmt: assignment
    | read
    | write
    | if_stmt
    | while_stmt
    | block
    | comment

assignment: NAME ATRIB arith_expr
read: "LEIA" NAME
write: "ESCREVA" (NAME | CADEIA)

if_stmt: "SE" rel_expr "ENTAO" stmt_list else_part "FIM"
else_part: "SENAO" stmt | -> empty_else

while_stmt: "ENQUANTO" rel_expr stmt_list "FIM"

block: "INICIO" stmt_list "FIM"

comment: COMMENT

?arith_expr: term (("+"|"-") term)*
?term: factor (("*"|"/") factor)*
?factor: NUMREAL -> numreal
       | NUMINT  -> numint
       | NAME    -> var
       | "(" arith_expr ")"

?rel_expr: rel_term (bool_op rel_term)*
rel_term: arith_expr OP_REL -> compare

bool_op: "E" -> and_op
       | "OU" -> or_op


PC: ":"
ATRIB: "<-"
OP_REL: "<="|">="|"=="|"!="|"<"|">"

%import common.CNAME -> NAME
NUMREAL: /\d+\.\d+/
NUMINT: /\d+/
CADEIA: /"([^\\\n]|(\\.))*?"/
COMMENT: /\#[^\n]*/

%import common.WS_INLINE
%ignore WS_INLINE
%ignore /\r?\n/
"""

# ------------------------------
# Estruturas auxiliares (símbolos, decls, erros)
# ------------------------------
symbols = {}
semantic_errors = []
c_decls = []

def map_type_to_c(xutype):
    if xutype == 'INTEIRO':
        return 'int'
    if xutype == 'REAL':
        return 'double'
    if xutype == 'TEXTO':
        return 'char'
    if xutype == 'LOGICO':
        return 'int'
    return None

def c_decl_for(varname, xutype):
    ctype = map_type_to_c(xutype)
    if ctype == 'char':
        return f'char {varname}[256];'
    else:
        return f'{ctype} {varname};'

def check_assignment(target_type, expr_type, lineno):
    if target_type == expr_type:
        return True
    if target_type == 'REAL' and expr_type == 'INTEIRO':
        return True
    if target_type == 'INTEIRO' and expr_type == 'REAL':
        semantic_errors.append(f"Erro semântico (linha {lineno}): atribuição de REAL para INTEIRO pode perder precisão.")
        return False
    if target_type == 'TEXTO' and expr_type == 'TEXTO':
        return True
    if target_type == 'LOGICO' and expr_type in ('LOGICO', 'INTEIRO'):
        return True
    semantic_errors.append(f"Erro semântico (linha {lineno}): tipo incompatível na atribuição ({target_type} <- {expr_type}).")
    return False

# ------------------------------
# Transformer: constrói código C e faz checagens
# ------------------------------
from lark import Transformer, Token, Tree, v_args

# ------------------------------
# Transformer: constrói código C e faz checagens
# ------------------------------
class XuTransformer(Transformer):
    def __init__(self):
        super().__init__()

    # --------------------------
    # Declarações
    # --------------------------
    def decl_list(self, children):
        # children são as declarações em C já geradas
        return list(children)

    def decl(self, children):
        name, _pc, tipo_node = children
        varname = str(name)
        xtype = str(tipo_node)
        lineno = name.line if isinstance(name, Token) else 0
        if varname in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{varname}' já declarada.")
            decl = c_decl_for(varname, xtype)
        else:
            symbols[varname] = {'type': xtype}
            decl = c_decl_for(varname, xtype)
            c_decls.append(decl)
        return decl

    def tipo(self, children):
        if children:  # se houver child
            token = children[0]
            return token.value
        # caso não haja child, pegar o token diretamente do tree.data
        return str(self.__current_token.value)  # ou apenas "INDEFINIDO"



    # --------------------------
    # Statements
    # --------------------------
    def stmt_list(self, children):
        result = []
        for s in children:
            if isinstance(s, list):
                result.extend(s)
            elif s is None:
                continue
            else:
                result.append(str(s))
        return result

    def assignment(self, children):
        name, _atrib, expr = children
        var = str(name)
        lineno = name.line if isinstance(name, Token) else 0
        expr_code, expr_type = expr
        if var not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada.")
            target_type = None
        else:
            target_type = symbols[var]['type']
        if target_type:
            ok = check_assignment(target_type, expr_type, lineno)
            if target_type == 'TEXTO':
                if expr_type == 'TEXTO':
                    code = f'strcpy({var}, {expr_code});'
                else:
                    semantic_errors.append(f"Erro semântico (linha {lineno}): não é possível atribuir tipo {expr_type} a TEXTO.")
                    code = f'/* atribuição inválida */'
            else:
                code = f'{var} = {expr_code};'
            return code
        else:
            return '/* erro: atribuição */'

    def read(self, children):
        _leia, name = children
        var = str(name)
        lineno = name.line if isinstance(name, Token) else 0
        if var not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para LEIA.")
            return '/* erro LEIA */'
        xtype = symbols[var]['type']
        if xtype == 'INTEIRO':
            return f'scanf("%d", &{var});'
        elif xtype == 'REAL':
            return f'scanf("%lf", &{var});'
        elif xtype == 'TEXTO':
            return f'scanf("%255s", {var});'
        elif xtype == 'LOGICO':
            return f'scanf("%d", &{var});'
        else:
            semantic_errors.append(f"Erro semântico (linha {lineno}): tipo desconhecido em LEIA para '{var}'.")
            return '/* erro LEIA tipo */'

    def write(self, children):
        _escreva, what = children
        if isinstance(what, Token) and what.type == 'CADEIA':
            text = str(what)
            return f'printf({text} "\\n");'
        else:
            var = str(what)
            lineno = what.line if isinstance(what, Token) else 0
            if var not in symbols:
                semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' não declarada para ESCREVA.")
                return '/* erro ESCREVA */'
            xtype = symbols[var]['type']
            if xtype == 'INTEIRO':
                return f'printf("%d\\n", {var});'
            elif xtype == 'REAL':
                return f'printf("%f\\n", {var});'
            elif xtype == 'TEXTO':
                return f'printf("%s\\n", {var});'
            elif xtype == 'LOGICO':
                return f'printf("%d\\n", {var});'
            else:
                semantic_errors.append(f"Erro semântico: tipo desconhecido para ESCREVA '{var}'.")
                return '/* erro ESCREVA tipo */'

    def comment(self, children):
        token = children[0]
        text = str(token)
        c = text[1:].lstrip()
        return f'// {c}'

    # --------------------------
    # If / Else
    # --------------------------
    def if_stmt(self, children):
        _se, rel, _entao, stmts, else_part, _fim = children
        expr_code, expr_type = rel
        body = '\n'.join('    ' + s for s in stmts)
        code = f'if ({expr_code}) {{\n{body}\n}}'
        if else_part:
            code += f'\n{else_part}'
        return code

    def empty_else(self, children=None):
        return ''

    def else_part(self, children):
        _senao, stmt = children
        if isinstance(stmt, list):
            body = '\n'.join('    ' + s for s in stmt)
            return f'else {{\n{body}\n}}'
        else:
            return f'else {{\n    {stmt}\n}}'

    # --------------------------
    # While
    # --------------------------
    def while_stmt(self, children):
        _enquanto, rel, stmts, _fim = children
        expr_code, expr_type = rel
        body = '\n'.join('    ' + s for s in stmts)
        return f'while ({expr_code}) {{\n{body}\n}}'

    # --------------------------
    # Block
    # --------------------------
    def block(self, children):
        _inicio, stmts, _fim = children
        body = '\n'.join('    ' + s for s in stmts)
        return '{\n' + body + '\n}'

    # --------------------------
    # Expressões aritméticas e relacionais
    # --------------------------
    @v_args(inline=True)
    def numint(self, token):
        return (str(token), 'INTEIRO')

    @v_args(inline=True)
    def numreal(self, token):
        return (str(token), 'REAL')

    @v_args(inline=True)
    def var(self, name):
        var = str(name)
        lineno = name.line if isinstance(name, Token) else 0
        if var not in symbols:
            semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{var}' usada antes de declaração.")
            return (var, 'INDEFINIDO')
        return (var, symbols[var]['type'])

    def arith_expr(self, children):
        code, typ = children[0]
        it = iter(children[1:])
        for item in it:
            if isinstance(item, Token):
                op = str(item)
                term_code, term_type = next(it)
                code = f'({code} {op} {term_code})'
                if typ == 'REAL' or term_type == 'REAL':
                    typ = 'REAL'
                else:
                    typ = 'INTEIRO'
        return (code, typ)

    def compare(self, children):
        left, op, right = children
        left_code, left_type = left
        right_code, right_type = right
        op_s = str(op)
        return (f'({left_code} {op_s} {right_code})', 'LOGICO')

    def rel_expr(self, children):
        code, typ = children[0]
        it = iter(children[1:])
        for item in it:
            if isinstance(item, Token):
                op = str(item)
                term_code, term_type = next(it)
                if op == 'E':
                    code = f'({code} && {term_code})'
                else:
                    code = f'({code} || {term_code})'
        return (code, 'LOGICO')

    @v_args(inline=True)
    def and_op(self, *args):
        return Token('BOOL', 'E')

    @v_args(inline=True)
    def or_op(self, *args):
        return Token('BOOL', 'OU')

# ------------------------------
# Montagem do parser e execução
# ------------------------------
parser = Lark(grammar, parser='lalr', lexer='contextual', propagate_positions=True)

def generate_c(stmts):
    out = []
    out.append('/* Código gerado automaticamente por xu_compiler_lark.py */')
    out.append('#include <stdio.h>')
    out.append('#include <stdlib.h>')
    out.append('#include <string.h>')
    out.append('')
    out.append('int main() {')
    if c_decls:
        out.append('    /* Declarações */')
        for d in c_decls:
            out.append('    ' + d)
        out.append('')
    out.append('    /* Programa */')
    for line in stmts:
        out.append('    ' + line)
    out.append('')
    out.append('    return 0;')
    out.append('}')
    return '\n'.join(out)

# ------------------------------
# Função principal
# ------------------------------
def main():
    if len(sys.argv) < 2:
        print('Uso: python xu_compiler_lark.py <arquivo.xu>')
        return

    fname = sys.argv[1]

    # Leitura do arquivo Xu
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        print(f"Erro ao ler o arquivo {fname}: {e}", file=sys.stderr)
        sys.exit(1)

    # Garantir que termina com \n
    if not data.endswith('\n'):
        data += '\n'

    # Criação do parser (assumindo que 'parser' já foi definido com Lark)
    try:
        tree = parser.parse(data)
    except Exception as e:
        print("Erro durante parsing:", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)

    # Criar o transformer
    tx = XuTransformer()

    # Encontrar subtrees de declarações e statements
    decl_list_node = None
    stmt_list_node = None
    for c in tree.children:
        if isinstance(c, Tree) and c.data == 'decl_list':
            decl_list_node = c
        if isinstance(c, Tree) and c.data == 'stmt_list':
            stmt_list_node = c

    # Transformar declarações primeiro para preencher tabela de símbolos e c_decls
    if decl_list_node is not None:
        tx.transform(decl_list_node)

    # Transformar statements
    stmts = []
    if stmt_list_node is not None:
        stmts = tx.transform(stmt_list_node)
    else:
        stmts = []

    # Reportar erros semânticos se existirem
    if semantic_errors:
        sys.stderr.write('Erros semânticos detectados:\n')
        for e in semantic_errors:
            sys.stderr.write(e + '\n')
        sys.exit(1)

    # Gerar código C
    c_code = generate_c(stmts)
    print(c_code)

    if len(sys.argv) < 2:
        print('Uso: python xu_compiler_lark.py <arquivo.xu>')
        return
    fname = sys.argv[1]
    data = open(fname, 'r', encoding='utf-8').read()
    if not data.endswith('\n'):
        data += '\n'
    try:
        tree = parser.parse(data)
        tx = XuTransformer()

        # Encontrar subtrees decl_list e stmt_list (start children contêm tokens e subtrees)
        decl_list_node = None
        stmt_list_node = None
        for c in tree.children:
            if isinstance(c, Tree) and c.data == 'decl_list':
                decl_list_node = c
            if isinstance(c, Tree) and c.data == 'stmt_list':
                stmt_list_node = c

        # Transform declarations first to fill symbol table / c_decls
        if decl_list_node is not None:
            tx.transform(decl_list_node)
        # Transform statements
        stmts = []
        if stmt_list_node is not None:
            stmts = tx.transform(stmt_list_node)
        else:
            stmts = []

        # Report semantic errors if any
        if semantic_errors:
            sys.stderr.write('Erros semânticos detectados:\n')
            for e in semantic_errors:
                sys.stderr.write(e + '\n')
            sys.exit(1)

        # gerar C
        c_code = generate_c(stmts)
        print(c_code)

    except Exception as e:
        print('Erro durante parsing/transformação:', file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
