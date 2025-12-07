// backend/server.js
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFile, spawn } = require('child_process');
const crypto = require('crypto');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

const PORT = process.env.PORT || 3000;

// Create a temporary working directory
function tmpDir() {
  const id = crypto.randomBytes(6).toString('hex');
  const dir = path.join(os.tmpdir(), 'xu_' + id);
  fs.mkdirSync(dir, { recursive: true });
  console.log('[tmpDir] criado:', dir);
  return dir;
}

// execFile wrapper returning a promise
function execCmd(cmd, args, opts = {}) {
  console.log('[execCmd] cmd:', cmd, 'args:', args, 'cwd:', opts && opts.cwd ? opts.cwd : process.cwd());
  return new Promise((resolve, reject) => {
    execFile(cmd, args, opts, (error, stdout, stderr) => {
      console.log(`[execCmd] finished cmd=${cmd} args=${JSON.stringify(args)} cwd=${opts && opts.cwd ? opts.cwd : ''}`);
      console.log('[execCmd] stdout length:', stdout ? stdout.length : 0);
      console.log('[execCmd] stderr length:', stderr ? stderr.length : 0);
      if (error) {
        // attach stdout/stderr for caller diagnostics
        error.stdout = stdout;
        error.stderr = stderr;
        return reject(error);
      }
      resolve({ stdout, stderr });
    });
  });
}

// spawn runner that writes stdin and returns stdout/stderr/exit info
function runProgramWithStdin(programPath, inputString = '', opts = {}) {
  const cwd = opts.cwd || process.cwd();
  const timeoutMs = typeof opts.timeoutMs === 'number' ? opts.timeoutMs : 5000;

  return new Promise((resolve) => {
    console.log('[runProgram] spawning', programPath, 'cwd:', cwd, 'timeoutMs:', timeoutMs);
    const child = spawn(programPath, [], { cwd, stdio: ['pipe', 'pipe', 'pipe'] });

    let stdout = '';
    let stderr = '';
    let exited = false;

    child.stdout.on('data', d => { stdout += d.toString(); });
    child.stderr.on('data', d => { stderr += d.toString(); });

    child.on('error', (err) => {
      if (exited) return;
      exited = true;
      clearTimeout(killer);
      resolve({ error: String(err), stdout, stderr, code: null, signal: null });
    });

    child.on('exit', (code, signal) => {
      if (exited) return;
      exited = true;
      clearTimeout(killer);
      resolve({ stdout, stderr, code, signal });
    });

    // write inputString (may be empty) and end stdin -> sends EOF
    try {
      if (inputString && inputString.length) {
        child.stdin.write(inputString);
      }
    } catch (e) {
      console.error('[runProgram] erro escrevendo stdin:', e && e.message ? e.message : e);
    } finally {
      try { child.stdin.end(); } catch (e) {}
    }

    // killer timeout: SIGTERM, then SIGKILL after grace
    const killer = setTimeout(() => {
      if (exited) return;
      console.log('[runProgram] timeout reached. killing process with SIGTERM');
      try { child.kill('SIGTERM'); } catch (e) {}
      setTimeout(() => {
        if (!exited) {
          try { child.kill('SIGKILL'); } catch (e) {}
        }
      }, 2000);
    }, timeoutMs);
  });
}

// Healthcheck
app.get('/', (req, res) => res.send('Xu backend — POST /apicompile'));

