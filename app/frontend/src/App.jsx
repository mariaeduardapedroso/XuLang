import React, { useState, useRef, useEffect } from 'react';

function sampleXu() {
  return [
    ': DECLARACOES',
    'nome : TEXTO',
    'idade : INTEIRO',
    ': PROGRAMA',
    'ESCREVA "Inicio"',
    'LEIA nome',
    'LEIA idade',
    'ESCREVA nome',
    'ESCREVA idade',
  ].join('\n');
}

export default function App() {
  const [files, setFiles] = useState([{ name: 'program.xu', content: sampleXu() }]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [logs, setLogs] = useState('');
  const [cCode, setCCode] = useState('');
  const [running, setRunning] = useState(false);
  const [inputsState, setInputsState] = useState([]); // [{ name, value }]
  const editorRef = useRef(null);
  const inputsRefs = useRef([]);

  // URL do backend via variável de ambiente
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:3000';

  const activeFile = files[activeIndex];

  // Parseia o conteúdo ativo para encontrar ocorrências de LEIA e criar entradas em ordem
  useEffect(() => {
    if (!activeFile) return;
    const lines = activeFile.content.split(/\r?\n/);
    const reads = [];

    for (const ln of lines) {
      const m = ln.match(/^\s*LEIA\s+(.+)$/i);
      if (m) {
        const vars = m[1].split(/[,]\s*|\s+/).map(s => s.trim()).filter(Boolean);
        for (const v of vars) {
          reads.push(v);
        }
      }
    }

    // somente atualiza o estado se mudou realmente (evita reset que quebra foco)
    setInputsState(prev => {
      const sameLength = prev.length === reads.length;
      const sameNames = sameLength && prev.every((p, i) => p.name === reads[i]);
      if (sameNames) return prev; // nada mudou, preserva referência (mantém foco)

      const next = reads.map((name, i) => ({ name: name || `input${i + 1}`, value: prev[i] ? prev[i].value : '' }));
      return next;
    });
  }, [activeFile.content, activeIndex]);

  function updateActiveContent(newContent) {
    setFiles(prev => {
      const copy = prev.slice();
      copy[activeIndex] = { ...copy[activeIndex], content: newContent };
      return copy;
    });
  }

  function addFile() {
    setFiles(prev => {
      const name = `file${prev.length + 1}.xu`;
      const next = [...prev, { name, content: 'novo arquivo .xu' }];
      setActiveIndex(next.length - 1);
      return next;
    });
  }

  function removeFile(idx) {
    setFiles(prev => {
      if (prev.length === 1) return prev;
      const next = prev.filter((_, i) => i !== idx);
      setActiveIndex(prevIndex => {
        if (idx < prevIndex) return prevIndex - 1;
        if (idx === prevIndex) return Math.max(0, prevIndex - 1);
        return prevIndex;
      });
      return next;
    });
  }

  function setInputValueAt(index, value) {
    setInputsState(prev => {
      const copy = prev.slice();
      copy[index] = { ...copy[index], value };
      return copy;
    });
  }

  async function compileAndRun() {
    setRunning(true);
    setLogs('');
    setCCode('');

    // monta inputs array em ordem
    const inputsArray = inputsState.map(i => (i && i.value != null ? String(i.value) : ''));

    const payload = {
      files,
      entry: files[activeIndex].name,
      inputs: inputsArray // enviamos array simples (o backend aceita também stdin string)
    };

    try {
      const resp = await fetch(`${backendUrl}/apicompile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();

      if (data.c_code) setCCode(data.c_code);

      let out = '';
      if (data.errors && data.errors.length) {
        out += '=== ERROS (semânticos / léxicos / sintáticos) ===\n';
        out += data.errors.join('\n') + '\n\n';
      }
      if (data.compile_stderr) out += '=== GCC STDERR ===\n' + data.compile_stderr + '\n\n';
      if (data.compile_stdout) out += '=== GCC STDOUT ===\n' + data.compile_stdout + '\n\n';
      if (data.run_stdout) out += '=== PROGRAMA (stdout) ===\n' + data.run_stdout + '\n\n';
      if (data.run_stderr) out += '=== PROGRAMA (stderr) ===\n' + data.run_stderr + '\n\n';

      // if (data.expects_input) {
      //   out += '=== AVISO ===\nO código gerado parece esperar entrada (LEIA). ';
      //   if (!inputsArray || inputsArray.length === 0) {
      //     out += 'Nenhum valor foi enviado — o backend enviou EOF automaticamente.\n\n';
      //   } else {
      //     out += `Foram enviados ${inputsArray.length} valores (na ordem de aparição de LEIA).\n\n`;
      //   }
      // }

      if (!out) out = 'Sem saída (vazio).';
      setLogs(out);
    } catch (err) {
      setLogs('Erro de comunicação com backend: ' + String(err));
    } finally {
      setRunning(false);
    }
  }

// substitua a função InputsPanel atual por esta versão
function InputsPanel() {
  // refs para inputs não controlados
  const inputEls = useRef([]);

  if (!inputsState || inputsState.length === 0) {
    return <div style={{ color: '#6b7280', fontSize: 13 }}>Sem LEIA detectado no código — nenhum input necessário.</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontWeight: 600 }}>Entradas aguardadas (LEIA)</div>
      {inputsState.map((it, idx) => (
        <div key={idx} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ minWidth: 120, fontFamily: 'monospace', fontSize: 13 }}>{it.name || `input${idx+1}`}</div>

          <input
            // usamos defaultValue para tornar o input não-controlado (evita perder cursor durante re-renders)
            defaultValue={it.value}
            ref={el => inputEls.current[idx] = el}
            placeholder="valor..."
            style={{ flex: 1, padding: '8px 10px', borderRadius: 6, border: '1px solid #e5e7eb', fontFamily: 'monospace' }}
            onBlur={(e) => {
              // quando o usuário sair do campo, salvamos o valor no estado controlado
              setInputValueAt(idx, e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                // salvar imediatamente e focar próximo input (se existir)
                setInputValueAt(idx, e.target.value);
                const next = inputEls.current[idx + 1];
                if (next) next.focus();
                e.preventDefault();
              }
            }}
          />
        </div>
      ))}
    </div>
  );
}

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <aside style={{ width: 320, padding: 12, background: '#0f172a', color: '#f3f4f6', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 18, fontWeight: 600 }}>Xu Explorer</div>
          <button onClick={addFile} style={{ padding: '6px 10px', borderRadius: 6, background: '#10b981', color: 'white' }}>+ arquivo</button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {files.map((f, i) => (
            <div
              key={f.name + i}
              onClick={() => setActiveIndex(i)}
              style={{
                padding: 8,
                borderRadius: 6,
                marginBottom: 6,
                cursor: 'pointer',
                background: i === activeIndex ? '#1f2937' : 'transparent'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</div>
                <button
                  title="remover"
                  onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                  style={{ fontSize: 12, padding: '2px 6px' }}
                >
                  ✖
                </button>
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>{activeFile.name}</div>
          <button onClick={compileAndRun} disabled={running} style={{ width: '100%', padding: '10px', borderRadius: 8, background: '#2563eb', color: 'white', opacity: running ? 0.7 : 1 }}>
            {running ? 'Compilando...' : 'Compilar e Executar'}
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', flex: 1 }}>
          <section style={{ flex: 1, padding: 12 }}>
            <div style={{ height: '100%', background: 'white', borderRadius: 8, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: 12, borderBottom: '1px solid #e5e7eb' }}>{activeFile.name}</div>
              <textarea
                ref={editorRef}
                value={activeFile.content}
                onChange={(e) => updateActiveContent(e.target.value)}
                style={{ flex: 1, padding: 12, fontFamily: 'monospace', fontSize: 13, border: 'none', outline: 'none', resize: 'none' }}
              />
            </div>
          </section>

          <aside style={{ width: 420, padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ flex: 1, background: '#000', color: '#bbf7d0', padding: 12, borderRadius: 8, overflow: 'auto', fontFamily: 'monospace' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Logs & Erros</div>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{logs}</pre>
            </div>

            <div style={{ height: 240, background: '#f8fafc', color: '#111827', padding: 12, borderRadius: 8, overflow: 'auto', fontFamily: 'monospace' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>C gerado</div>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{cCode}</pre>
            </div>
          </aside>
        </div>

        <footer style={{ height: 140, display: 'flex', alignItems: 'flex-start', padding: 12, background: '#f3f4f6', fontSize: 13, gap: 12 }}>
          <div style={{ width: 360, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontWeight: 600 }}>Entradas detectadas</div>
            <div style={{ background: '#fff', padding: 12, borderRadius: 8 }}>
              <InputsPanel />
            </div>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontWeight: 600 }}>Ações</div>
            <div style={{ color: '#6b7280' }}>
              Dica: preencha as caixas de "Entradas" e clique em <strong>Compilar e Executar</strong>. O frontend monta `inputs` na ordem de aparição de LEIA e o backend envia esses valores como stdin para o programa.
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
