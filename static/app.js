/* Swipe&Watch 2.0 — lightweight single-page client for the existing FastAPI service. */
'use strict';

const API = '/api';
const TOKEN_KEY = 'sw_token';
const GENRE_OPTIONS = [
  {id:'thriller',label:'Триллер и детектив',desc:'Загадки, расследования и интрига',genres:['Триллер','Детектив'],icon:'search'},
  {id:'scifi',label:'Фантастика и приключения',desc:'Другие миры и большие истории',genres:['Фантастика','Приключения'],icon:'planet'},
  {id:'drama',label:'Драма и мелодрама',desc:'Сильные истории, эмоции и чувства',genres:['Драма'],icon:'clapper'},
  {id:'comedy',label:'Комедия',desc:'Лёгкое кино и хорошее настроение',genres:['Комедия'],icon:'smile'},
  {id:'horror',label:'Ужасы',desc:'Напряжение и мурашки',genres:['Хоррор'],icon:'moon'},
  {id:'action',label:'Экшен и криминал',desc:'Движение, риск и погони',genres:['Экшен','Криминал'],icon:'zap'},
  {id:'mystery',label:'Мистика и фэнтези',desc:'Необъяснимое и загадочное',genres:['Мистика'],icon:'sparkles'}
];
const ICONS = {
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  sparkles:'<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/>',
  bookmark:'<path d="M6 4.8A1.8 1.8 0 0 1 7.8 3h8.4A1.8 1.8 0 0 1 18 4.8V21l-6-3.8L6 21z"/>',
  history:'<path d="M3 11a9 9 0 1 1 2.6 6.4"/><path d="M3 4v7h7"/><path d="M12 7v5l3 2"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/>',
  planet:'<circle cx="12" cy="12" r="8"/><path d="M4 12c2.5-3 13.5-3 16 0M12 4c-3 2.5-3 13.5 0 16"/>',
  clapper:'<path d="M4 9h16v11H4zM4 5l16 4M8 4l4 5M15 3l4 5"/>',
  smile:'<circle cx="12" cy="12" r="9"/><path d="M8 14s1.3 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>',
  moon:'<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/>',
  zap:'<path d="m13 2-9 12h7l-1 8 10-13h-7z"/>',
  heart:'<path d="M20.8 8.7c0 5-8.8 11-8.8 11s-8.8-6-8.8-11A4.7 4.7 0 0 1 12 6a4.7 4.7 0 0 1 8.8 2.7Z"/>',
  shapes:'<circle cx="8" cy="8" r="4"/><path d="M16 4h4v4h-4zM16 14l4 7h-8z"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  close:'<path d="m18 6-12 12M6 6l12 12"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  chevron:'<path d="m9 18 6-6-6-6"/>',
  star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  trash:'<path d="M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  filter:'<path d="M4 5h16M7 12h10m-7 7h4"/>',
  play:'<path d="m8 5 11 7-11 7z"/>',
  undo:'<path d="M9 14 4 9l5-5"/><path d="M4 9h9a7 7 0 0 1 0 14h-2"/>',
  layers:'<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 20h16"/>',
  vk:'<path d="M4 8c.5 5 3.3 9 7.7 9h.8v-3.4c1.8.2 3.2 1.5 3.8 3.4H20c-.7-2.6-2.1-4.2-4-5 1.8-1 3-2.7 3.5-5H16c-.5 1.7-1.8 3.4-3.5 3.6V7H9.7v7.3C8 13.8 6.6 11.2 6.3 8z"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.1 1.9-1.8 1.8-2-1.1-.1.1-2.2.9-.5 2.2h-2.6l-.5-2.2-2.2-.9-.1-.1-2 1.1-1.8-1.8 1.1-2-.1-.1-.9-2.2L2 12.3V9.7l2.2-.5.9-2.2.1-.1-1.1-2L5.9 3l2 1.1.1-.1 2.2-.9.5-2.2h2.6l.5 2.2 2.2.9.1.1 2-1.1 1.8 1.8-1.1 2 .1.1.9 2.2 2.2.5v2.6l-2.2.5z"/>',
  external:'<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/>',
  film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4m-4 6h4m10-6h4m-4 6h4"/>',
  library:'<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21z"/><path d="M4 5.5v15.2M8 7h8m-8 4h8"/>',
  chevronDown:'<path d="m6 9 6 6 6-6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.5-3"/>',
  copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
};
const state = {
  token: '', page: 'home', meta: null, dashboard: null, profile: null, providers: {vk:false},
  selectedGenres: new Set(), sessionLimit: 15, filterDefaults: {content_type:'all',max_duration:'',year_from:'',year_to:'',min_rating:'',max_age:''},
  session: null, collectionView: 'watchlist', collectionSearch: '', collectionGenre: '',
  collectionItems: [], historyItems: [], movieCache: new Map(), detailMovie: null, toastTimer: null,
  loadingMore: false, finishing: false, swiping: false, collectionTotal: 0, collectionGenreSet: new Set(), pendingRatingMovie: null, sessionDetail: null,
  collectionMap: new Map(), collectionReq: 0, sessionResult: null, confirmResolve: null, storageWarned: false
};

