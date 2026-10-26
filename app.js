'use strict';

/* BNSC Content Library — no third-party libraries or analytics. */
const CAMPFIRE_HOSTS = new Set(['community.camp-fire.jp', 'camp-fire.jp', 'www.camp-fire.jp']);
const CATEGORIES = ['すべて', 'トレーニング', 'リハビリ', '療育・発達支援', '脳機能・神経科学'];
const TYPES = ['すべて', '動画', '研究解説'];
const STORAGE_KEY = 'bnsc_saved_items_v1';
const state = { items: [], demo: true, keyword: '', type: 'すべて', category: 'すべて', tag: '', onlySaved: false, sort: 'new', saved: new Set() };
const $ = (id) => document.getElementById(id);
const htmlEl = (tag, cls = '', value) => { const el = document.createElement(tag); if (cls) el.className = cls; if (value !== undefined) el.textContent = String(value); return el; };
const normalize = (s) => String(s ?? '').normalize('NFKC').toLocaleLowerCase('ja-JP').replace(/[\s\u3000]+/g, ' ').trim();
const splitTokens = (s) => normalize(s).split(' ').filter(Boolean);

function safeArticleUrl(raw) {
  if (typeof raw !== 'string' || !raw.trim()) return '';
  try {
    const url = new URL(raw.trim());
    if (url.protocol !== 'https:' || !CAMPFIRE_HOSTS.has(url.hostname) || url.username || url.password || url.port || url.search || url.hash) return '';
    return url.toString();
  } catch { return ''; }
}
function readSaved() {
  try { const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY)); return new Set(Array.isArray(parsed) ? parsed.filter((s) => typeof s === 'string') : []); }
  catch { return new Set(); }
}
function storeSaved() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(state.saved))); } catch { /* private mode */ } }
function readQuery() {
  const p = new URLSearchParams(window.location.search);
  state.keyword = (p.get('q') || '').slice(0, 150);
  $('search-input').value = state.keyword;
}
function updateQuery() {
  const url = new URL(window.location.href);
  if (state.keyword.trim()) url.searchParams.set('q', state.keyword.trim()); else url.searchParams.delete('q');
  try { history.replaceState(null, '', url.pathname + url.search + url.hash); } catch { /* local file preview */ }
}
function itemMatches(item) {
  const corpus = normalize([item.title, item.summary, item.category, item.type, ...item.tags, ...item.keywords].join(' '));
  return splitTokens(state.keyword).every((token) => corpus.includes(token))
    && (state.type === 'すべて' || item.type === state.type)
    && (state.category === 'すべて' || item.category === state.category)
    && (!state.tag || item.tags.includes(state.tag))
    && (!state.onlySaved || state.saved.has(item.id));
}
function displayedItems() {
  const out = state.items.filter(itemMatches);
  const collator = new Intl.Collator('ja');
  out.sort((a, b) => {
    if (state.sort === 'title') return collator.compare(a.title, b.title);
    const byDate = (Date.parse(b.published_at || '') || 0) - (Date.parse(a.published_at || '') || 0);
    const byOrder = b.order - a.order;
    return (state.sort === 'old' ? -1 : 1) * (byDate || byOrder);
  });
  return out;
}
function makeFilterButton(text, selected, count, fn, cls='filter-option') {
  const btn = htmlEl('button', `${cls}${selected ? ' active' : ''}`);
  btn.type = 'button'; btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
  btn.append(htmlEl('span', '', text));
  if (count !== null) btn.append(htmlEl('span', 'count', count));
  btn.addEventListener('click', fn);
  return btn;
}
function renderFilters() {
  const typeContainer = $('type-filters');
  const categoryContainer = $('category-filters');
  typeContainer.replaceChildren(...TYPES.map(type => makeFilterButton(type, type === state.type, state.items.filter(item => type === 'すべて' || item.type === type).length, () => { state.type = type; render(); })));
  categoryContainer.replaceChildren(...CATEGORIES.map(category => makeFilterButton(category, category === state.category, state.items.filter(item => category === 'すべて' || item.category === category).length, () => { state.category = category; render(); })));
  const counts = new Map();
  for (const item of state.items) for (const tag of item.tags) counts.set(tag, (counts.get(tag) || 0) + 1);
  const tags = Array.from(counts).sort((a,b)=> b[1]-a[1] || a[0].localeCompare(b[0],'ja')).slice(0, 25);
  $('tag-filters').replaceChildren(...tags.map(([tag]) => makeFilterButton(tag, state.tag === tag, null, () => { state.tag = state.tag === tag ? '' : tag; render(); }, 'tag-option')));
}
function renderActiveFilters() {
  const c = $('active-filters');
  const active = [];
  if (state.keyword) active.push(['検索: ' + state.keyword, () => { state.keyword=''; $('search-input').value=''; updateQuery(); }]);
  if (state.type !== 'すべて') active.push([state.type, ()=>{state.type='すべて';}]);
  if (state.category !== 'すべて') active.push([state.category, ()=>{state.category='すべて';}]);
  if (state.tag) active.push(['#'+state.tag, ()=>{state.tag='';}]);
  if (state.onlySaved) active.push(['あとで見る', ()=>{state.onlySaved=false;}]);
  c.replaceChildren(...active.map(([label, fn])=>{
    const pill=htmlEl('span','active-pill'); pill.append(htmlEl('span','',label));
    const close=htmlEl('button','','×'); close.type='button'; close.setAttribute('aria-label', label+' を解除');
    close.addEventListener('click',()=>{fn();render();}); pill.append(close);return pill;
  }));
}
function friendlyDate(date) {
  const dateObj = new Date(date);
  return Number.isNaN(dateObj.getTime()) ? '' : `${dateObj.getFullYear()}.${String(dateObj.getMonth()+1).padStart(2,'0')}.${String(dateObj.getDate()).padStart(2,'0')}`;
}
function cardFor(item) {
  const articleUrl = item.source === 'vimeo' ? '' : safeArticleUrl(item.url);
  const card=htmlEl('article','content-card');
  const top=htmlEl('div','card-top');
  top.append(htmlEl('span','format-badge'+(item.type==='研究解説'?' article':''),item.type));
  top.append(htmlEl('span','category-badge',item.category));
  if(state.demo) top.append(htmlEl('span','sample-label','サンプル'));
  const title=htmlEl('h4','card-title',item.title);
  const summary=htmlEl('p','card-description',item.summary || '説明文は登録されていません。');
  const tags=htmlEl('div','card-tags');
  for(const t of item.tags.slice(0,5)) tags.append(htmlEl('span','',t));
  const bottom=htmlEl('div','card-bottom');
  const meta=htmlEl('div','meta');
  if(item.duration_minutes) meta.append(htmlEl('span','',item.duration_minutes+'分'));
  if(item.published_at) meta.append(htmlEl('span','',friendlyDate(item.published_at)));
  const actions=htmlEl('div','card-actions');
  const save=htmlEl('button','save-button',state.saved.has(item.id)?'★':'☆');
  save.type='button'; save.setAttribute('aria-pressed',state.saved.has(item.id)?'true':'false');
  save.setAttribute('aria-label',item.title+' をあとで見る'+(state.saved.has(item.id)?'から削除':'に保存'));
  save.addEventListener('click',()=>{ if(state.saved.has(item.id)) state.saved.delete(item.id); else state.saved.add(item.id); storeSaved(); render(); });
  actions.append(save);
  if(articleUrl) {
    const link=htmlEl('a','open-link',item.type==='動画'?'動画を開く ↗':'記事を開く ↗');
    link.href=articleUrl;link.target='_blank';link.rel='noopener noreferrer';
    link.setAttribute('aria-label',item.title+' のCAMPFIRE投稿を開く（新しいタブ）');
    actions.append(link);
  } else actions.append(htmlEl('span','unavailable',item.source === 'vimeo' ? '視聴機能は準備中' : '投稿URL未登録'));
  bottom.append(meta,actions);
  card.append(top,title,summary,tags,bottom);
  return card;
}
function render() {
  renderFilters(); renderActiveFilters();
  const items=displayedItems();
  $('result-count').textContent = items.length+'件';
  $('bookmark-toggle').setAttribute('aria-pressed',state.onlySaved?'true':'false');
  $('bookmark-toggle').firstElementChild.textContent = state.onlySaved?'★':'☆';
  $('results-grid').replaceChildren(...items.map(cardFor));
  $('results-grid').setAttribute('aria-busy','false');
  $('empty-state').hidden=items.length!==0;
  const preparing = state.items.length === 0;
  $('empty-state').querySelector('h4').textContent = preparing ? 'コンテンツ登録の準備中です' : '該当するコンテンツがありません';
  $('empty-state').querySelector('p').textContent = preparing ? '確認済みの動画・研究解説を順次登録します。' : 'キーワードを短くするか、絞り込み条件を変更してください。';
  $('empty-reset').hidden = preparing;
}
function reset() {
  Object.assign(state,{keyword:'',type:'すべて',category:'すべて',tag:'',onlySaved:false});
  $('search-input').value=''; updateQuery(); render();
}
function wireUI() {
  $('search-form').addEventListener('submit',e=>{e.preventDefault();state.keyword=$('search-input').value.trim();updateQuery();render();$('results').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});});
  let searchDebounce;
  $('search-input').addEventListener('input',e=>{clearTimeout(searchDebounce);searchDebounce=setTimeout(()=>{state.keyword=e.target.value.trim();updateQuery();render();},120);});
  $('clear-filters').addEventListener('click',reset);
  $('empty-reset').addEventListener('click',reset);
  $('bookmark-toggle').addEventListener('click',()=>{state.onlySaved=!state.onlySaved;render();});
  $('sort-select').addEventListener('change',e=>{state.sort=e.target.value;render();});
  $('filters-mobile-toggle').addEventListener('click',()=>{const sidebar=document.querySelector('.sidebar'); const open=sidebar.classList.toggle('mobile-open'); $('filters-mobile-toggle').setAttribute('aria-expanded',String(open)); $('filters-mobile-toggle').textContent=open?'条件を閉じる ▴':'条件を表示 ▾';});
  document.querySelectorAll('[data-keyword]').forEach(btn=>btn.addEventListener('click',()=>{state.keyword=btn.dataset.keyword;$('search-input').value=state.keyword;updateQuery();render();$('results').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}));
  document.addEventListener('keydown',e=>{if(e.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('search-input').focus();}});
  window.addEventListener('popstate',()=>{readQuery();render();});
}
async function initialize() {
  state.saved=readSaved(); readQuery(); wireUI();
  try {
    const response = await fetch('./data/contents.json', {cache:'no-store'});
    if (!response.ok) throw new Error('コンテンツデータを読み込めませんでした。');
    const data=await response.json();
    if(!data || !Array.isArray(data.items)) throw new Error('データ形式に問題があります。');
    state.demo=Boolean(data.demo);
    state.items=data.items.map((it,index)=>({
      source:it.source === 'vimeo' ? 'vimeo' : 'csv',id:String(it.id||`item-${index}`),title:String(it.title||'タイトルなし'),type:TYPES.includes(it.type)?it.type:'動画',
      category:CATEGORIES.includes(it.category)?it.category:'脳機能・神経科学',
      summary:String(it.summary||''),tags:Array.isArray(it.tags)?it.tags.map(String):[],
      keywords:Array.isArray(it.keywords)?it.keywords.map(String):[],
      duration_minutes:Math.max(0,Number(it.duration_minutes)||0),published_at:String(it.published_at||''),url:String(it.url||''),order:index
    }));
    $('demo-notice').hidden=!state.demo;
    render();
  } catch (err) {
    $('results-grid').setAttribute('aria-busy','false');
    $('results-grid').replaceChildren(htmlEl('p','',`読み込みに失敗しました。${err.message} ローカルでは README の手順に従ってサーバーを起動してください。`));
  }
}
initialize();
