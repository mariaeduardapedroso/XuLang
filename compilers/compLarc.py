"""
xu_compiler_lark.py
Compilador XuLang -> C usando Lark (substitui versão com PLY).

Como usar:
    python xu_compiler_lark.py entrada.xu > saida.c
    gcc saida.c -o programa
    ./programa

Funcionalidades implementadas:
 - Parser com Lark
 - Transformer que cria AST
 - Tabela de símbolos e checagem semântica (variáveis não declaradas, tipos incompatíveis)
 - Geração de código C (int main() { ... return 0; })
 - Tratamento de strings (TEXTO) com buffers de 256 e strcpy
 - Operadores aritméticos, relacionais e booleanos (E, OU)
 - Mensagens de erro léxico/sintático/semântico com linha

Observação: esta implementação tenta reproduzir o comportamento do compilador PLY original.
"""

from lark import Lark, Transformer, v_args, Token
import sys
import textwrap

# ------------------------------
# GRAMÁTICA Lark
# ------------------------------

xu_grammar = r"""
start: ":" "DECLARACOES" decls ":" "PROGRAMA" commands

?decls: (declaration)*

declaration: NAME ":" type

type: "INTEIRO" | "REAL" | "TEXTO" | "LOGICO"

?commands: (command)*

?command: assignment
        | input
        | output
        | cond
        | loop
        | block

assignment: NAME "<-" expr
input: "LEIA" NAME
output: "ESCREVA" (NAME | STRING)

cond: "SE" expr "ENTAO" commands elsepart? "FIM"
elsepart: "SENAO" commands

loop: "ENQUANTO" expr commands "FIM"

block: "INICIO" commands "FIM"

?expr: logic

?logic: rel (LOGIC_OP rel)*
LOGIC_OP: "E" | "OU"

?rel: arith (REL_OP arith)?
REL_OP: "<=" | ">=" | "==" | "!=" | "<" | ">"

?arith: term (("+"|"-") term)*
?term: factor (("*"|"/") factor)*
?factor: NUMBER    -> number
       | STRING    -> string
       | NAME      -> var
       | "(" expr ")"

%import common.CNAME -> NAME
%import common.ESCAPED_STRING -> STRING
%import common.SIGNED_NUMBER -> NUMBER
%import common.WS
%ignore WS

// Comentários estilo # até fim da linha
COMMENT: /\#[^
]*/
%ignore COMMENT
"""

parser = Lark(xu_grammar, start='start', propagate_positions=True)

# ------------------------------
# ESTRUTURAS PARA CHECAGEM E GERAÇÃO
# ------------------------------

# mapa de tipos XuLang -> C
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

# ------------------------------
# AST Transformer
# ------------------------------

class XuTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.symbols = {}  # name -> {'type': XUTYPE, 'lineno': n}
        self.c_decls = []
        self.semantic_errors = []

    # helpers
    def _get_lineno(self, token_or_tree):
        if isinstance(token_or_tree, Token):
            return token_or_tree.line
        # fallback
        return 0

    def start(self, items):
        # items: : DECLARACOES decls : PROGRAMA commands
        # decls is list of declarations already processed
        # commands is a list of C code lines
        decls, commands = items[2], items[5]
        return {'decls': decls, 'commands': commands, 'symbols': self.symbols, 'errors': self.semantic_errors}

    def declaration(self, items):
        name_tok = items[0]
        typename = items[2].value if isinstance(items[2], Token) else str(items[2])
        name = str(name_tok)
        lineno = self._get_lineno(name_tok)
        if name in self.symbols:
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' já declarada.")
            return ''
        self.symbols[name] = {'type': typename, 'lineno': lineno}
        decl = c_decl_for(name, typename)
        self.c_decls.append(decl)
        return decl

    def type(self, items):
        return items[0]

    # commands: list
    def commands(self, items):
        # cada item é um trecho de código (string) ou list of lines
        out = []
        for it in items:
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out

    # assignment: NAME "<-" expr
    def assignment(self, items):
        name_tok = items[0]
        expr = items[2]
        name = str(name_tok)
        lineno = self._get_lineno(name_tok)
        if name not in self.symbols:
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' não declarada.")
            target_type = None
        else:
            target_type = self.symbols[name]['type']
        expr_code, expr_type = expr
        if target_type is None:
            return f'/* atribuição inválida para {name} */'
        # checagem de compatibilidade
        ok = self.check_assignment(target_type, expr_type, lineno)
        if not ok:
            # já reportado em check_assignment
            pass
        # gerar código
        if target_type == 'TEXTO':
            if expr_type == 'TEXTO':
                return f'strcpy({name}, {expr_code});'
            else:
                self.semantic_errors.append(f"Erro semântico (linha {lineno}): não é possível atribuir tipo {expr_type} a TEXTO.")
                return f'/* incompatível {name} <- {expr_code} */'
        else:
            return f'{name} = {expr_code};'

    # input: LEIA NAME
    def input(self, items):
        name_tok = items[1]
        name = str(name_tok)
        lineno = self._get_lineno(name_tok)
        if name not in self.symbols:
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' não declarada para LEIA.")
            return f'/* LEIA {name} erro */'
        xtype = self.symbols[name]['type']
        if xtype == 'INTEIRO':
            return f'scanf("%d", &{name});'
        elif xtype == 'REAL':
            return f'scanf("%lf", &{name});'
        elif xtype == 'TEXTO':
            return f'scanf("%255s", {name});'
        elif xtype == 'LOGICO':
            return f'scanf("%d", &{name});'
        else:
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): tipo desconhecido em LEIA para '{name}'.")
            return f'/* LEIA {name} tipo desconhecido */'

    # output: ESCREVA (NAME | STRING)
    def output(self, items):
        what = items[1]
        if isinstance(what, Token) and what.type == 'STRING':
            txt = what
            return f'printf({txt} "\n");'
        else:
            name_tok = what
            name = str(name_tok)
            lineno = self._get_lineno(name_tok)
            if name not in self.symbols:
                self.semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' não declarada para ESCREVA.")
                return f'/* ESCREVA {name} erro */'
            xtype = self.symbols[name]['type']
            if xtype == 'INTEIRO':
                return f'printf("%d\n", {name});'
            elif xtype == 'REAL':
                return f'printf("%f\n", {name});'
            elif xtype == 'TEXTO':
                return f'printf("%s\n", {name});'
            elif xtype == 'LOGICO':
                return f'printf("%d\n", {name});'
            else:
                self.semantic_errors.append(f"Erro semântico: tipo desconhecido para ESCREVA '{name}'.")
                return f'/* ESCREVA {name} tipo desconhecido */'

    # cond: SE expr ENTAO commands elsepart? FIM
    def cond(self, items):
        expr = items[1]
        cmds = items[3]
        elsepart = None
        if len(items) == 6:
            elsepart = items[4]
        expr_code, expr_type = expr
        # em C, expressão booleana já é aceitável
        body = ''.join(['    ' + line for line in cmds])
        code = f'if ({expr_code}) {{{body}}}'
        if elsepart:
            else_cmds = elsepart
            else_body = ''.join(['    ' + line for line in else_cmds])
            code += f' else {{{else_body}}}'
        return code

    def elsepart(self, items):
        return items[1]

    # loop: ENQUANTO expr commands FIM
    def loop(self, items):
        expr = items[1]
        cmds = items[2]
        expr_code, expr_type = expr
        body = ''.join(['    ' + line for line in cmds])
        return f'while ({expr_code}) {{{body}}}'

    # block: INICIO commands FIM
    def block(self, items):
        cmds = items[1]
        body = ''.join(cmds)
        return ['{'] + ['    ' + line for line in cmds] + ['}']

    # EXPRESSÕES
    def number(self, items):
        token = items[0]
        txt = str(token)
        if '.' in txt:
            return (txt, 'REAL')
        else:
            return (txt, 'INTEIRO')

    def string(self, items):
        token = items[0]
        # token is quoted (e.g. "hello") - keep as-is
        return (str(token), 'TEXTO')

    def var(self, items):
        token = items[0]
        name = str(token)
        lineno = self._get_lineno(token)
        if name not in self.symbols:
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): variável '{name}' usada antes de declaração.")
            return (name, 'INDEFINIDO')
        return (name, self.symbols[name]['type'])

    def rel(self, items):
        # arith (REL_OP arith)?
        left = items[0]
        if len(items) == 1:
            return left
        op = items[1].value
        right = items[2]
        code = f'({left[0]} {op} {right[0]})'
        return (code, 'LOGICO')

    def logic(self, items):
        # rel (LOGIC_OP rel)*
        left = items[0]
        code = left[0]
        typ = left[1]
        i = 1
        while i < len(items):
            op = items[i].value
            right = items[i+1]
            if op == 'E':
                code = f'({code} && {right[0]})'
            else:
                code = f'({code} || {right[0]})'
            typ = 'LOGICO'
            i += 2
        return (code, typ)

    def arith(self, items):
        # term ((+|-) term)* -> items include operators as tokens in between
        # Lark returns flattened list: term, op, term, op, term...
        code = items[0][0]
        typ = items[0][1]
        i = 1
        while i < len(items):
            op = items[i].value
            right = items[i+1]
            code = f'({code} {op} {right[0]})'
            # determine resulting type: if any REAL involved -> REAL
            if typ == 'REAL' or right[1] == 'REAL':
                typ = 'REAL'
            else:
                typ = 'INTEIRO'
            i += 2
        return (code, typ)

    def term(self, items):
        # similar to arith
        code = items[0][0]
        typ = items[0][1]
        i = 1
        while i < len(items):
            op = items[i].value
            right = items[i+1]
            code = f'({code} {op} {right[0]})'
            if typ == 'REAL' or right[1] == 'REAL':
                typ = 'REAL'
            else:
                typ = 'INTEIRO'
            i += 2
        return (code, typ)

    # checagem de compatibilidade de atribuição
    def check_assignment(self, target_type, expr_type, lineno):
        if target_type == expr_type:
            return True
        if target_type == 'REAL' and expr_type == 'INTEIRO':
            return True
        if target_type == 'INTEIRO' and expr_type == 'REAL':
            self.semantic_errors.append(f"Erro semântico (linha {lineno}): atribuição de REAL para INTEIRO pode perder precisão.")
            return False
        if target_type == 'TEXTO' and expr_type == 'TEXTO':
            return True
        if target_type == 'LOGICO' and expr_type in ('LOGICO','INTEIRO'):
            return True
        self.semantic_errors.append(f"Erro semântico (linha {lineno}): tipo incompatível na atribuição ({target_type} <- {expr_type}).")
        return False

