import React from 'react';

// XuLangPage.jsx
// Página explicativa sobre a gramática XuLang.
// Instruções de roteamento (exemplo):
// 1) instale react-router-dom se ainda não tiver: npm install react-router-dom
// 2) no seu App root (ou onde configura rotas) adicione:
//    import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
//    import XuLangPage from './XuLangPage';
//    // dentro do BrowserRouter:
//    <Routes>
//      <Route path="/" element={<App />} />
//      <Route path="/xulang" element={<XuLangPage />} />
//    </Routes>
// 3) Ou adicione um Link: <Link to="/xulang">XuLang</Link>

export default function XuLangPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 font-sans">
      <div className="max-w-5xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-extrabold">XuLang: Programação e Lógica Descomplicada em Português</h1>
          <p className="mt-2 text-slate-600">A linguagem de programação criada para ensinar — sintaxe em Português, foco em didática.</p>
        </header>

        <section className="grid gap-6">
          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Por que XuLang?</h2>
            <ul className="list-disc pl-5 mt-3 text-slate-700 space-y-2">
              <li>Problema: barreiras linguísticas e complexidade de sintaxe em linguagens iniciantes.</li>
              <li>Solução XuLang: ambiente 100% em Português com sintaxe mínima e intuitiva.</li>
              <li>Público-alvo: estudantes, iniciantes e qualquer falante de Português.</li>
            </ul>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Arquitetura Simples</h2>
            <p className="mt-3 text-slate-700">XuLang é um compilador source-to-source. Fluxo:</p>
            <pre className="mt-3 p-3 bg-slate-100 rounded font-mono text-sm">{`Código XuLang (.xu) -> Compilador -> Código C (.c) -> Executável`}</pre>
            <p className="mt-3 text-slate-600">Benefício: aproveitar eficiência do C sem que o usuário precise lidar com sua complexidade.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Léxico e Palavras-chave</h2>
            <p className="mt-3 text-slate-700">A XuLang é case-insensitive (usamos maiúsculas por clareza).</p>
            <div className="mt-3 grid grid-cols-2 gap-4 text-slate-700">
              <div>
                <strong>Estrutura</strong>
                <ul className="list-disc pl-5 mt-2">
                  <li>DECLARACOES, PROGRAMA, INICIO, FIM</li>
                </ul>
              </div>
              <div>
                <strong>Controle & E/S</strong>
                <ul className="list-disc pl-5 mt-2">
                  <li>SE, ENTAO, SENAO, ENQUANTO</li>
                  <li>LEIA, ESCREVA</li>
                </ul>
              </div>
            </div>

            <p className="mt-3 text-slate-700">Operadores e símbolos: atribuição &lt;- , lógicos E / OU, delimitador : , etc.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Tipos de Dados</h2>
            <p className="mt-3 text-slate-700">Tipos essenciais para começar:</p>
            <ul className="list-disc pl-5 mt-2 text-slate-700">
              <li><strong>INTEIRO</strong> — números inteiros</li>
              <li><strong>REAL</strong> — números com ponto flutuante</li>
              <li><strong>TEXTO</strong> — strings</li>
              <li><strong>LOGICO</strong> — verdadeiro / falso</li>
            </ul>
            <p className="mt-2 text-slate-600">Nomes (identificadores) devem começar com letra ou _ e podem conter letras, números e _.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Estrutura Principal (Regra de Ouro)</h2>
            <p className="mt-3 text-slate-700">Todo programa XuLang segue a estrutura fixa:</p>
            <pre className="mt-3 p-3 bg-slate-100 rounded font-mono text-sm">{`: DECLARACOES
<ListaDeclaracoes>
: PROGRAMA
<ListaComandos>`}</pre>
            <p className="mt-3 text-slate-700">Declarações: <code>NAME : Tipo</code>. Blocos: <code>INICIO ... FIM</code>.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Comandos Essenciais</h2>
            <ul className="list-disc pl-5 mt-3 text-slate-700 space-y-2">
              <li><strong>Atribuição:</strong> <code>NAME &lt;- ExpressaoAritmetica</code></li>
              <li><strong>Entrada:</strong> <code>LEIA NAME</code></li>
              <li><strong>Saída:</strong> <code>ESCREVA NAME | "cadeia"</code></li>
            </ul>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Estruturas de Controle</h2>
            <p className="mt-3 text-slate-700">Condicional:</p>
            <pre className="mt-2 p-3 bg-slate-100 rounded font-mono text-sm">{`SE <ExpressaoRelacional> ENTAO
  <ListaComandos>
<ContraCondicao>
FIM`}</pre>
            <p className="mt-3 text-slate-700">Repetição:</p>
            <pre className="mt-2 p-3 bg-slate-100 rounded font-mono text-sm">{`ENQUANTO <ExpressaoRelacional>
  <ListaComandos>
FIM`}</pre>
            <p className="mt-3 text-slate-600">Todas as estruturas terminam com <strong>FIM</strong> — menos confusão para iniciantes.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Regras de Expressões</h2>
            <p className="mt-3 text-slate-700">Precedência: multiplicação/divisão &gt; adição/subtração &gt; relacional &gt; E &gt; OU. Parênteses são permitidos.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">O que Não Pode</h2>
            <ul className="list-disc pl-5 mt-3 text-slate-700 space-y-2">
              <li>Variáveis não declaradas.</li>
              <li>Atribuições entre tipos incompatíveis.</li>
              <li>Misturar seções de declaração e programa.</li>
              <li>Programas sem as seções <code>DECLARACOES</code> e <code>PROGRAMA</code>.</li>
            </ul>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Exemplo de Código XuLang</h2>
            <pre className="mt-3 p-3 bg-slate-100 rounded font-mono text-sm text-slate-800">{` : DECLARACOES
nome : TEXTO
idade : INTEIRO
: PROGRAMA
ESCREVA "Inicio"
LEIA nome
LEIA idade
ESCREVA nome
ESCREVA idade`}</pre>
            <p className="mt-3 text-slate-600">Use o compilador Xu para ver a tradução para C ao vivo.</p>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Gramática (BNF)</h2>
            <div className="mt-3 text-slate-700">
              <pre className="p-4 bg-slate-100 rounded font-mono text-sm overflow-auto">{`<Programa> ::= ":" DECLARACOES <ListaDeclaracoes> ":" PROGRAMA <ListaComandos>
<ListaDeclaracoes> ::= <Declaracao> <OutrasDeclaracoes>
<OutrasDeclaracoes> ::= <ListaDeclaracoes> | ε
<Declaracao> ::= NAME ":" <TipoVar>
<TipoVar> ::= INTEIRO | REAL | TEXTO | LOGICO

<ListaComandos> ::= <Comando> <ListaComandos> | ε
<Comando> ::= <ComandoAtribuicao>
  | <ComandoEntrada>
  | <ComandoSaida>
  | <ComandoCondicao>
  | <ComandoRepeticao>
  | <SubAlgoritmo>
  | COMMENT

<ComandoAtribuicao> ::= NAME ATRIB <ExpressaoAritmetica>
<ComandoEntrada> ::= LEIA NAME
<ComandoSaida> ::= ESCREVA <TipoSaida>
<TipoSaida> ::= NAME | CADEIA

<ComandoCondicao> ::= SE <ExpressaoRelacional> ENTAO <ListaComandos> <ContraCondicao> FIM
<ContraCondicao> ::= SENAO <ListaComandos> FIM | ε
<ComandoRepeticao> ::= ENQUANTO <ExpressaoRelacional> <ListaComandos> FIM

<SubAlgoritmo> ::= INICIO <ListaComandos> FIM

<ExpressaoAritmetica> ::= <TermoAritmetico> <SentencaAritmetica>
<SentencaAritmetica> ::= '+' <TermoAritmetico> <SentencaAritmetica>
  | '-' <TermoAritmetico> <SentencaAritmetica> | ε
<TermoAritmetico> ::= <FatorAritmetico> <ProposicaoAritmetica>
<ProposicaoAritmetica> ::= '*' <FatorAritmetico> <ProposicaoAritmetica> | ε
  | '/' <FatorAritmetico> <ProposicaoAritmetica> | ε
<FatorAritmetico> ::= NUMINT | NUMREAL | NAME | '(' <ExpressaoAritmetica> ')'

<ExpressaoRelacional> ::= <TermoRelacional> <SentencaRelacional>
<TermoRelacional> ::= <ExpressaoAritmetica> OP_REL <ExpressaoAritmetica>
  | '(' <ExpressaoRelacional> ')'
<SentencaRelacional> ::= E_BOOL <TermoRelacional> <SentencaRelacional> | ε
  | OU_BOOL <TermoRelacional> <SentencaRelacional> | ε`}</pre>
            </div>
          </article>

          <article className="bg-white p-6 rounded-2xl shadow">
            <h2 className="text-xl font-semibold">Conclusão & CTA</h2>
            <p className="mt-3 text-slate-700">Recapitulação: XuLang facilita a curva de aprendizado — comece a programar em Português hoje mesmo.</p>
            <div className="mt-4">
              <a href="/" className="inline-block px-4 py-2 rounded bg-indigo-600 text-white">Voltar</a>
            </div>
          </article>

          <article className="bg-white p-8 rounded-3xl shadow-lg hover:shadow-2xl transition-shadow duration-300 text-center">
            <h2 className="text-2xl font-semibold text-indigo-600 mb-3">Pronto para Programar?</h2>
            <p className="text-slate-700">Comece agora e explore todos os recursos da XuLang!</p>
            <a href="/" className="inline-block mt-4 px-6 py-3 rounded-full bg-indigo-600 text-white font-semibold shadow-lg hover:bg-indigo-500 transition-colors duration-300">
              Voltar ao Compilador
            </a>
          </article>
        </section>

      </div>
    </div>
  );
}
