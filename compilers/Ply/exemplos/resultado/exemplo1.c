/* Código gerado automaticamente por xu_compiler.py */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    /* Declarações */
    char nome[256];
    int idade;

    /* Programa */
    //teste de comentário
    fgets(nome, 256, stdin);
    nome[strcspn(nome, "\n")] = 0;
    scanf("%d", &idade);
    printf("Oi" "\n");

    return 0;
}