// Main compile+run endpoint
app.post('/apicompile', async (req, res) => {
  const payload = req.body;
  if (!payload || !Array.isArray(payload.files) || !payload.entry) {
    return res.status(400).json({ error: 'payload inválido: espere { files: [{name,content}], entry: "file.xu" }' });
  }

  const dir = tmpDir();

  try {
    // write files
    console.log('[apicompile] escrevendo arquivos no dir:', dir, 'numFiles:', payload.files.length);
    for (const f of payload.files) {
      const safeName = path.basename(f.name);
      const fname = path.join(dir, safeName);
      console.log('[apicompile] escrevendo arquivo:', fname);
      fs.writeFileSync(fname, f.content, 'utf8');
    }

    // python command (allow override via env)
    const pythonCmd = process.env.PYTHON || 'python3';
    console.log('[apicompile] pythonCmd:', pythonCmd);

    const xuCompilerPath = path.join(process.cwd(), 'xu_compiler.py');
    console.log('[apicompile] xuCompilerPath:', xuCompilerPath);
    if (!fs.existsSync(xuCompilerPath)) {
      throw new Error('xu_compiler.py não encontrado no diretório do backend');
    }

    const entryPath = path.join(dir, path.basename(payload.entry));
    console.log('[apicompile] entryPath (no temp dir):', entryPath);

    // run xu_compiler.py <entry>
    let compileXu;
    try {
      console.log('[apicompile] executando xu_compiler.py...');
      compileXu = await execCmd(pythonCmd, [xuCompilerPath, entryPath], { cwd: dir, timeout: 15000 });
      console.log('[apicompile] xu_compiler.py retornou. stdout len:', compileXu.stdout ? compileXu.stdout.length : 0, 'stderr len:', compileXu.stderr ? compileXu.stderr.length : 0);
    } catch (e) {
      console.error('[apicompile] erro no compilador xu:', e.message);
      console.error('[apicompile] compilador stdout len:', e.stdout ? e.stdout.length : 0);
      console.error('[apicompile] compilador stderr len:', e.stderr ? e.stderr.length : 0);
      const resultErr = {
        c_code: e.stdout || '',
        errors: (e.stderr || '').split(/\r?\n/).filter(Boolean),
      };
      return res.json(resultErr);
    }

    const result = { c_code: compileXu.stdout || '', errors: [] };

    if (compileXu.stderr && compileXu.stderr.trim()) {
      const lines = compileXu.stderr.split(/\r?\n/).filter(Boolean);
      result.errors.push(...lines);
    }

    if (!compileXu.stdout || compileXu.stdout.trim() === '') {
      console.log('[apicompile] compilador não produziu stdout (nenhum C gerado). Respondendo result.');
      return res.json(result);
    }

    const outC = path.join(dir, 'out.c');
    console.log('[apicompile] escrevendo out.c em:', outC);
    fs.writeFileSync(outC, compileXu.stdout, 'utf8');

    // heuristic: detect whether generated C likely expects stdin
    try {
      const src = compileXu.stdout || '';
      const expectsInput = /scanf\s*\(|fgets\s*\(|getchar\s*\(|read\s*\(|cin\s*<</i.test(src);
      result.expects_input = Boolean(expectsInput);
    } catch (e) {
      result.expects_input = false;
    }

    // compile with gcc
    try {
      console.log('[apicompile] invocando gcc...');
      const gcc = await execCmd('gcc', [outC, '-o', 'program'], { cwd: dir, timeout: 15000 });
      result.compile_stdout = gcc.stdout || '';
      result.compile_stderr = gcc.stderr || '';
      console.log('[apicompile] gcc finalizado. stdout len:', (gcc.stdout || '').length, 'stderr len:', (gcc.stderr || '').length);

      // prepare program path
      const programPath = path.join(dir, process.platform === 'win32' ? 'program.exe' : './program');
      console.log('[apicompile] executando program em:', programPath, 'cwd:', dir);

      // determine stdin: accept payload.stdin (string) or payload.inputs (array)
      let inputString = '';
      if (payload && typeof payload.stdin === 'string') {
        inputString = payload.stdin;
      } else if (payload && Array.isArray(payload.inputs)) {
        if (payload.inputs.length && typeof payload.inputs[0] === 'object' && 'value' in payload.inputs[0]) {
          inputString = payload.inputs.map(i => String(i.value)).join('\n') + (payload.inputs.length ? '\n' : '');
        } else {
          inputString = payload.inputs.map(i => String(i)).join('\n') + (payload.inputs.length ? '\n' : '');
        }
      } else {
        inputString = '';
      }

      // run program
      try {
        const run = await runProgramWithStdin(programPath, inputString, { cwd: dir, timeoutMs: 5000 });
        result.run_stdout = run.stdout || '';
        result.run_stderr = run.stderr || '';
        result.run_code = run.code;
        result.run_signal = run.signal;
        console.log('[apicompile] program finalizado. run_stdout len:', (run.stdout || '').length, 'run_stderr len:', (run.stderr || '').length, 'code:', run.code, 'signal:', run.signal);
      } catch (runErr) {
        console.error('[apicompile] erro ao executar program (unexpected):', runErr && runErr.message ? runErr.message : String(runErr));
        result.run_stdout = (runErr && runErr.stdout) || '';
        result.run_stderr = (runErr && runErr.stderr) || String(runErr);
      }
    } catch (gccErr) {
      console.error('[apicompile] gcc falhou:', gccErr && gccErr.message ? gccErr.message : String(gccErr));
      result.compile_stdout = gccErr.stdout || '';
      result.compile_stderr = gccErr.stderr || String(gccErr);
    }

    console.log('[apicompile] respondendo result. keys:', Object.keys(result));
    res.json(result);
  } catch (err) {
    console.error('[apicompile] erro interno:', err && err.stack ? err.stack : String(err));
    res.status(500).json({ error: String(err) });
  } finally {
    // cleanup directory after short delay to allow clients to fetch results
    console.log('[apicompile] agendando cleanup do dir:', dir);
    setTimeout(() => {
      try {
        fs.rmSync(dir, { recursive: true, force: true });
        console.log('[cleanup] removido dir:', dir);
      } catch (e) {
        console.error('[cleanup] erro ao remover dir:', dir, 'err:', String(e));
      }
    }, 1000);
  }
});

app.listen(PORT, () => console.log(`Backend rodando na porta ${PORT}`));