# ------------------------------
# Função principal: parse, checar e gerar C
# ------------------------------

def generate_c(result):
    c_out = []
    c_out.append('/* Código gerado automaticamente por xu_compiler_lark.py */')
    c_out.append('#include <stdio.h>')
    c_out.append('#include <stdlib.h>')
    c_out.append('#include <string.h>')
    c_out.append('')
    c_out.append('int main() {')
    if result['decls']:
        c_out.append('    /* Declarações */')
        for d in result['decls']:
            c_out.append('    ' + d)
        c_out.append('')
    c_out.append('    /* Programa */')
    for line in result['commands']:
        c_out.append('    ' + line)
    c_out.append('')
    c_out.append('    return 0;')
    c_out.append('}')
    return ''.join(c_out)


def main():
    if len(sys.argv) < 2:
        print("Uso: python xu_compiler_lark.py <arquivo.xu>")
        return
    fname = sys.argv[1]
    data = open(fname, 'r', encoding='utf-8').read()
    if not data.endswith(''):
        data += ''
    try:
        tree = parser.parse(data)
    except Exception as e:
        print(f"Erro sintático: {e}", file=sys.stderr)
        sys.exit(1)
    transformer = XuTransformer()
    result = transformer.transform(tree)
    # result: dict with decls, commands, symbols, errors
    if transformer.semantic_errors:
        sys.stderr.write("Erros semânticos detectados:")
        for e in transformer.semantic_errors:
            sys.stderr.write(e + "")
        sys.exit(1)
    # gerar C
    c_code = generate_c(result)
    print(c_code)

if __name__ == '__main__':
    main()
