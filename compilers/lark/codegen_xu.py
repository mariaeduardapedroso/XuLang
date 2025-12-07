# Xu Geração de Código (Codegen) Comentado
# Responsável por transformar as estruturas geradas pelo parser
# em código C final. Mantém helpers relacionados à formatação.

"""
Este módulo contém utilitários e exemplos para a geração de código C.
Em nosso design, o parser retorna pedaços de código (strings) para
cada comando. O codegen junta essas strings e monta o arquivo C.

Responsabilidades:
 - montar includes e main()
 - juntar declarações (c_decls) vindas do módulo de semântica
 - juntar o corpo (lista de comandos gerada pelo parser)
 - fornecer helpers para melhorar legibilidade
"""


def generate_c_program(commands):
    """Gera o texto completo do programa C a partir de uma lista de
    comandos (strings). Assume que c_decls está presente em xu_semantic_comentado."""
    try:
        from xu_semantic_comentado import c_decls
    except Exception:
        c_decls = []

    out = []
    out.append('/* Código gerado automaticamente por Xu */')
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
    for c in commands:
        out.append('    ' + c)

    out.append('')
    out.append('    return 0;')
    out.append('}')
    return '\n'.join(out)

# Exemplo de uso (não executado automaticamente)
if __name__ == '__main__':
    example_cmds = [
        'int x = 10;',
        'printf("%d\\n", x);'
    ]
    print(generate_c_program(example_cmds))
