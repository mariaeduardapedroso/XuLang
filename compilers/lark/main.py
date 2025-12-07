import sys
from lexer_xu import lexer, tokens
from parser_xu import parser
from semantic_xu import report_semantic_errors_and_exit
from codegen_xu import generate_c_program

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py arquivo.xu")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, "r", encoding="utf-8") as f:
        code = f.read()

    print("🔍 Fazendo análise sintática...")
    parser.parse(code, lexer=lexer)

    print("🔍 Verificando erros semânticos...")
    report_semantic_errors_and_exit()

    print("✨ Compilação concluída com sucesso!")

if __name__ == '__main__':
    main()
