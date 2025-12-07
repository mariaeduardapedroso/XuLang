# Xu Semântica Comentado
# Contém a tabela de símbolos, checagens de tipo e helpers

"""
Este documento reúne a análise semântica do compilador:
 - Tabela de símbolos (symbols)
 - Declarações C geradas (c_decls)
 - Erros semânticos (semantic_errors)
 - Funções auxiliares: map_type_to_c, c_decl_for, check_assignment

A finalidade é separar responsabilidades: o parser foca em
sintaxe e delega regras semânticas para este módulo.
"""

# Tabela de símbolos: nome -> {'type': 'INTEIRO'|'REAL'|'TEXTO'|'LOGICO'}
symbols = {}

# Declarações C que serão escritas no início do main()
c_decls = []

# Lista de erros encontrados durante a análise semântica
semantic_errors = []

# Mapear tipos Xu -> tipos C
def map_type_to_c(xutype):
    if xutype == 'INTEIRO': return 'int'
    if xutype == 'REAL': return 'double'
    if xutype == 'TEXTO': return 'char'
    if xutype == 'LOGICO': return 'int'
    return None

# Gerar declaração C apropriada (TEXTO -> char name[256])
def c_decl_for(varname, xutype):
    ctype = map_type_to_c(xutype)
    if ctype == 'char':
        return f'char {varname}[256];'
    return f'{ctype} {varname};'

# Checar compatibilidade de atribuição
# Regras simples:
#  - INTEIRO <- REAL => erro
#  - REAL <- INTEIRO => permitido (promoção)
#  - TEXTO <-> CADEIA permitido somente para TEXTO
#  - LOGICO tratado como int

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
    if target_type == 'LOGICO' and expr_type in ('LOGICO','INTEIRO'):
        return True
    semantic_errors.append(f"Erro semântico (linha {lineno}): tipo incompatível na atribuição ({target_type} <- {expr_type}).")
    return False

# Função utilitária para reportar e abortar quando erros existirem
def report_semantic_errors_and_exit():
    import sys
    if semantic_errors:
        sys.stderr.write("Erros semânticos detectados:\n")
        for e in semantic_errors:
            sys.stderr.write(e + "\n")
        sys.exit(1)