const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
const svg = (name, cls='') => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const safeUrl = value => { try { const u = new URL(value, location.origin); return ['http:','https:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } };
const fmtDate = value => { if (!value) return 'Недавно'; const d = new Date(value); return new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',year:'numeric'}).format(d); };
const fmtShortDate = value => { if (!value) return ''; return new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'short'}).format(new Date(value)); };
const getInitial = name => (String(name || 'К').trim()[0] || 'К').toLocaleUpperCase('ru-RU');

const tokenStore = {
  mem: '',
  get() { for (const kind of ['localStorage','sessionStorage']) { try { const v = window[kind].getItem(TOKEN_KEY); if (v) return v; } catch {} } return this.mem; },
  set(value) { this.mem = value; for (const kind of ['localStorage','sessionStorage']) { try { window[kind].setItem(TOKEN_KEY, value); return true; } catch {} } return false; },
  clear() { this.mem = ''; for (const kind of ['localStorage','sessionStorage']) { try { window[kind].removeItem(TOKEN_KEY); } catch {} } }
};
const FIELD_LABELS = {year_from:'Год «от»',year_to:'Год «до»',max_duration:'Длительность',min_rating:'Минимальный рейтинг',max_age:'Возраст',limit:'Размер подборки',display_name:'Имя',note:'Заметка',rating:'Оценка'};
function validationText(item) {
  const msg = String(item?.msg || ''), type = String(item?.type || '');
  if (type === 'value_error') return msg.replace(/^Value error,\s*/, '');
  const field = FIELD_LABELS[item?.loc?.[item.loc.length - 1]] || 'Значение';
  if (/greater_than|too_short/.test(type)) return `${field}: слишком маленькое значение`;
  if (/less_than|too_long/.test(type)) return `${field}: слишком большое значение`;
  if (/missing/.test(type)) return `${field}: обязательное поле`;
  if (/type|parsing/.test(type)) return `${field}: некорректное значение`;
  return msg || 'Проверьте введённые данные';
}
function humanizeError(data, status) {
  const d = data && typeof data === 'object' ? (data.detail ?? data.message) : null;
  if (Array.isArray(d)) { const list = [...new Set(d.map(validationText).filter(Boolean))]; if (list.length) return list.join('. '); }
  if (typeof d === 'string' && d) return d;
  if (d && typeof d === 'object') return validationText(d);
  if (status === 429) return 'Слишком много запросов. Попробуйте чуть позже.';
  if (status >= 500) return 'Сервис временно недоступен. Попробуйте ещё раз.';
  return `Ошибка запроса (${status})`;
}
function httpError(message, status) { const e = new Error(message); e.status = status; return e; }
function setOffline(flag) { const el = $('#netBanner'); if (el) el.hidden = !flag; }
let guestPromise = null;
function createGuest() {
  if (!guestPromise) guestPromise = (async () => {
    let response;
    try { response = await fetch(API + '/auth/anon', {method:'POST', headers:{Accept:'application/json'}}); }
    catch { setOffline(true); throw httpError('Нет соединения с сервером. Проверьте интернет.', 0); }
    setOffline(false);
    let data = null; try { data = await response.json(); } catch {}
    if (!response.ok) throw httpError(humanizeError(data, response.status), response.status);
    state.token = data.token;
    if (!tokenStore.set(state.token) && !state.storageWarned) { state.storageWarned = true; showToast('Браузер не сохраняет вход: после закрытия вкладки гостевой профиль будет потерян.', 6500); }
    return data;
  })().finally(() => { guestPromise = null; });
  return guestPromise;
}
async function api(path, options={}) {
  const headers = new Headers(options.headers || {});
  headers.set('Accept','application/json');
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
  let body = options.body;
  if (body !== undefined && !(body instanceof FormData) && typeof body !== 'string') {
    headers.set('Content-Type','application/json'); body = JSON.stringify(body);
  }
  let response;
  try { response = await fetch(API + path, {...options, headers, body}); }
  catch { setOffline(true); throw httpError('Нет соединения с сервером. Проверьте интернет.', 0); }
  setOffline(false);
  const fresh = response.headers.get('X-Refreshed-Token');       // скользящий срок жизни токена
  if (fresh && fresh !== state.token) { state.token = fresh; tokenStore.set(fresh); }
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (response.status === 401 && !options._retried && !path.startsWith('/auth/')) {
    const had = !!state.token;
    await createGuest();                                          // токен истёк/не принят -> новый гость, запрос повторяем
    if (had) showToast('Сессия истекла — вы вошли как гость.');
    return api(path, {...options, _retried: true});
  }
  if (!response.ok) throw httpError(humanizeError(data, response.status), response.status);
  return data;
}

async function ensureAuth() {
  state.token = tokenStore.get();
  if (!state.token) await createGuest();
  else await api('/meta');                                        // 401 здесь прозрачно создаст гостя
}

function showToast(message, duration=2600, action=null) {
  const el = $('#toast'); if (!el) return;
  el.innerHTML = esc(message) + (action ? ` <button class="toast-action" data-action="${esc(action.name)}" data-id="${esc(action.id)}">${esc(action.label)}</button>` : '');
  el.classList.toggle('has-action', !!action); el.classList.add('show');
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(()=>el.classList.remove('show'),duration);
}
const FLAG_KEYS = ['is_favorite','in_watchlist','watched','skipped','rating','note'];
function pickFlags(obj) { const out = {}; let any = false; for (const k of FLAG_KEYS) if (k in obj) { out[k] = obj[k]; any = true; } return any ? out : null; }
function setCollection(id, flags) { state.collectionMap.set(String(id), {...(flags || {})}); }
function mergeCollection(id, flags) { const k = String(id); state.collectionMap.set(k, {...(state.collectionMap.get(k) || {}), ...(flags || {})}); }
function cacheMovies(items) {
  (items || []).forEach(item => {
    const movie = item.movie || item;
    if (!movie?.id) return;
    state.movieCache.set(String(movie.id), movie);
    if (item.movie) { const f = pickFlags(item); if (f) setCollection(movie.id, f); }   // единый источник состояния кнопок
  });
}
function posterFail(img){
  img.onerror=null;
  const box=document.createElement('div');
  box.className='poster-fallback';
  box.textContent=(img.alt||'').replace(/^Постер:\s*/,'')||'Без постера';
  img.replaceWith(box);
}
function moviePoster(movie, extra='', eager=false) {
  const src = safeUrl(movie?.posterUrl);
  if (!src) return `<div class="poster-fallback ${extra}">${esc(movie?.title || 'Без постера')}</div>`;
  return `<img src="${esc(src)}" alt="Постер: ${esc(movie.title)}" ${eager?'':'loading="lazy"'} decoding="async" referrerpolicy="no-referrer" draggable="false" onerror="posterFail(this)">`;
}
function swipeCardHTML(movie, interactive) {
  const kp = movie.kp ? Number(movie.kp).toFixed(1) : '';
  const imdb = movie.imdb ? Number(movie.imdb).toFixed(1) : '';
  const orig = movie.originalTitle && movie.originalTitle !== movie.title ? movie.originalTitle : '';
  const typeLine = [movie.type || 'Фильм', movie.year, movie.age].filter(Boolean).map(esc).join(' <span>·</span> ');
  const topType = [movie.type || 'Фильм', movie.year].filter(Boolean).map(esc).join(' <i>·</i> ');
  return `<div class="cinema-poster">${moviePoster(movie,'',true)}<div class="cinema-poster-shade"></div>
    ${interactive ? `<div id="stampRight" class="swipe-stamp stamp-right">${svg('bookmark')} В МОЙ СПИСОК</div><div id="stampLeft" class="swipe-stamp stamp-left">${svg('close')} ПРОПУСТИТЬ</div><div id="stampUp" class="swipe-stamp stamp-up">${svg('check')} УЖЕ СМОТРЕЛ</div>` : ''}
    <div class="poster-topline"><span class="poster-type">${topType}</span><div class="poster-ratings">${kp?`<span class="poster-kp">★ ${kp}</span>`:''}${imdb?`<span class="poster-imdb">IMDb ${imdb}</span>`:''}</div></div>
    <div class="poster-bottomline"><div class="poster-genres">${(movie.genres||[]).slice(0,3).map(g=>`<span>${esc(g)}</span>`).join('')}</div>${movie.duration?`<span class="poster-runtime">${esc(movie.duration)}</span>`:''}</div>
    <span class="poster-index">S<span>·</span>W / PICK</span></div>
  <div class="cinema-info">
    <div class="cinema-info-heading"><div class="cinema-type-line">${typeLine}</div><h2>${esc(movie.title)}</h2>${orig?`<p class="cinema-original">${esc(orig)}</p>`:''}</div>
    <p class="cinema-hook">${esc(movie.synopsis||movie.shortHook||'Описание пока отсутствует.')}</p>
    ${interactive ? `<button class="cinema-more" data-action="movie-details" data-id="${esc(movie.id)}">Подробнее о фильме ${svg('chevron')}</button>` : ''}
  </div>`;
}
function renderMovieCard(movie, collectionState=null) {
  state.movieCache.set(String(movie.id),movie);
  collectionState = collectionState || getCollectionState(movie.id);
  const isFavorite = !!collectionState?.is_favorite;
  const inWatchlist = !!collectionState?.in_watchlist;
  const isWatched = !!collectionState?.watched;
  const rating = movie.kp ?? movie.imdb;
  return `<article class="movie-card" data-movie-card="${esc(movie.id)}">
    <div class="poster-frame" data-action="movie-details" data-id="${esc(movie.id)}">${moviePoster(movie)}
      ${rating ? `<span class="poster-ribbon">★ ${esc(Number(rating).toFixed(1))}</span>` : ''}
      <button class="poster-action ${isFavorite?'active':''}" data-action="toggle-favorite" data-id="${esc(movie.id)}" aria-label="${isFavorite?'Убрать из избранного':'В избранное'}">${svg('heart')}</button>
    </div>
    <div class="movie-card-copy">
      <div class="movie-card-title" data-action="movie-details" data-id="${esc(movie.id)}">${esc(movie.title)}</div>
      <div class="movie-card-meta"><span>${esc(movie.year || 'Год неизвестен')}</span><span>·</span><span>${esc(movie.type || 'Фильм')}</span>${rating ? `<span class="movie-card-rating">★ ${esc(Number(rating).toFixed(1))}</span>`:''}</div>
      ${collectionState?.rating?`<div class="movie-card-meta"><span class="movie-card-rating">Моя оценка: ${Number((collectionState.rating/2).toFixed(1))}/5</span></div>`:''}${collectionState?.note?`<div class="movie-card-note">${esc(collectionState.note)}</div>`:''}
      <div class="movie-card-actions">
        <button class="btn-icon ${inWatchlist?'active':''}" data-action="toggle-watchlist" data-id="${esc(movie.id)}" title="Хочу посмотреть" aria-label="Хочу посмотреть">${svg('bookmark')}</button>
        <button class="btn-icon ${isWatched?'active':''}" data-action="mark-watched" data-id="${esc(movie.id)}" title="Уже смотрел" aria-label="Уже смотрел">${svg('check')}</button>
        <button class="btn-icon" data-action="movie-details" data-id="${esc(movie.id)}" title="Подробнее">${svg('info')}</button>
      </div>
    </div>
  </article>`;
}

function setNav(page) {
  const labels={home:'Главная',discover:'Подбор фильма',collection:'Моя коллекция',history:'История подборок',profile:'Профиль'};
  $('#pageLabel').textContent=labels[page] || 'Swipe&Watch';
  $$('.nav-item,.mobile-nav-item').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
}
function navigate(page) {
  state.page=page; setNav(page);
  if(page==='home') renderHome();
  else if(page==='discover') renderDiscover();
  else if(page==='collection') loadCollection();
  else if(page==='history') loadHistory();
  else if(page==='profile') renderProfile();
  window.scrollTo({top:0,behavior:'smooth'});
}

async function bootstrap() {
  $('#view').innerHTML='<div class="boot-state"><span class="loader"></span><p>Настраиваем ваш кинозал…</p></div>';
  try {
    await ensureAuth();
    const query=new URLSearchParams(location.search);
    const vkCode=query.get('vk_code');
    const vkError=query.get('vk_error');
    if(vkCode){
      history.replaceState({},'',location.pathname);
      try{
        const exchanged=await api(`/auth/exchange?code=${encodeURIComponent(vkCode)}`,{method:'POST'});
        state.token=exchanged.token; tokenStore.set(state.token);
        showToast('VK ID подключён. Коллекция сохранена.');
      }catch(exchangeError){
        showToast('Не удалось завершить вход через VK ID. Гостевой профиль сохранён.');
        console.warn('VK exchange',exchangeError);
      }
    } else if(vkError){
      history.replaceState({},'',location.pathname);
      showToast('Не удалось завершить вход через VK ID. Попробуйте ещё раз.');
    }
    const [meta,providers]=await Promise.all([api('/meta'),api('/auth/providers')]);
    state.meta=meta; state.providers=providers;
    try { state.dashboard=await api('/me/dashboard'); state.profile=state.dashboard.profile; } catch(e){ console.warn(e); showToast('Не удалось загрузить статистику и коллекцию. Обновите страницу.',4500); }
    refreshIdentity();
    if('serviceWorker' in navigator){ navigator.serviceWorker.register('/sw.js').catch(()=>{}); }
    navigate('home');
  } catch(error) {
    console.error(error);
    $('#view').innerHTML=`<div class="empty-state"><div class="empty-icon">${svg('refresh')}</div><h3>Не удалось подключиться</h3><p>${esc(String(error.message||'').replace(/[.\s]+$/,''))}. Нажмите «Повторить» — обычно этого достаточно.</p><button class="btn btn-primary" data-action="retry">Повторить</button></div>`;
  }
}
function refreshIdentity() {
  const profile=state.profile||{display_name:'Киноман'};
  const name=profile.display_name||'Киноман', initial=getInitial(name);
  $('#sideName').textContent=name; $('#sideStatus').textContent=state.dashboard?.has_vk?'VK ID подключён':'Гостевой профиль';
  $('#sideAvatar').innerHTML=profile.avatar_url?`<img src="${esc(safeUrl(profile.avatar_url))}" alt="">`:initial;
  $('#topAvatar').innerHTML=profile.avatar_url?`<img src="${esc(safeUrl(profile.avatar_url))}" alt="">`:initial;
  $('#navWatchCount').textContent=String(state.dashboard?.counts?.watchlist ?? 0);
}

function renderHome() {
  const d=state.dashboard||{profile:{display_name:'Киноман'},counts:{favorites:0,watchlist:0,watched:0,skipped:0},recent:[]};
  cacheMovies(d.recent||[]);
  const name=(d.profile?.display_name||'Киноман').split(' ')[0];
  const active=d.active_session;
  const posters=(d.recent||[]).slice(0,2).map(x=>x.movie);
  const continueBlock=active?`<div class="section-block"><div class="resume-card"><div class="resume-copy"><div class="resume-icon">${svg('play')}</div><div><strong>У вас осталась незавершённая подборка</strong><small>Начата ${fmtDate(active.started_at)} · ${active.limit} карточек</small></div></div><button class="btn btn-dark" data-action="resume-session">Продолжить ${svg('arrow')}</button></div></div>`:'';
  const quickMoods=[['comedy','Лёгкое кино'],['thriller','Немного интриги'],['drama','Сильная история'],['scifi','Другой мир'],['horror','Хочется острых ощущений']];
  $('#view').innerHTML=`
    <section class="hero">
      <div class="hero-copy"><div class="hero-kicker">ВАШЕ ЛИЧНОЕ КИНОПРОСТРАНСТВО</div><h1>Привет, ${esc(name)}.<br>Что будем смотреть?</h1><p>Не тратьте вечер на бесконечный поиск. Расскажите, какое у вас настроение — мы подберём фильмы под ваш вкус.</p><div class="hero-actions"><button class="btn btn-primary" data-action="go-discover">Подобрать фильм ${svg('arrow')}</button><button class="btn btn-outline" data-action="surprise">Удиви меня</button></div></div>
      <div class="hero-art"><div class="hero-orbit"></div><div class="hero-film-stack">${posters[0]?.posterUrl?`<img class="hero-poster one" src="${esc(safeUrl(posters[0].posterUrl))}" alt="">`:''}${posters[1]?.posterUrl?`<img class="hero-poster two" src="${esc(safeUrl(posters[1].posterUrl))}" alt="">`:'<div class="hero-poster-fallback"></div>'}</div><div class="hero-ornament">cinema</div></div>
    </section>
    ${continueBlock}
    <section class="section-block"><div class="section-heading"><div><h2>Какое сегодня настроение?</h2><p>Выберите направление — детали можно настроить дальше.</p></div></div><div class="quick-moods">${quickMoods.map(([id,label])=>`<button class="mood-chip" data-action="mood" data-id="${id}">${esc(label)}</button>`).join('')}</div></section>
    <section class="section-block"><div class="section-heading"><div><h2>Ваша коллекция</h2><p>Всё, что вы сохранили и уже посмотрели.</p></div><button class="text-link" data-page="collection">Открыть коллекцию →</button></div><div class="stats-grid">
      ${statCard('Хочу посмотреть',d.counts?.watchlist||0,'bookmark','Список на потом')}${statCard('Избранное',d.counts?.favorites||0,'heart','Особенно любимое')}${statCard('Просмотрено',d.counts?.watched||0,'check','Ваша история кино')}${statCard('Подборки',d.sessions_count||0,'layers','Создано подборок')}
    </div></section>
    <section class="section-block"><div class="section-heading"><div><h2>Недавно в коллекции</h2><p>Последние фильмы, с которыми вы взаимодействовали.</p></div><button class="text-link" data-page="collection">Вся коллекция →</button></div>${d.recent?.length?`<div class="movie-grid">${d.recent.slice(0,5).map(item=>renderMovieCard(item.movie,item)).join('')}</div>`:emptyState('library','Здесь пока пусто','Добавляйте фильмы во время подбора — они появятся в вашей личной коллекции.','Начать подбор','go-discover')}</section>
    <section class="section-block"><div class="section-heading"><div><h2>Небольшое напоминание</h2><p>Swipe&Watch помогает выбрать, а не решает за вас.</p></div></div><div class="inline-note">Ваши реакции постепенно формируют профиль вкуса. Чем чаще вы пользуетесь подбором и отмечаете просмотренное, тем точнее становятся следующие рекомендации.</div></section>`;
}
function statCard(label,value,iconName,detail){return `<div class="stat-card"><div class="stat-card-label">${svg(iconName)} ${esc(label)}</div><div class="stat-card-value">${Number(value).toLocaleString('ru-RU')}</div><div class="stat-card-detail">${esc(detail)}</div></div>`;}
function emptyState(iconName,title,copy,buttonLabel,buttonAction){return `<div class="empty-state"><div class="empty-icon">${svg(iconName)}</div><h3>${esc(title)}</h3><p>${esc(copy)}</p>${buttonLabel?`<button class="btn btn-primary" data-action="${buttonAction}">${esc(buttonLabel)} ${svg('arrow')}</button>`:''}</div>`;}

function renderDiscover() {
  const active=state.dashboard?.active_session;
  const genresHtml=GENRE_OPTIONS.map(g=>`<button class="genre-option ${state.selectedGenres.has(g.id)?'selected':''}" data-action="toggle-genre" data-id="${g.id}"><span class="genre-option-icon">${svg(g.icon)}</span><span><strong>${esc(g.label)}</strong><small>${esc(g.desc)}</small></span></button>`).join('');
  $('#view').innerHTML=`<div class="heading-row"><div><div class="eyebrow">ВАШ СЛЕДУЮЩИЙ ФИЛЬМ</div><h1 class="page-title">Подбор по настроению</h1><p class="page-subtitle">Выберите жанры, задайте несколько ограничений и доверьте остальное алгоритму.</p></div><div class="heading-actions"><button class="btn btn-quiet" data-action="surprise">${svg('sparkles')} Удиви меня</button></div></div>
    ${active?`<div class="resume-card" style="margin-bottom:22px"><div class="resume-copy"><div class="resume-icon">${svg('play')}</div><div><strong>Есть незавершённая подборка</strong><small>Можно продолжить с того же места.</small></div></div><button class="btn btn-dark" data-action="resume-session">Продолжить ${svg('arrow')}</button></div>`:''}
    <div class="discover-layout"><div class="discover-main">
      <section class="panel"><div class="eyebrow">01 / НАСТРОЕНИЕ</div><h2 class="panel-title" style="margin-top:7px">Что вам сейчас ближе?</h2><p class="panel-subtitle">Можно выбрать несколько вариантов или оставить всё открытым.</p><div class="genre-grid">${genresHtml}</div></section>
      <section class="panel" style="margin-top:13px"><div class="eyebrow">02 / ФОРМАТ И ВРЕМЯ</div><h2 class="panel-title" style="margin-top:7px">Какие фильмы показывать?</h2><div class="form-grid">
        <div class="field"><label for="filterType">Формат</label><select id="filterType" class="select-field"><option value="all" ${state.filterDefaults.content_type==='all'?'selected':''}>Фильмы и сериалы</option><option value="films" ${state.filterDefaults.content_type==='films'?'selected':''}>Только фильмы</option><option value="series" ${state.filterDefaults.content_type==='series'?'selected':''}>Только сериалы</option></select></div>
        <div class="field"><label for="filterDuration">Максимальная длительность</label><select id="filterDuration" class="select-field"><option value="">Любая</option><option value="90" ${state.filterDefaults.max_duration===90?'selected':''}>До 90 минут</option><option value="120" ${state.filterDefaults.max_duration===120?'selected':''}>До 2 часов</option><option value="150" ${state.filterDefaults.max_duration===150?'selected':''}>До 2,5 часов</option><option value="180" ${state.filterDefaults.max_duration===180?'selected':''}>До 3 часов</option></select></div>
        <div class="field"><label for="filterYearFrom">Год выпуска от</label><input id="filterYearFrom" class="input-field" type="number" min="1888" max="2100" placeholder="Любой" value="${esc(state.filterDefaults.year_from||'')}"></div>
        <div class="field"><label for="filterYearTo">Год выпуска до</label><input id="filterYearTo" class="input-field" type="number" min="1888" max="2100" placeholder="Любой" value="${esc(state.filterDefaults.year_to||'')}"></div>
        <div class="field"><label for="filterRating">Минимальный рейтинг</label><select id="filterRating" class="select-field"><option value="">Неважно</option><option value="6" ${state.filterDefaults.min_rating===6?'selected':''}>От 6.0</option><option value="7" ${state.filterDefaults.min_rating===7?'selected':''}>От 7.0</option><option value="8" ${state.filterDefaults.min_rating===8?'selected':''}>От 8.0</option></select></div>
        <div class="field"><label for="filterAge">Возрастное ограничение</label><select id="filterAge" class="select-field"><option value="">Любое</option><option value="6" ${state.filterDefaults.max_age===6?'selected':''}>До 6+</option><option value="12" ${state.filterDefaults.max_age===12?'selected':''}>До 12+</option><option value="16" ${state.filterDefaults.max_age===16?'selected':''}>До 16+</option><option value="18" ${state.filterDefaults.max_age===18?'selected':''}>До 18+</option></select></div>
      </div><div class="field-error" id="filterError" role="alert" hidden></div></section>
      <section class="panel" style="margin-top:13px"><div class="eyebrow">03 / РАЗМЕР ПОДБОРКИ</div><h2 class="panel-title" style="margin-top:7px">Сколько карточек показать?</h2><div class="choice-group">${[10,15,20].map(n=>`<button class="choice-pill ${state.sessionLimit===n?'selected':''}" data-action="set-limit" data-id="${n}">${n} фильмов</button>`).join('')}</div><div class="spacer"></div><div class="inline-note">Никаких обязательных анкет: можно выбрать только настроение, а все остальные фильтры оставить по умолчанию. Если подходящих фильмов окажется меньше, чем вы запросили, подбор закончится раньше.</div><div style="display:flex;justify-content:flex-end;margin-top:18px"><button class="btn btn-primary" data-action="start-session">Начать подбор ${svg('arrow')}</button></div></section>
    </div><aside class="discovery-aside"><div class="panel"><div class="eyebrow">КАК ЭТО РАБОТАЕТ</div><h3 class="panel-title" style="margin-top:7px">Подбор учится на ваших реакциях</h3><p class="panel-subtitle" style="margin-top:12px">Если выбрать жанр, мы покажем только его. Лайки, пропуски и оценки помогают понять, что вам по вкусу, а в конце вы получите лучшее совпадение и несколько хороших вариантов.</p></div></aside></div>`;
}

const EMPTY_FILTERS={content_type:'all',max_duration:'',year_from:'',year_to:'',min_rating:'',max_age:''};
function readSessionFilters() {
  const read=(key,id)=>{const el=document.getElementById(id);return el?el.value:(state.filterDefaults[key]??'');};
  const filters={content_type:read('content_type','filterType')||'all'};
  [['max_duration','filterDuration'],['year_from','filterYearFrom'],['year_to','filterYearTo'],['min_rating','filterRating'],['max_age','filterAge']].forEach(([key,id])=>{const v=read(key,id);if(v!==''&&v!=null)filters[key]=Number(v);});
  state.filterDefaults={...EMPTY_FILTERS,...filters};
  return filters;
}
function validateFilters(f) {
  for (const [k,label] of [['year_from','Год «от»'],['year_to','Год «до»']]) {
    if (f[k] != null && (!Number.isInteger(f[k]) || f[k] < 1888 || f[k] > 2100)) return `${label}: введите год от 1888 до 2100`;
  }
  if (f.year_from != null && f.year_to != null && f.year_from > f.year_to) return 'Год «от» не может быть больше года «до»';
  return '';
}
function showFilterError(message) {
  const el = $('#filterError'); if (el) { el.textContent = message; el.hidden = !message; }
  ['filterYearFrom','filterYearTo'].forEach(id => $('#'+id)?.classList.toggle('is-invalid', !!message));
}
async function startSession(surprise=false, filtersOverride=null) {
  const filters=filtersOverride||(state.page==='discover'?readSessionFilters():{content_type:'all'});
  const problem=validateFilters(filters);
  if(problem){showFilterError(problem);$('#filterError')?.scrollIntoView({block:'center',behavior:'smooth'});return;}
  const activeId=state.session?.id||state.dashboard?.active_session?.session_id;
  if(activeId){
    if(!(await confirmDialog({title:'Завершить текущую подборку?',text:'Незавершённая подборка будет закрыта, а новая начнётся с чистого листа.',okLabel:'Начать новую'})))return;
    try{await api(`/sessions/${activeId}/finish`,{method:'POST'});}catch(error){showToast('Не удалось завершить текущую подборку: '+error.message);return;}
  }
  const initialGenres=surprise?[]:[...state.selectedGenres].flatMap(id=>GENRE_OPTIONS.find(g=>g.id===id)?.genres||[]);
  $('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Собираем вашу подборку…</div>';
  try{
    const data=await api('/sessions',{method:'POST',body:{limit:state.sessionLimit,initial_genres:initialGenres,surprise:!!surprise,filters}});
    state.session={id:data.session_id,limit:state.sessionLimit,servedTotal:data.served_total,plannedTotal:data.planned_total,exhausted:data.exhausted,queue:[...data.cards],allCards:[...data.cards],events:[],actions:0,reactions:[],filters,surprise,startedAt:new Date().toISOString(),undoStack:[]};
    cacheMovies(data.cards); renderSession();
  }catch(error){console.error(error);showToast(error.message||'Не удалось начать подбор');navigate('discover');}
}
async function resumeSession() {
  try{
    const data=await api('/sessions/active');
    if(!data.session){showToast('Активной подборки нет');state.dashboard=await api('/me/dashboard');navigate('home');return;}
    const s=data.session; const reacted=new Set((s.events||[]).map(e=>String(e.movie_id)));
    state.session={id:s.session_id,limit:s.limit,servedTotal:s.served_total,plannedTotal:s.planned_total??s.limit,exhausted:!!s.exhausted,queue:s.cards.filter(m=>!reacted.has(String(m.id))),allCards:s.cards,events:s.events||[],actions:(s.events||[]).length,reactions:(s.events||[]).map(e=>({...e,movie:state.movieCache.get(String(e.movie_id))||s.cards.find(m=>String(m.id)===String(e.movie_id))})),filters:s.filters||{},surprise:s.surprise,startedAt:s.started_at,undoStack:[]};
    cacheMovies(s.cards);renderSession();
  }catch(error){showToast('Не удалось восстановить подборку');console.error(error);}
}
function currentCard(){return state.session?.queue?.[0]||null;}
function sessionIsDone(s){return !!s.exhausted||s.servedTotal>=(s.plannedTotal||s.limit);}
function renderSession() {
  const session=state.session;if(!session)return;
  if(!session.queue.length){
    if(sessionIsDone(session)){
      if(!session.actions&&!session.allCards.length){renderEmptyDeck();return;}
      completeSession();return;
    }
    loadNextBatch(false);return;
  }
  const movie=currentCard();const nextMovie=session.queue[1]||null;
  const position=session.actions+1;const total=session.plannedTotal||session.limit;
  const percentage=Math.min(100,Math.round(session.actions/Math.max(1,total)*100));
  if(session.timedId!==movie.id){session.timedId=movie.id;session.cardShownAt=Date.now();session.detailsOpened=false;}   // замер времени и «открыл детали»
  const previous=session.reactions.slice(-4).reverse();
  $('#view').innerHTML=`<div class="session-screen"><div class="session-shell"><div class="session-main">
      <div class="session-topline"><div class="session-progress"><div class="progress-copy">Карточка <strong id="progPos">${position}</strong> из <strong id="progTotal">${total}</strong></div><div class="progress-track"><span id="progBar" style="width:${percentage}%"></span></div></div>
        <button class="btn-icon" data-action="undo" title="Отменить последний выбор" aria-label="Отменить последний выбор" ${session.actions?'' : 'disabled'}>${svg('undo')}</button>
        <button class="btn btn-quiet btn-small" data-action="finish-session">Завершить</button></div>
      <div class="swipe-stage" id="swipeStage">${nextMovie?`<article class="swipe-card-next" id="nextSwipeCard" aria-hidden="true">${swipeCardHTML(nextMovie,false)}</article>`:''}<article class="swipe-card" id="activeSwipeCard" data-movie-id="${esc(movie.id)}">${swipeCardHTML(movie,true)}</article></div>
      <div class="swipe-actions"><button class="swipe-action no" data-action="swipe-left" title="Не моё · ←" aria-label="Пропустить">${svg('close')}</button><button class="swipe-action watched" data-action="swipe-watched" title="Уже смотрел · ↑" aria-label="Уже смотрел">${svg('check')}</button><button class="swipe-action yes" data-action="swipe-right" title="Хочу посмотреть · →" aria-label="Хочу посмотреть">${svg('bookmark')}</button></div>
      <div class="keyboard-hint">Клавиши: <kbd>←</kbd> пропустить &nbsp; <kbd>↑</kbd> уже смотрел &nbsp; <kbd>→</kbd> сохранить &nbsp; <kbd>Пробел</kbd> подробнее</div>
    </div><aside class="session-aside"><h3>Ваши последние решения</h3><p>Здесь отображаются фильмы, на которые вы уже отреагировали.</p><div class="session-aside-list">${previous.length?previous.map(e=>`<div class="session-aside-item">${moviePoster(e.movie||{})}<span>${esc(e.movie?.title||'Фильм')}</span><strong style="margin-left:auto;color:${e.type==='right'?'#59866b':e.type==='left'?'#bd7669':'#65859a'}">${e.type==='right'?'♥':e.type==='left'?'×':'✓'}</strong></div>`).join(''):'<span class="small muted">Пока нет реакций.</span>'}</div><div class="keyboard-hint">Подборка сохраняется автоматически. Можно закрыть вкладку и вернуться позже.</div></aside></div></div>`;
  bindSwipeGesture();
  if(session.queue.length<=2&&!sessionIsDone(session)) loadNextBatch(true);
}
function updateProgressUI(){
  const s=state.session;if(!s)return;
  const total=s.plannedTotal||s.limit;
  const t=$('#progTotal');if(t)t.textContent=String(total);
  const bar=$('#progBar');if(bar)bar.style.width=Math.min(100,Math.round(s.actions/Math.max(1,total)*100))+'%';
  const stage=$('#swipeStage');
  if(stage&&$('#activeSwipeCard')&&s.queue[1]&&!$('#nextSwipeCard')){        // подгрузилась следующая — рисуем «стопку», не трогая активную карточку
    const art=document.createElement('article');art.className='swipe-card-next';art.id='nextSwipeCard';art.setAttribute('aria-hidden','true');
    art.innerHTML=swipeCardHTML(s.queue[1],false);stage.insertBefore(art,stage.firstChild);
  }
}
async function loadNextBatch(background=false){
  const s=state.session;
  if(!s||state.loadingMore||sessionIsDone(s))return;            // защита от параллельных вызовов
  state.loadingMore=true;
  if(!background)$('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Подбираем следующие карточки…</div>';
  let failed=null;
  try{
    const data=await api(`/sessions/${s.id}/next?n=5`);
    if(state.session!==s)return;
    s.queue.push(...data.cards);s.allCards.push(...data.cards);cacheMovies(data.cards);
    s.servedTotal=data.served_total;s.plannedTotal=data.planned_total;
    s.exhausted=!!data.exhausted||data.cards.length===0;          // пустая порция = карточки кончились (иначе вечный цикл)
  }catch(error){failed=error;console.warn('next batch',error);}
  finally{state.loadingMore=false;}
  if(state.session!==s)return;
  if(failed){
    if(!background)$('#view').innerHTML=emptyState('refresh','Не удалось загрузить карточки',failed.message,'Повторить','retry-next');
    return;
  }
  if(!s.queue.length||!background){if(state.page==='discover')renderSession();}
  else updateProgressUI();
}
function renderEmptyDeck(){
  const s=state.session;
  if(s&&!state.finishing){api(`/sessions/${s.id}/finish`,{method:'POST'}).catch(()=>{});}   // не оставляем пустую активную сессию
  api('/me/dashboard').then(d=>{state.dashboard=d;refreshIdentity();}).catch(()=>{});
  $('#view').innerHTML=emptyState('search','По заданным условиям фильмов не найдено','Попробуйте смягчить условия: увеличьте длительность, расширьте годы, снизьте минимальный рейтинг или выберите другой жанр.','Изменить условия','start-again');
}
const FLY={right:'translate3d(460px,25px,0) rotate(18deg)',left:'translate3d(-460px,25px,0) rotate(-18deg)',up:'translate3d(0,-520px,0) scale(.94)'};
const REST='translate3d(0,0,0) rotate(0deg)';
function setCardStamp(kind,opacity){['right','left','up'].forEach(k=>{const el=$('#stamp'+k[0].toUpperCase()+k.slice(1));if(el)el.style.opacity=(k===kind?opacity:0);});}
function setNextProgress(p){const n=$('#nextSwipeCard');if(n){n.style.transform=`scale(${.95+.05*p}) translateY(${10-10*p}px)`;n.style.opacity=String(.6+.4*p);}}
function resetCard(){const c=$('#activeSwipeCard');if(!c)return;c.classList.add('animating');c.style.transform=REST;c.style.opacity='1';setCardStamp(null,0);setNextProgress(0);}
function flyOut(action){
  const c=$('#activeSwipeCard');
  if(!c||!FLY[action]||matchMedia('(prefers-reduced-motion: reduce)').matches)return Promise.resolve();
  setCardStamp(action,1);setNextProgress(1);
  c.classList.add('animating');c.style.transform=FLY[action];c.style.opacity='0';
  return new Promise(r=>setTimeout(r,380));
}
function bindSwipeGesture(){
  const el=$('#activeSwipeCard');if(!el)return;
  let drag=null;
  el.addEventListener('pointerdown',e=>{
    if(state.swiping||(e.button!==undefined&&e.button!==0)||e.target.closest('button,a'))return;
    drag={id:e.pointerId,x:e.clientX,y:e.clientY,dx:0,dy:0,t:Date.now(),moved:false};
    el.classList.remove('animating');
  });
  el.addEventListener('pointermove',e=>{
    if(!drag||e.pointerId!==drag.id||state.swiping)return;
    drag.dx=e.clientX-drag.x;drag.dy=e.clientY-drag.y;
    if(!drag.moved){if(Math.hypot(drag.dx,drag.dy)<6)return;drag.moved=true;try{el.setPointerCapture(e.pointerId);}catch(_){}}
    const {dx,dy}=drag;
    el.style.transform=`translate3d(${dx}px,${dy}px,0) rotate(${dx*0.05}deg)`;
    setNextProgress(Math.min(1,Math.hypot(dx,dy)/130));
    if(dy<-40&&Math.abs(dy)>Math.abs(dx)*1.1)setCardStamp('up',Math.min(1,(Math.abs(dy)-35)/65));
    else if(dx>35)setCardStamp('right',Math.min(1,(dx-30)/70));
    else if(dx<-35)setCardStamp('left',Math.min(1,(Math.abs(dx)-30)/70));
    else setCardStamp(null,0);
  });
  const end=(e,cancel)=>{
    if(!drag||e.pointerId!==drag.id)return;
    const d=drag;drag=null;
    try{el.releasePointerCapture(e.pointerId);}catch(_){}
    if(cancel){resetCard();return;}
    if(!d.moved)return;                       // тап по карточке больше не открывает «Подробнее» (случайные срабатывания при свайпе)
    if(d.dy<-85&&Math.abs(d.dy)>Math.abs(d.dx)*1.05)performSwipe('up');
    else if(d.dx>85)performSwipe('right');
    else if(d.dx<-85)performSwipe('left');
    else resetCard();
  };
  el.addEventListener('pointerup',e=>end(e,false));
  el.addEventListener('pointercancel',e=>end(e,true));
}
function applySwipeToCollection(id,action){
  if(action==='right')mergeCollection(id,{in_watchlist:true,skipped:false});
  else if(action==='left')mergeCollection(id,{skipped:true,in_watchlist:false});
  else mergeCollection(id,{watched:true,skipped:false,in_watchlist:false});
}
async function performSwipe(action,rating=null){
  const s=state.session;if(!s||!s.queue.length||state.swiping)return false;
  state.swiping=true;
  const flight=flyOut(action);
  try{
    const movie=s.queue[0];
    const dwell=Math.max(0,Math.min(Date.now()-(s.cardShownAt||Date.now()),120000));
    try{await api(`/sessions/${s.id}/events`,{method:'POST',body:{events:[{event_id:crypto.randomUUID(),type:action,movie_id:Number(movie.id),rating,dwell_ms:Math.round(dwell),opened_details:!!s.detailsOpened}]}});}
    catch(error){
      resetCard();
      if(error.status===409||error.status===404){            // подборку закрыли в другой вкладке/на другом устройстве
        showToast('Эта подборка уже завершена. Начните новую.');
        state.session=null;state.dashboard=await api('/me/dashboard').catch(()=>state.dashboard);refreshIdentity();navigate('home');
        return false;
      }
      showToast('Выбор не сохранён: '+error.message);return false;
    }
    await flight;
    s.queue.shift();s.actions+=1;s.events.push({movie_id:String(movie.id),type:action,rating});s.reactions.push({movie_id:String(movie.id),type:action,rating,movie});
    applySwipeToCollection(movie.id,action);
    if(action==='up'&&rating==null)showToast('Отмечено как просмотренное',5200,{name:'rate-watched',id:movie.id,label:'Оценить'});
    if(s.queue.length)renderSession();else if(sessionIsDone(s))completeSession();else renderSession();
    if(state.dashboard)api('/me/dashboard').then(d=>{state.dashboard=d;refreshIdentity();}).catch(()=>{});
    return true;
  }finally{state.swiping=false;}
}

async function undoLast(){const s=state.session;if(!s||!s.actions)return;try{const result=await api(`/sessions/${s.id}/undo`,{method:'POST'});if(!result.movie_id){showToast('Больше нечего отменять');return;}const idx=s.reactions.map(x=>x.movie_id).lastIndexOf(String(result.movie_id));if(idx>=0){const [event]=s.reactions.splice(idx,1);s.events=s.events.filter((e,i)=>i!==idx);s.actions=Math.max(0,s.actions-1);const movie=event.movie||s.allCards.find(m=>String(m.id)===String(result.movie_id));if(movie)s.queue.unshift(movie);}if(state.dashboard)state.dashboard=await api('/me/dashboard').catch(()=>state.dashboard);refreshIdentity();renderSession();}catch(error){showToast('Не удалось отменить выбор: '+error.message);}}
async function completeSession(){
  const s=state.session;if(!s||state.finishing)return;
  state.finishing=true;
  try{await api(`/sessions/${s.id}/finish`,{method:'POST'});}
  catch(error){
    state.finishing=false;console.warn(error);
    showToast('Не удалось завершить подборку: '+error.message);
    if(!s.queue.length)$('#view').innerHTML=emptyState('refresh','Не удалось завершить подборку','Ваши реакции сохранены. Проверьте соединение и попробуйте ещё раз.','Повторить','retry-finish');
    return;
  }
  state.finishing=false;
  const d=await api('/me/dashboard').catch(()=>state.dashboard);state.dashboard=d;refreshIdentity();await renderResults();
}
function rememberResult(item){if(item?.movie){state.movieCache.set(String(item.movie.id),item.movie);setCollection(item.movie.id,item.collection||{});}}
function reasonsHTML(item){return (item.reasons||[]).length?`<ul class="reason-list">${item.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>`:'';}
function bestCardHTML(item){
  rememberResult(item);
  const m=item.movie,rating=m.kp??m.imdb,st=getCollectionState(m.id)||{};
  const meta=[m.type,m.year,m.duration,rating?'★ '+Number(rating).toFixed(1):''].filter(Boolean).map(esc).join(' · ');
  return `<article class="best-card" data-movie-card="${esc(m.id)}">
    <div class="best-poster" data-action="movie-details" data-id="${esc(m.id)}">${moviePoster(m,'',true)}</div>
    <div class="best-copy">
      <div class="best-badges"><span class="match-pill">${esc(item.match)}% совпадение</span>${item.saved?'<span class="saved-pill">Из вашего списка</span>':''}</div>
      <h3>${esc(m.title)}</h3><div class="best-meta">${meta}</div>
      ${reasonsHTML(item)}
      <p class="best-synopsis">${esc(m.shortHook||m.synopsis||'')}</p>
      <div class="best-actions"><button class="btn btn-primary" data-action="movie-details" data-id="${esc(m.id)}">Подробнее ${svg('chevron')}</button>
        <button class="btn-icon ${st.in_watchlist?'active':''}" data-action="toggle-watchlist" data-id="${esc(m.id)}" title="Хочу посмотреть" aria-label="Хочу посмотреть">${svg('bookmark')}</button>
        <button class="btn-icon ${st.watched?'active':''}" data-action="mark-watched" data-id="${esc(m.id)}" title="Уже смотрел" aria-label="Уже смотрел">${svg('check')}</button>
        <button class="btn-icon ${st.is_favorite?'active':''}" data-action="toggle-favorite" data-id="${esc(m.id)}" title="В избранное" aria-label="В избранное">${svg('heart')}</button></div>
    </div></article>`;
}
function recCardHTML(item){rememberResult(item);return `<div class="session-card-wrap">${renderMovieCard(item.movie)}<div class="match-line"><b>${esc(item.match)}%</b> ${esc((item.reasons||[])[0]||'совпадение с вашим вкусом')}</div></div>`;}
function resultSectionsHTML(r,{withSaved=true}={}){
  if(!r)return '';
  const sec=(title,sub,body)=>`<section class="section-block"><div class="section-heading"><div><h2>${title}</h2><p>${sub}</p></div></div>${body}</section>`;
  let html='';
  if(r.best)html+=sec('Лучшее совпадение','Фильм, который лучше всего подходит под ваши реакции.',bestCardHTML(r.best));
  if(r.alternatives?.length)html+=sec('Хорошие варианты','Следующие по совпадению — на случай, если лучший не подойдёт.',`<div class="result-grid">${r.alternatives.map(recCardHTML).join('')}</div>`);
  if(withSaved&&r.saved?.length){r.saved.forEach(rememberResult);html+=sec('Вы отобрали','Фильмы, которые вы сохранили в этой подборке.',`<div class="result-grid">${r.saved.map(x=>renderMovieCard(x.movie)).join('')}</div>`);}
  return html;
}
async function renderResults(){
  const s=state.session;if(!s)return;
  $('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Подводим итог…</div>';
  let r=null;
  try{r=await api(`/sessions/${s.id}/result`);}catch(error){console.warn('result',error);}
  if(state.session!==s)return;
  if(!r){$('#view').innerHTML=emptyState('refresh','Не удалось загрузить итог','Ваши реакции сохранены. Проверьте соединение и попробуйте ещё раз.','Повторить','retry-result');return;}
  const c=r.counts||{saved:0,watched:0,skipped:0};
  const note=r.ended_early?`Подходящих карточек больше нет: показали ${r.served_total} из ${s.limit}.`:`Вы ответили на ${r.answered} карточек — мы учли каждую реакцию.`;
  const badge=(icon,n,label)=>`<span class="stat-badge">${svg(icon)}<b>${n}</b><span>${label}</span></span>`;
  const empty=!r.best&&!r.saved?.length;
  $('#view').innerHTML=`<section class="results-hero"><div><div class="eyebrow">ПОДБОР ЗАВЕРШЁН</div><h2>${r.best?'Вот что стоит посмотреть':'Подходящих фильмов не нашлось'}</h2><p>${esc(note)}</p><div class="stat-badges">${badge('heart',c.saved,'в списке')}${badge('check',c.watched,'просмотрено')}${badge('close',c.skipped,'пропущено')}</div></div><button class="btn btn-primary" data-action="start-again">Новая подборка ${svg('arrow')}</button></section>
  ${empty?`<section class="section-block">${emptyState('search','Рекомендовать пока нечего','Попробуйте смягчить условия — расширить годы, снизить рейтинг или выбрать другой жанр.','','')}</section>`:resultSectionsHTML(r)}
  <section class="section-block"><div class="inline-note">Эта подборка сохранена в истории: там можно снова увидеть рекомендации и все ваши реакции.</div><div style="display:flex;gap:9px;margin-top:16px;flex-wrap:wrap"><button class="btn btn-quiet" data-page="history">История подборок</button></div></section>`;
  window.scrollTo({top:0});
}

async function fetchCollection(append=false){
  const params=new URLSearchParams({view:state.collectionView,limit:'60',offset:String(append?state.collectionItems.length:0)});
  if(state.collectionSearch)params.set('q',state.collectionSearch);
  if(state.collectionGenre)params.set('genre',state.collectionGenre);
  const result=await api(`/me/collection?${params}`);
  const items=result.items||[];
  state.collectionItems=append?[...state.collectionItems,...items]:items;
  state.collectionTotal=result.total??state.collectionItems.length;
  items.forEach(i=>(i.movie.genres||[]).forEach(g=>state.collectionGenreSet.add(g)));
  cacheMovies(items);
}
async function loadCollection(append=false){
  if(!append){state.page='collection';setNav('collection');$('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Открываем коллекцию…</div>';}
  try{
    await fetchCollection(append);
    const y=window.scrollY;renderCollection();if(append)window.scrollTo(0,y);
  }catch(error){
    if(append){showToast('Не удалось загрузить ещё: '+error.message);return;}
    $('#view').innerHTML=emptyState('library','Не удалось загрузить коллекцию',error.message,'Повторить','reload-collection');
  }
}
async function refreshCollectionResults(){      // поиск/фильтр/обновление: меняем только список, поле ввода остаётся в фокусе
  const req=++state.collectionReq;
  try{
    await fetchCollection(false);
    if(req!==state.collectionReq||state.page!=='collection')return;
    const box=$('#collectionResults');
    if(!box){renderCollection();return;}
    box.innerHTML=collectionResultsHTML();
    const cnt=$('#collectionCount');if(cnt)cnt.textContent=collectionCountLabel();
  }catch(error){if(req===state.collectionReq)showToast('Не удалось обновить список: '+error.message);}
}
function collectionCountLabel(){const count=state.collectionTotal||state.collectionItems.length;return `${count} ${count%10===1&&count%100!==11?'фильм':(count%10>=2&&count%10<=4&&(count%100<10||count%100>=20))?'фильма':'фильмов'}`;}
function collectionResultsHTML(){
  const count=state.collectionTotal||state.collectionItems.length;
  return count?`<div class="movie-grid">${state.collectionItems.map(item=>renderMovieCard(item.movie,item)).join('')}</div>${state.collectionItems.length<count?`<div class="load-more"><button class="btn btn-quiet" data-action="collection-more">Показать ещё (${count-state.collectionItems.length})</button></div>`:''}`:emptyState('bookmark','В этой вкладке пока пусто',collectionEmptyCopy(state.collectionView),'Подобрать фильм','go-discover');
}
function renderCollection(){const tabs=[['watchlist','Хочу посмотреть'],['favorites','Избранное'],['watched','Просмотрено'],['skipped','Пропущено'],['all','Всё']];const genreSet=[...state.collectionGenreSet].sort((a,b)=>a.localeCompare(b,'ru'));
  $('#view').innerHTML=`<div class="heading-row"><div><div class="eyebrow">ВАША ЛИЧНАЯ КИНОТЕКА</div><h1 class="page-title">Моя коллекция</h1><p class="page-subtitle">Сохраняйте интересное, отмечайте просмотренное и собирайте собственные киносписки.</p></div><div class="heading-actions"><button class="btn btn-quiet" data-action="export-data">${svg('download')} Экспорт</button><button class="btn btn-primary" data-action="go-discover">Найти фильм ${svg('arrow')}</button></div></div>
    <div class="tabs">${tabs.map(([key,label])=>`<button class="tab-btn ${state.collectionView===key?'active':''}" data-action="collection-tab" data-id="${key}">${label}</button>`).join('')}</div>
    <div class="filter-bar"><label class="search-box">${svg('search')}<input id="collectionSearch" type="search" value="${esc(state.collectionSearch)}" placeholder="Найти фильм в коллекции…"></label><select id="collectionGenre" class="select-field"><option value="">Все жанры</option>${genreSet.map(g=>`<option value="${esc(g)}" ${state.collectionGenre===g?'selected':''}>${esc(g)}</option>`).join('')}</select><span class="small muted" id="collectionCount">${collectionCountLabel()}</span></div>
    <div id="collectionResults">${collectionResultsHTML()}</div>`;
  const search=$('#collectionSearch');let timer=null;search?.addEventListener('input',()=>{clearTimeout(timer);state.collectionSearch=search.value;timer=setTimeout(refreshCollectionResults,300);});$('#collectionGenre')?.addEventListener('change',e=>{state.collectionGenre=e.target.value;refreshCollectionResults();});}
function collectionEmptyCopy(view){return ({favorites:'Отмечайте сердечком фильмы, которые особенно понравились.',watchlist:'Добавляйте интересные фильмы во время подбора, чтобы вернуться к ним позже.',watched:'Отмечайте уже просмотренные фильмы и ставьте им личные оценки.',skipped:'Пропущенные фильмы временно сохраняются здесь — их можно пересмотреть.',all:'Ваша личная коллекция появится здесь.'})[view]||'Здесь пока пусто.';}
function syncMovieButtons(id){
  const st=getCollectionState(id)||{};
  $$(`[data-movie-card="${CSS.escape(String(id))}"]`).forEach(card=>{
    const set=(action,on,labels)=>{const b=card.querySelector(`[data-action="${action}"]`);if(!b)return;b.classList.toggle('active',!!on);if(labels)b.setAttribute('aria-label',on?labels[0]:labels[1]);};
    set('toggle-favorite',st.is_favorite,['Убрать из избранного','В избранное']);
    set('toggle-watchlist',st.in_watchlist);
    set('mark-watched',st.watched);
  });
}
async function updateCollection(movieId,patch){
  try{
    const res=await api(`/me/collection/${movieId}`,{method:'PUT',body:patch});
    mergeCollection(movieId,res.item);syncMovieButtons(movieId);          // кнопки на любом экране берут состояние из одного места
    if(state.page==='collection')await refreshCollectionResults();
    else{state.dashboard=await api('/me/dashboard').catch(()=>state.dashboard);refreshIdentity();if(state.page==='home')renderHome();}
    showToast('Коллекция обновлена');
  }catch(error){showToast(error.message||'Не удалось обновить коллекцию');}
}
function getCollectionState(id){return state.collectionMap.get(String(id))||state.collectionItems.find(x=>String(x.movie?.id)===String(id))||state.dashboard?.recent?.find(x=>String(x.movie?.id)===String(id))||null;}
async function toggleFlag(id,key){const cur=getCollectionState(id)||{};await updateCollection(id,{[key]:!cur[key]});}

async function loadHistory(){state.page='history';setNav('history');$('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Загружаем историю…</div>';try{state.historyItems=await api('/me/sessions?limit=50');renderHistory();}catch(error){$('#view').innerHTML=emptyState('history','Не удалось загрузить историю',error.message,'Повторить','reload-history');}}
function renderHistory(){const items=state.historyItems||[];$('#view').innerHTML=`<div class="heading-row"><div><div class="eyebrow">ВАШ ПУТЬ В КИНО</div><h1 class="page-title">История подборок</h1><p class="page-subtitle">Возвращайтесь к прошлым решениям, просматривайте реакции и запускайте похожие подборки.</p></div><button class="btn btn-primary" data-action="go-discover">Новая подборка ${svg('arrow')}</button></div>${items.length?`<div class="history-list">${items.map(item=>{const date=new Date(item.started_at);return `<button class="history-item" data-action="session-detail" data-id="${esc(item.id)}"><span class="history-date"><strong>${date.getDate()}</strong><small>${date.toLocaleDateString('ru-RU',{month:'short'})}</small></span><span class="history-body"><span class="history-title">${item.surprise?'Удиви меня':'Подборка по настроению'}</span><span class="history-meta">${fmtDate(item.started_at)} · ${item.swiped} реакций · ${item.liked} сохранено · ${item.status==='active'?'В процессе':item.status==='finished'?'Завершена':'Прервана'}</span></span><span class="history-arrow">${svg('chevron')}</span></button>`;}).join('')}</div>`:emptyState('history','История пока пуста','Завершите первую подборку — и здесь появится её история.','Начать подбор','go-discover')}`;}
async function openSessionDetail(id){
  $('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Открываем подборку…</div>';
  try{
    const [detail,result]=await Promise.all([api(`/me/sessions/${id}`),api(`/sessions/${id}/result`).catch(()=>null)]);
    state.sessionDetail=detail;state.sessionResult=result;
    (detail.cards||[]).forEach(c=>{state.movieCache.set(String(c.movie.id),c.movie);setCollection(c.movie.id,c.collection||{});});
    renderSessionDetail();
  }catch(error){showToast(error.message);loadHistory();}
}
const REACTIONS={right:['right','♥ Хочу посмотреть'],left:['left','× Пропущен'],up:['up','✓ Просмотрено']};
function reactionBadge(item){const r=REACTIONS[item.action];if(!r)return '<span class="reaction-badge">Без реакции</span>';const stars=item.action==='up'&&item.rating?` · ★ ${item.rating}/5`:'';return `<span class="reaction-badge ${r[0]}">${r[1]}${stars}</span>`;}
function renderSessionDetail(){const d=state.sessionDetail;if(!d)return;const cards=d.cards||[];const count=cards.length;$('#view').innerHTML=`<div class="heading-row"><div><button class="text-link" data-action="back-history">← К истории</button><div class="eyebrow" style="margin-top:13px">АРХИВ ПОДБОРКИ</div><h1 class="page-title">${d.surprise?'Удиви меня':'Подборка по настроению'}</h1><p class="page-subtitle">${fmtDate(d.started_at)} · ${count} карточек · статус: ${d.status==='finished'?'завершена':d.status==='active'?'в процессе':'прервана'}</p></div><button class="btn btn-primary" data-action="repeat-session">Повторить подбор ${svg('refresh')}</button></div>${resultSectionsHTML(state.sessionResult,{withSaved:false})}<section class="section-block"><div class="section-heading"><div><h2>Все карточки подборки</h2><p>Ваши реакции на каждый фильм.</p></div></div><div class="movie-grid">${cards.map(item=>`<div class="session-card-wrap">${renderMovieCard(item.movie)}${reactionBadge(item)}</div>`).join('')}</div></section>`;}

async function renderProfile(){state.page='profile';setNav('profile');$('#view').innerHTML='<div class="loading-inline"><span class="loader"></span>Загружаем профиль…</div>';try{const [profile,dashboard,providers]=await Promise.all([api('/me/profile'),api('/me/dashboard'),api('/auth/providers')]);state.profile=profile;state.dashboard=dashboard;state.providers=providers;refreshIdentity();}catch(error){console.warn(error);}const p=state.profile||{display_name:'Киноман'};const connected=!!state.dashboard?.has_vk;
  $('#view').innerHTML=`<div class="heading-row"><div><div class="eyebrow">ВАШ АККАУНТ</div><h1 class="page-title">Профиль</h1><p class="page-subtitle">Настройки аккаунта и ваша история предпочтений.</p></div></div><div class="profile-layout"><section class="profile-card"><div class="profile-avatar-large">${p.avatar_url?`<img src="${esc(safeUrl(p.avatar_url))}" alt="">`:esc(getInitial(p.display_name))}</div><div><h2>${esc(p.display_name||'Киноман')}</h2><p>${connected?'Аккаунт связан с VK ID':'Гостевой аккаунт'}</p><span class="profile-chip">${connected?'СИНХРОНИЗАЦИЯ ВКЛЮЧЕНА':'ДАННЫЕ СОХРАНЯЮТСЯ В ЭТОМ БРАУЗЕРЕ'}</span></div></section><section class="panel"><div class="profile-form"><div><div class="eyebrow">ЛИЧНЫЕ ДАННЫЕ</div><h2 class="panel-title" style="margin-top:7px">Как к вам обращаться?</h2><p class="panel-subtitle">Имя отображается только в вашем профиле.</p></div><div class="field"><label for="profileName">Имя</label><input id="profileName" class="input-field" maxlength="80" value="${esc(p.display_name||'Киноман')}"></div><div><button class="btn btn-primary" data-action="save-profile">Сохранить изменения</button></div></div><div class="spacer"></div>${(connected||state.providers.vk)?`<div class="setting-row"><div><strong>${connected?'VK ID подключён':'Сохранить профиль через VK ID'}</strong><small>${connected?'Коллекция и история привязаны к вашему VK ID.':'После подключения можно открывать коллекцию с разных устройств.'}</small></div>${connected?'<span class="profile-chip" style="margin:0;background:#e8f0e9;color:#40745c">Подключён</span>':`<button class="btn btn-dark btn-small" data-action="vk-login">${svg('vk')} Войти через VK</button>`}</div>`:''}<div class="setting-row"><div><strong>Экспорт коллекции</strong><small>Скачать список фильмов и историю подборок в JSON.</small></div><button class="btn btn-quiet btn-small" data-action="export-data">${svg('download')} Скачать</button></div><div class="setting-row"><div><strong>Выйти из аккаунта</strong><small>${connected?'Вы сможете войти снова через VK ID.':'Гостевой профиль хранится только в этом браузере: после выхода вернуться к нему не получится.'}</small></div><button class="btn btn-quiet btn-small" data-action="logout">Выйти</button></div></section></div><section class="section-block"><div class="section-heading"><div><h2>Данные и приватность</h2><p>Вы контролируете свою коллекцию и историю.</p></div></div><div class="panel"><div class="setting-row"><div><strong>Очистить историю реакций</strong><small>Удалит историю лайков, пропусков и просмотренного, а также коллекцию.</small></div><button class="btn btn-danger btn-small" data-action="reset-history">Очистить данные</button></div><div class="inline-note">Swipe&Watch не публикует ваши списки автоматически. Для совместного использования в будущей версии будет отдельная настройка приватности.</div></div></section>`;
}
async function saveProfile(){const display_name=$('#profileName')?.value.trim();if(!display_name){showToast('Введите имя');return;}try{state.profile=await api('/me/profile',{method:'PATCH',body:{display_name}});state.dashboard=await api('/me/dashboard');refreshIdentity();showToast('Профиль сохранён');renderProfile();}catch(error){showToast(error.message);}}
async function startVkLogin(){try{const result=await api('/auth/vk/start');if(result.authorization_url)location.href=result.authorization_url;else showToast('VK ID не настроен');}catch(error){showToast(error.message);}}
async function fetchAllPages(path,pageSize,pick){
  const out=[];const sep=path.includes('?')?'&':'?';
  for(let offset=0,guard=0;guard<200;offset+=pageSize,guard++){
    const page=pick(await api(`${path}${sep}limit=${pageSize}&offset=${offset}`))||[];
    out.push(...page);if(page.length<pageSize)break;
  }
  return out;
}
async function exportData(){try{const [collection,historyRows,profile]=await Promise.all([fetchAllPages('/me/collection?view=all',200,r=>r.items),fetchAllPages('/me/sessions',100,r=>r),api('/me/profile')]);const payload={exported_at:new Date().toISOString(),profile,collection,sessions:historyRows};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='swipewatch-export.json';a.click();URL.revokeObjectURL(url);showToast('Экспорт подготовлен');}catch(error){showToast('Экспорт не удался: '+error.message);}}
async function resetHistory(){
  if(!(await confirmDialog({title:'Удалить все данные?',text:'Реакции и записи коллекции будут удалены без возможности восстановления.',okLabel:'Удалить',danger:true})))return;
  try{await api('/me/history',{method:'DELETE'});state.collectionMap.clear();state.dashboard=await api('/me/dashboard');refreshIdentity();showToast('Данные очищены');navigate('home');}catch(error){showToast(error.message);}
}
async function logout(){
  const guest=!state.dashboard?.has_vk;
  if(!(await confirmDialog({title:'Выйти из аккаунта?',text:guest?'Это гостевой профиль: он хранится только в этом браузере. После выхода его коллекция и история станут недоступны.':'Вы сможете снова войти через VK ID.',okLabel:'Выйти',danger:guest})))return;
  tokenStore.clear();state.token='';state.session=null;state.dashboard=null;state.profile=null;state.collectionMap.clear();state.collectionItems=[];state.historyItems=[];state.selectedGenres=new Set();
  await bootstrap();
}
function confirmDialog({title,text,okLabel='Подтвердить',cancelLabel='Отмена',danger=false}){
  return new Promise(resolve=>{
    closeModal();state.confirmResolve=resolve;
    $('#modalRoot').innerHTML=`<div class="modal-backdrop" data-action="close-modal"><section class="modal confirm-modal" role="alertdialog" aria-modal="true" aria-label="${esc(title)}"><h2 class="page-title" style="font-size:24px;margin-top:0">${esc(title)}</h2><p class="page-subtitle">${esc(text)}</p><div class="confirm-actions"><button class="btn btn-quiet" data-action="confirm-no">${esc(cancelLabel)}</button><button class="btn ${danger?'btn-danger':'btn-primary'}" data-action="confirm-yes">${esc(okLabel)}</button></div></section></div>`;
    $('[data-action="confirm-yes"]')?.focus();
  });
}
function settleConfirm(value){const r=state.confirmResolve;state.confirmResolve=null;$('#modalRoot').innerHTML='';if(r)r(value);}
function openMovieDetails(id){const movie=state.movieCache.get(String(id));if(movie&&state.session&&currentCard()&&String(currentCard().id)===String(id))state.session.detailsOpened=true;if(!movie){showToast('Не удалось найти карточку фильма');return;}state.detailMovie=movie;const host=$('#modalRoot');host.innerHTML=`<div class="modal-backdrop" data-action="close-modal"><section class="modal" role="dialog" aria-modal="true" aria-label="Информация о фильме"><button class="modal-close" data-action="close-modal">×</button><div class="movie-modal-layout"><div class="movie-modal-poster">${moviePoster(movie)}</div><div class="movie-modal-copy"><div class="eyebrow">${esc(movie.type||'ФИЛЬМ')} ${movie.year?`· ${esc(movie.year)}`:''}</div><h2>${esc(movie.title)}</h2><div class="movie-modal-meta">${esc(movie.originalTitle&&movie.originalTitle!==movie.title?movie.originalTitle:'')}${movie.duration?` · ${esc(movie.duration)}`:''}${movie.age?` · ${esc(movie.age)}`:''}</div><div class="movie-card-meta" style="margin-top:11px">${movie.kp?`<span class="movie-card-rating">★ КП ${Number(movie.kp).toFixed(1)}</span>`:''}${movie.imdb?`<span class="movie-card-rating">IMDb ${Number(movie.imdb).toFixed(1)}</span>`:''}</div><div class="swipe-tags" style="margin-top:12px">${(movie.genres||[]).map(g=>`<span style="background:#f0eee7;border-color:#e2ded5;color:#777">${esc(g)}</span>`).join('')}</div><p>${esc(movie.synopsis||movie.shortHook||'Описание пока отсутствует.')}</p>${myNoteBlock(movie)}<div class="modal-actions"><button class="btn btn-primary" data-action="detail-watchlist" data-id="${esc(movie.id)}">${svg('bookmark')} Хочу посмотреть</button><button class="btn btn-quiet" data-action="detail-favorite" data-id="${esc(movie.id)}">${svg('heart')} В избранное</button><button class="btn btn-quiet" data-action="detail-watched" data-id="${esc(movie.id)}">${svg('check')} Просмотрено</button></div>${movie.kinopoiskUrl&&safeUrl(movie.kinopoiskUrl)?`<a class="text-link" href="${esc(safeUrl(movie.kinopoiskUrl))}" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:16px">Открыть на Кинопоиске ↗</a>`:''}</div></div></section></div>`;}
function myNoteBlock(movie){
  const item=getCollectionState(movie.id)||{};const cur=item.rating?Math.round(item.rating/2):0;
  return `<div class="my-note"><h4>Моя оценка и заметка</h4><div class="rating-stars" id="myRatingStars" data-rating="${cur}">${[1,2,3,4,5].map(n=>`<button data-action="my-rating" data-id="${n}" class="${n<=cur?'active':''}" aria-label="${n} из 5">★</button>`).join('')}</div><textarea id="movieNote" maxlength="2000" placeholder="Заметка о фильме…" data-initial="${esc(item.note||'')}">${esc(item.note||'')}</textarea><button class="btn btn-quiet btn-small" data-action="save-note" data-id="${esc(movie.id)}" style="margin-top:10px">Сохранить</button></div>`;
}
async function saveMyNote(id){
  const box=$('#movieNote');if(!box)return;const item=getCollectionState(id);const patch={};
  const text=box.value.trim();if(text!==(box.dataset.initial||'').trim())patch.note=text||null;
  const stars=Number($('#myRatingStars')?.dataset.rating||0);if(stars&&stars!==Math.round((item?.rating||0)/2))patch.rating=stars*2;
  if(!Object.keys(patch).length){closeModal();return;}
  try{
    await api(`/me/collection/${id}`,{method:'PUT',body:patch});closeModal();showToast('Сохранено');
    if(state.page==='collection')await loadCollection();
    else{state.dashboard=await api('/me/dashboard').catch(()=>state.dashboard);refreshIdentity();if(state.page==='home')renderHome();}
  }catch(error){showToast(error.message||'Не удалось сохранить');}
}
function closeModal(){ if(state.confirmResolve){settleConfirm(false);return;} $('#modalRoot').innerHTML='';state.detailMovie=null;state.pendingRatingMovie=null; }
function showRatingModal(movie){
  if(!movie)return;state.pendingRatingMovie=movie;
  $('#modalRoot').innerHTML=`<div class="modal-backdrop" data-action="close-modal"><section class="modal rating-modal" role="dialog" aria-modal="true"><button class="modal-close" data-action="close-modal" aria-label="Закрыть">×</button><div class="eyebrow">ВАША ОЦЕНКА</div><h2 class="page-title" style="font-size:26px">${esc(movie.title)}</h2><p class="page-subtitle">Оценка необязательна, но помогает точнее подбирать фильмы.</p><div class="rating-stars" id="ratingStars">${[1,2,3,4,5].map(n=>`<button data-action="choose-rating" data-id="${n}" aria-label="${n} из 5">★</button>`).join('')}</div><button class="btn btn-primary" id="submitRating" data-action="submit-rating" disabled>Сохранить оценку</button><button class="text-link" data-action="close-modal" style="display:block;margin:12px auto 0">Не сейчас</button></section></div>`;
}
async function rateWatched(id,stars){
  try{const res=await api(`/me/collection/${id}`,{method:'PUT',body:{rating:stars*2}});mergeCollection(id,res.item);showToast('Оценка сохранена');return true;}
  catch(error){showToast(error.message||'Не удалось сохранить оценку');return false;}
}
async function handleAction(button){const action=button.dataset.action;const id=button.dataset.id;
  if(action==='go-discover'){state.session=null;navigate('discover');}
  else if(action==='surprise'){state.session=null;await startSession(true);}
  else if(action==='mood'){state.selectedGenres=new Set([id]);navigate('discover');}
  else if(action==='toggle-genre'){state.selectedGenres.has(id)?state.selectedGenres.delete(id):state.selectedGenres.add(id);renderDiscover();}
  else if(action==='set-limit'){state.sessionLimit=Number(id);renderDiscover();}
  else if(action==='start-session')await startSession(false);
  else if(action==='resume-session')await resumeSession();
  else if(action==='swipe-left')await performSwipe('left');
  else if(action==='swipe-right')await performSwipe('right');
  else if(action==='swipe-watched')await performSwipe('up');
  else if(action==='rate-watched')showRatingModal(state.movieCache.get(String(id)));
  else if(action==='retry-next')await loadNextBatch(false);
  else if(action==='retry-result')await renderResults();
  else if(action==='logout')await logout();
  else if(action==='confirm-yes')settleConfirm(true);
  else if(action==='confirm-no')settleConfirm(false);
  else if(action==='undo')await undoLast();
  else if(action==='retry-finish')await completeSession();
  else if(action==='finish-session'){if(await confirmDialog({title:'Завершить подборку?',text:'Мы покажем итог по тому, что вы уже отметили.',okLabel:'Завершить'}))await completeSession();}
  else if(action==='start-again'){state.session=null;navigate('discover');}
  else if(action==='collection-tab'){state.collectionView=id;await loadCollection();}
  else if(action==='collection-more')await loadCollection(true);
  else if(action==='movie-details')openMovieDetails(id);
  else if(action==='toggle-favorite')await toggleFlag(id,'is_favorite');
  else if(action==='toggle-watchlist')await toggleFlag(id,'in_watchlist');
  else if(action==='mark-watched')await toggleFlag(id,'watched');
  else if(action==='detail-watchlist'){await updateCollection(id,{in_watchlist:true});closeModal();}
  else if(action==='detail-favorite'){await updateCollection(id,{is_favorite:true});closeModal();}
  else if(action==='detail-watched'){await updateCollection(id,{watched:true});closeModal();}
  else if(action==='close-modal')closeModal();
  else if(action==='my-rating'){const box=$('#myRatingStars');if(box){box.dataset.rating=id;$$('#myRatingStars button').forEach(b=>b.classList.toggle('active',Number(b.dataset.id)<=Number(id)));}}
  else if(action==='save-note')await saveMyNote(id);
  else if(action==='choose-rating'){ $$('#ratingStars button').forEach(b=>b.classList.toggle('active',Number(b.dataset.id)<=Number(id)));$('#submitRating').disabled=false;$('#submitRating').dataset.rating=id; }
  else if(action==='submit-rating'){const n=Number($('#submitRating')?.dataset.rating||0);const m=state.pendingRatingMovie;if(n&&m&&await rateWatched(m.id,n))closeModal();}
  else if(action==='save-profile')await saveProfile();
  else if(action==='vk-login')await startVkLogin();
  else if(action==='export-data')await exportData();
  else if(action==='reset-history')await resetHistory();
  else if(action==='session-detail')await openSessionDetail(id);
  else if(action==='back-history')navigate('history');
  else if(action==='repeat-session'){
    const d=state.sessionDetail;const used=new Set(d.initial_genres||[]);
    state.selectedGenres=new Set(GENRE_OPTIONS.filter(g=>g.genres.every(x=>used.has(x))).map(g=>g.id));
    state.sessionLimit=[10,15,20].includes(d.limit)?d.limit:15;
    state.filterDefaults={...EMPTY_FILTERS,...(d.filters||{})};
    state.session=null;
    if(d.surprise){await startSession(true,{content_type:'all',...(d.filters||{})});}else navigate('discover');
  }
  else if(action==='retry')bootstrap();
  else if(action==='reload-collection')loadCollection();
  else if(action==='reload-history')loadHistory();
}

document.querySelector('.brand')?.addEventListener('click', event=>{event.preventDefault();navigate('home');});
document.addEventListener('click',event=>{
  const pageButton=event.target.closest('[data-page]');
  if(pageButton){event.preventDefault();navigate(pageButton.dataset.page);return;}
  const button=event.target.closest('[data-action]');
  if(button){
    if(button.classList.contains('modal-backdrop') && event.target.closest('.modal')) return;
    event.preventDefault();handleAction(button);return;
  }
});

document.addEventListener('change',event=>{
  const keys={filterType:'content_type',filterDuration:'max_duration',filterYearFrom:'year_from',filterYearTo:'year_to',filterRating:'min_rating',filterAge:'max_age'};
  const key=keys[event.target.id];if(key)state.filterDefaults[key]=event.target.value===''?'':(key==='content_type'?event.target.value:Number(event.target.value));
});
document.addEventListener('input',event=>{
  const keys={filterYearFrom:'year_from',filterYearTo:'year_to'};const key=keys[event.target.id];
  if(key){state.filterDefaults[key]=event.target.value;const f={};['filterYearFrom','filterYearTo'].forEach((id,i)=>{const v=$('#'+id)?.value;if(v)f[i?'year_to':'year_from']=Number(v);});showFilterError(validateFilters(f));}
});

document.addEventListener('keydown',event=>{
  if(event.key==='Escape'){closeModal();return;}
  if(state.page!=='discover'||!state.session||$('#modalRoot').innerHTML)return;
  if(event.key==='ArrowLeft'){event.preventDefault();performSwipe('left');}
  else if(event.key==='ArrowRight'){event.preventDefault();performSwipe('right');}
  else if(event.key==='ArrowUp'){event.preventDefault();performSwipe('up');}
  else if(event.code==='Space' && currentCard()){event.preventDefault();openMovieDetails(currentCard().id);}
});

new MutationObserver(()=>document.body.classList.toggle('in-session',!!document.querySelector('#view .session-screen'))).observe($('#view'),{childList:true});
bootstrap();
