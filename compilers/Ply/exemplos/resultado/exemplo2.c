/* Código gerado automaticamente por xu_compiler.py */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    /* Declarações */
    char nome[256];
    char nome2[256];
    int idade;

    /* Programa */
    //teste de comentário
    if ((idade >= 18)) {
    printf("Maior de idade" "\n");
    printf("Maior de idade" "\n");
}
else {
    printf("Menor de idade" "\n");
}
    fgets(nome, 256, stdin);
    nome[strcspn(nome, "\n")] = 0;
    scanf("%d", &idade);
    printf("%s\n", nome2);
    printf("Oi" "\n");

    return 0;
}