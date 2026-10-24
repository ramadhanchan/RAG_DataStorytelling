import {useEffect, useRef, useState} from 'react';
import ReactMarkdown from 'react-markdown';
import {Bar, Line, Pie} from 'react-chartjs-2';
import {ArcElement, BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Title, Tooltip} from 'chart.js';
import {ask, getIngests, templateUrl, uploadCsv} from './api';
import {mapChartSpecToChartJs} from './chartMapper';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Filler, Title, Tooltip, Legend);

const sessionId = crypto.randomUUID();

const SUGGESTIONS = [
  'Genre apa yang paling laris?',
  'Buku terlaris tahun 2005',
  'Penulis dengan penjualan terbesar',
  'Bahasa apa yang paling banyak terjual?',
];

const MODE_LABEL = {
  deepseek: 'DeepSeek',
  keyword: 'Kata kunci',
  vector: 'Semantik',
  generic: 'Ringkasan data',
  'local-fallback': 'Analisis lokal',
  empty: 'Data kosong',
  'no-match': 'Tidak cocok',
  error: 'Galat',
};

const CHART_LABEL = {bar: 'Batang', line: 'Garis', pie: 'Lingkar'};

function ChartMessage({spec}) {
  const [type, setType] = useState(spec.type);
  const config = mapChartSpecToChartJs({...spec, type});
  if (!config) return null;
  const Chart = type === 'bar' ? Bar : type === 'line' ? Line : Pie;
  return (
    <figure className="chart">
      <div className="chart-bar">
        <span className="chart-name">{spec.title || 'Visualisasi data'}</span>
        <div className="chart-tabs" role="tablist" aria-label="Jenis grafik">
          {['bar', 'line', 'pie'].map(option => (
            <button type="button" key={option} role="tab" aria-selected={type === option} className={type === option ? 'active' : ''} onClick={() => setType(option)}>
              {CHART_LABEL[option]}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-canvas"><Chart {...config} /></div>
      {spec.insight && <figcaption>{spec.insight}</figcaption>}
    </figure>
  );
}

function Message({item}) {
  const [copied, setCopied] = useState(false);
  const text = item.content || item.narration || '';
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }
  return (
    <article className={`msg ${item.role}`}>
      <div className="msg-head">
        <span className="avatar" aria-hidden="true">{item.role === 'user' ? 'Anda' : 'AI'}</span>
        {item.mode && <span className={`mode ${item.mode}`}>{MODE_LABEL[item.mode] || item.mode}</span>}
        {item.role === 'assistant' && text && (
          <button type="button" className="ghost copy" onClick={copy} aria-label="Salin jawaban">{copied ? 'Tersalin' : 'Salin'}</button>
        )}
      </div>
      <div className="msg-body"><ReactMarkdown>{text}</ReactMarkdown></div>
      {item.chart && <ChartMessage spec={item.chart} />}
      {item.recommendation && <p className="recommendation">Rekomendasi: {item.recommendation}</p>}
      {item.sources?.length > 0 && (
        <div className="sources" aria-label="Sumber data">
          {item.sources.slice(0, 6).map(source => <span key={source}>{source}</span>)}
          {item.sources.length > 6 && <span>+{item.sources.length - 6} lainnya</span>}
        </div>
      )}
    </article>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [ingests, setIngests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openIngest, setOpenIngest] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('ds-theme') || 'dark');
  const feedRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { getIngests().then(response => setIngests(response.data)).catch(() => {}); }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('ds-theme', theme);
  }, [theme]);
  useEffect(() => {
    const feed = feedRef.current;
    if (feed) feed.scrollTo({top: feed.scrollHeight, behavior: 'smooth'});
  }, [messages, loading]);
  useEffect(() => { inputRef.current?.focus(); }, []);

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setStatus({type: 'error', text: 'Pilih file CSV terlebih dahulu.'});
      return;
    }
    setStatus({type: 'loading', text: `Mengunggah ${file.name}...`});
    try {
      const result = await uploadCsv(file);
      const {successful_rows: ok, failed_rows: failed, status: state} = result.data;
      setStatus({type: failed ? 'warn' : 'ok', text: `${ok} baris masuk, ${failed} baris gagal (${state}).`});
      setIngests((await getIngests()).data);
      setFile(null);
      event.target.reset();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setStatus({type: 'error', text: detail?.message || detail || 'Upload gagal. Coba lagi.'});
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }

  async function send(text) {
    const clean = text.trim();
    if (!clean || loading) return;
    setMessage('');
    setMessages(prev => [...prev, {role: 'user', content: clean}]);
    setLoading(true);
    try {
      const result = await ask(clean, sessionId);
      setMessages(prev => [...prev, {role: 'assistant', ...result.data}]);
    } catch {
      setMessages(prev => [...prev, {role: 'assistant', narration: 'Terjadi kesalahan saat memproses pertanyaan. Coba lagi.', mode: 'error'}]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  const activeRows = ingests[0]?.successful_rows ?? 0;

  return (
    <main>
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span className="dot" />Bookstore Intelligence</p>
          <h1>Cerita di balik <em>angka</em> penjualan.</h1>
          <p className="lede">Unggah data penjualan, lalu tanyakan apa saja. Setiap jawaban datang dengan narasi, grafik interaktif, dan rekomendasi.</p>
        </div>
        <div className="hero-side">
          <button type="button" className="ghost theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? 'Mode terang' : 'Mode gelap'}
          </button>
          <div className="hero-stats">
            <div><strong>{ingests.length}</strong><span>unggahan</span></div>
            <div><strong>{activeRows.toLocaleString('id-ID')}</strong><span>baris data aktif</span></div>
          </div>
        </div>
      </header>

      <section className="panel upload">
        <div className="panel-head">
          <h2>Unggah data</h2>
          <a href={templateUrl} className="link">Unduh template CSV</a>
        </div>
        <form onSubmit={handleUpload}>
          <label
            className={`dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={event => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <input type="file" accept=".csv" onChange={event => setFile(event.target.files[0] || null)} />
            <span className="drop-icon" aria-hidden="true">↑</span>
            <span className="drop-title">{file ? file.name : 'Tarik CSV ke sini atau klik untuk memilih'}</span>
            <span className="drop-hint">judul_buku, penulis, bahasa, tahun, penjualan (juta), genre</span>
          </label>
          <button type="submit" disabled={!file || status?.type === 'loading'}>Upload CSV</button>
        </form>
        {status && <p className={`status ${status.type}`}>{status.text}</p>}
      </section>

      <section className="layout">
        <div className="panel chat">
          <div className="panel-head">
            <h2>Tanya data Anda</h2>
            <span className="live"><span className="pulse" />Sesi aktif</span>
          </div>
          <div className="messages" ref={feedRef}>
            {messages.length === 0 && !loading && (
              <div className="empty">
                <p>Belum ada pertanyaan. Mulai dari salah satu ide ini:</p>
                <div className="chips">
                  {SUGGESTIONS.map(suggestion => (
                    <button type="button" key={suggestion} onClick={() => send(suggestion)}>{suggestion}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((item, index) => <Message key={index} item={item} />)}
            {loading && <article className="msg assistant typing" aria-label="Sedang menganalisis"><span /><span /><span /></article>}
          </div>
          <form className="chat-form" onSubmit={event => { event.preventDefault(); send(message); }}>
            <input
              ref={inputRef}
              value={message}
              onChange={event => setMessage(event.target.value)}
              placeholder="Contoh: Genre apa paling laris?"
              aria-label="Pertanyaan"
            />
            <button type="submit" disabled={loading || !message.trim()}>Tanya</button>
          </form>
        </div>

        <aside className="panel side">
          <div className="panel-head">
            <h2>Riwayat ingest</h2>
          </div>
          {ingests.length === 0 ? (
            <p className="muted">Belum ada data. Unggah CSV pertama Anda untuk memulai.</p>
          ) : (
            <ul className="ingests">
              {ingests.map(item => (
                <li key={item.id}>
                  <button type="button" onClick={() => setOpenIngest(openIngest === item.id ? null : item.id)} aria-expanded={openIngest === item.id}>
                    <span className="ingest-main">
                      <strong>{item.filename}</strong>
                      <span>{item.successful_rows} baris · {item.failed_rows} gagal</span>
                    </span>
                    <em className={`tag ${item.status}`}>{item.status}</em>
                  </button>
                  {openIngest === item.id && (
                    <div className="ingest-detail">
                      <p>Diunggah {new Date(item.created_at).toLocaleString('id-ID')}</p>
                      <p>ID ingest #{item.id}</p>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </aside>
      </section>
    </main>
  );
}
