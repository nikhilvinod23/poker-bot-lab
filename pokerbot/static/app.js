const $=s=>document.querySelector(s);let game=null,bots=['easy'],busy=false,timer=null;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url,body){const r=await fetch(url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');return d}
function error(e){$('#error').textContent=e.message}
function setup(){ $('#bots').innerHTML=bots.map((d,i)=>`<div class="bot"><span>BOT ${i+1}</span><select aria-label="Bot ${i+1} difficulty" data-bot="${i}"><option value="easy" ${d==='easy'?'selected':''}>EASY</option><option value="intermediate" ${d==='intermediate'?'selected':''}>INTERMEDIATE</option></select><button data-remove="${i}" aria-label="Remove bot ${i+1}">×</button></div>`).join('');$('#add').disabled=bots.length>=5;}
$('#bots').onchange=e=>{if(e.target.dataset.bot!==undefined)bots[+e.target.dataset.bot]=e.target.value};$('#bots').onclick=e=>{if(e.target.dataset.remove!==undefined){bots.splice(+e.target.dataset.remove,1);setup()}};$('#add').onclick=()=>{bots.push('easy');setup()};
$('#start').onclick=async()=>{try{if(busy)return;busy=true;game=await api('/api/games',{human:$('#human').checked,bots,rounds:Number($('#rounds').value),small_blind:Number($('#smallblind').value),big_blind:Number($('#bigblind').value),starting_chips:Number($('#startingchips').value)});localStorage.setItem('holdem-game',game.id);render()}catch(e){error(e)}finally{busy=false;schedule()}};
function face(c){return c==='??'?'??':(c[0]==='T'?'10':c[0])+({c:'♣',d:'♦',h:'♥',s:'♠'}[c[1]]||'');}
function card(c){const hidden=c==='??',rank=hidden?'?':c[0]==='T'?'10':c[0],suit=hidden?'?':{c:'♣',d:'♦',h:'♥',s:'♠'}[c[1]];return `<span class="card ${!hidden&&'dh'.includes(c[1])?'red':''}">+-----+\n|${rank.padEnd(5)}|\n|  ${suit}  |\n|${rank.padStart(5)}|\n+-----+</span>`;}
function render(){if(!game)return;$('#setup').hidden=true;$('#game').hidden=false;$('#error').textContent='';$('#round').textContent=`HAND ${String(game.hand).padStart(2,'0')} / ${String(game.limit).padStart(2,'0')}`;$('#street').textContent=game.ended?'FINISHED':['PREFLOP','FLOP','TURN','RIVER'][game.street];$('#pot').textContent=`POT / ${game.pot}`;$('#board').innerHTML=game.board.map(card).join('');$('#seats').className='n'+game.seats.length;$('#seats').innerHTML=game.seats.map((s,i)=>`<div class="seat ${game.current===i?'active':''} ${s.chips===0&&!s.live?'out':''}"><div class="name">${esc(s.name)} ${i===game.dealer?'[D]':''} ${i===game.sb?'[SB]':''} ${i===game.bb?'[BB]':''}</div><div class="chips">${s.chips}</div><div class="tag">${s.kind==='bot'?s.difficulty.toUpperCase():'HUMAN'} ${s.live&&s.chips===0?' / ALL IN':''} ${!s.live?' / OUT':s.bet?' / BET '+s.bet:''}</div><div class="cards">${s.cards.map(card).join('')}</div></div>`).join('');$('#outcome').textContent=game.hand_done?(game.ended?game.reason.toUpperCase():'HAND COMPLETE'):'';let actions=[];if(game.ended)actions=[['new','NEW TABLE'],['export','SAVE LOG ↓']];else if(game.hand_done)actions=[['next','NEXT HAND →'],['vote','END BY AGREEMENT']];else if(game.seats[game.current].kind==='human')actions=game.legal.map(a=>[a,a==='call'?`CALL ${game.to_call}`:a==='raise'?'BET / RAISE':a.toUpperCase()]);$('#actions').innerHTML=actions.map(([a,t])=>`<button data-action="${a}" ${a==='raise'||a==='next'?'class="primary"':''}>${t}</button>`).join('');$('#status').textContent=game.ended?'SCORES SAVED':game.hand_done?'':'TURN / '+game.seats[game.current].name;$('#stats').hidden=!game.ended;if(game.ended)$('#stats').innerHTML=`<table><thead><tr><th>PLAYER</th><th>CHIPS</th><th>NET</th><th>HANDS</th><th>WON</th></tr></thead><tbody>${game.seats.map(s=>`<tr><td>${esc(s.name)}</td><td>${s.chips}</td><td>${s.chips-(game.setup.starting_chips||100)}</td><td>${s.played}</td><td>${s.won}</td></tr>`).join('')}</tbody></table><button id="fullhistory">DEALT CARDS / HAND HISTORY [+]</button>`;$('#reset').disabled=game.ended;}
function schedule(){clearTimeout(timer);if(game&&!game.ended&&!game.hand_done&&game.seats[game.current].kind==='bot')timer=setTimeout(()=>act('tick'),650)}
async function act(action){if(busy)return;if(action==='new'){forgetGame();return}if(action==='export'){const data=await api(`/api/games/${game.id}/export`);const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download=`holdem-${game.id}.json`;a.click();URL.revokeObjectURL(a.href);return}busy=true;clearTimeout(timer);try{game=await api(`/api/games/${game.id}/action`,{action,version:game.version,amount:action==='raise'?Number($('#betamount').value):null});render()}catch(e){try{game=await api(`/api/games/${game.id}`);render()}catch{}error(e)}finally{busy=false;schedule()}}
$('#actions').onclick=e=>{if(e.target.dataset.action)act(e.target.dataset.action)};$('#reset').onclick=()=>act('reset');$('#close').onclick=()=>$('#drawer').close();
function modal(title,content){$('#logtitle').textContent=title;$('#logbody').innerHTML=content;$('#drawer').showModal()}
$('#log').onclick=()=>modal('ACTION LOG',game.events.map(e=>esc(`H${e.hand} / ${e.kind.toUpperCase()} ${e.seat!==undefined?' / '+game.seats[e.seat].name:''} ${e.action||''} ${e.paid!==undefined?'+'+e.paid:''} ${e.kind==='board'?e.cards||'':''} ${e.awards?'AWARDS '+e.awards.join(' / '):''}`)).join('\n'));
$('#stats').onclick=async e=>{if(e.target.id==='fullhistory'){try{const d=await api(`/api/games/${game.id}/export`);modal('HAND HISTORY',`<p>${when(d.setup.started_local||d.setup.started_utc||d.setup.started_cst)}</p>`+d.hands.map(h=>`<details><summary>HAND ${h.hand} / ${h.board.join(' ')}</summary><pre>${esc(JSON.stringify(h,null,2))}</pre></details>`).join(''))}catch(e){error(e)}}};
$('#history').onclick=async()=>{try{const rows=await api('/api/games');modal('SAVED GAMES',rows.map(r=>`<details><summary>${esc(r.setup.started_cst.slice(0,19).replace('T',' '))} CST / ${r.hand} HANDS / ${esc(r.reason||'ACTIVE')}</summary><p>${r.setup.bots.map(esc).join(' / ')}${r.setup.human?' / HUMAN':''}</p><button data-open="${r.id}">${r.ended?'VIEW RESULTS':'RESUME'}</button></details>`).join('')||'NO GAMES YET')}catch(e){error(e)}};
$('#logbody').onclick=async e=>{if(e.target.dataset.open){try{clearTimeout(timer);game=await api(`/api/games/${e.target.dataset.open}`);localStorage.setItem('holdem-game',game.id);$('#drawer').close();render();schedule()}catch(e){error(e)}}};
setup();(async()=>{const id=localStorage.getItem('holdem-game');if(id)try{game=await api(`/api/games/${id}`);render();schedule()}catch(e){localStorage.removeItem('holdem-game')}})();


const baseRender=render;
function eventText(e,seats){
 const who=p=>seats[p]?.name||`SEAT ${Number(p)+1}`;
 if(e.kind==='deal')return `HAND ${e.hand} / ${who(e.dealer)} DEALER / ${who(e.small_blind)} SB ${e.small_blind_amount||1} / ${who(e.big_blind)} BB ${e.big_blind_amount||2}`;
 if(e.kind==='action')return `${who(e.seat)} ${e.action.toUpperCase()}${e.raise_by?` BY ${e.raise_by} / TO ${e.to}`:''}${e.paid?` / PAID ${e.paid}`:''}${e.all_in?' / ALL IN':''}`;
 if(e.kind==='board')return `BOARD / ${e.cards.map(face).join(' ')}`;
 if(e.kind==='settlement')return `HANDS / ${Object.entries(e.hand_types||{}).map(([p,h])=>who(p)+': '+h.label).join(' / ')}\n${(e.pots||[]).map(pot=>pot.name+' '+pot.amount+(pot.refund?'':' ['+pot.eligible.map(who).join(', ')+']')+' → '+Object.entries(pot.awards||{}).map(([p,v])=>who(p)+' +'+v).join(', ')).join('\n')}\nPAYOUT / ${e.awards.map((v,p)=>v?who(p)+' +'+v:'').filter(Boolean).join(' / ')}`;
 if(e.kind==='void_hand')return 'HAND VOID / CHIPS REFUNDED';
 if(e.kind==='end')return `END / ${e.reason}`;
 if(e.kind==='unanimous_vote')return 'ALL REMAINING SEATS AGREE TO END';
 return '';
}
render=function(){
 baseRender();
 if(!game)return;
 const last={};game.events.filter(e=>e.kind==='action').forEach(e=>last[e.seat]=e);
 document.querySelectorAll('.seat').forEach((el,p)=>{const e=last[p];if(e&&e.hand===game.hand)el.insertAdjacentHTML('beforeend',`<div class="last-action">${esc(e.action.toUpperCase())}${e.paid?' +'+e.paid:''}</div>`)});
 if(game.legal.includes('raise')&&!game.hand_done&&game.seats[game.current].kind==='human'){
  $('#actions').insertAdjacentHTML('afterbegin',`<label class="bet-input">${game.to_call?'RAISE BY':'BET'} <input aria-label="Bet or raise increment" id="betamount" type="number" step="1" min="${game.raise_min}" max="${game.raise_max}" value="${game.raise_min}"><small>${game.raise_min}–${game.raise_max}${game.to_call?' + CALL '+game.to_call:''}</small></label>`);
 }
 const meta=game.setup;
 updateFeed(meta);
 $('#log').hidden=true;
 const latest=game.events.filter(e=>e.kind==='action').at(-1);
 if(latest)$('#outcome').textContent=eventText(latest,game.seats);
};
schedule=function(){clearTimeout(timer);if(game&&!game.ended&&!game.hand_done&&game.seats[game.current].kind==='bot'){
 $('#status').textContent=game.seats[game.current].name+' / THINKING…';
 timer=setTimeout(()=>act('tick'),Number($('#botdelay').value)*1000);
}};
async function showArchive(id){
 try{const d=await api(`/api/games/${id}/export`);
 modal(d.setup.title||'GAME',`<p>${when(d.setup.started_local||d.setup.started_utc||d.setup.started_cst)}</p><p>${esc(d.reason)} / ${d.hands.length} HANDS / BLINDS ${d.setup.small_blind}:${d.setup.big_blind}</p><p>${d.seats.map(s=>esc(s.name)+' '+s.chips+' ('+(s.chips-(d.setup.starting_chips||100))+')').join(' / ')}</p>`+d.hands.map(h=>`<details><summary>HAND ${h.hand}${h.void?' / VOID':''} / ${h.board.map(face).join(' ')}</summary><p>${Object.entries(h.cards).map(([p,c])=>esc(d.seats[p].name)+': '+c.map(face).join(' ')+' / '+esc(h.hand_types?.[p]?.label||'Not evaluated')).join('<br>')}</p><div>${d.events.filter(e=>e.hand===h.hand).map(e=>esc(eventText(e,d.seats))).join('<br>')}</div></details>`).join(''));
 }catch(e){error(e)}
}
$('#stats').onclick=e=>{if(e.target.id==='fullhistory')showArchive(game.id)};
$('#history').onclick=async()=>{try{const rows=await api('/api/games');modal('SAVED GAMES',rows.map(r=>`<details><summary>GAME ${r.id.slice(0,8).toUpperCase()} / ${esc(r.setup.started_cst.slice(0,19).replace('T',' '))} CST</summary><p>${r.setup.bots.map(esc).join(' / ')}${r.setup.human?' / HUMAN':''}<br>${r.hand} / ${r.setup.rounds} HANDS · ${esc(r.reason||'ACTIVE')}</p><button ${r.ended?'data-archive':'data-open'}="${r.id}">${r.ended?'HANDS / ACTIONS / CARDS':'RESUME GAME'}</button></details>`).join('')||'NO GAMES YET')}catch(e){error(e)}};
const previousLogClick=$('#logbody').onclick;
$('#logbody').onclick=e=>{if(e.target.dataset.archive)showArchive(e.target.dataset.archive);else previousLogClick(e)};

function when(value){return value?esc(new Date(value).toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'})):'';}
function clock(value){return value?new Date(value).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';}
const numberedRender=render;
render=function(){numberedRender();if(game){document.querySelector('header > span').textContent=game.setup.title||'HOLD’EM';document.title=(game.setup.title||'HOLD’EM')+' / ASCII';}};
async function listGames(){try{const rows=await api('/api/games');modal('SAVED GAMES',`<button id="clearall" ${rows.length?'':'disabled'}>CLEAR ALL LOGS</button>`+rows.map(r=>`<details><summary>${esc(r.setup.title||'GAME')} / ${when(r.setup.started_local||r.setup.started_utc||r.setup.started_cst)}</summary><p>ID ${esc(r.id)}<br>${r.setup.bots.map(esc).join(' / ')}${r.setup.human?' / HUMAN':''}<br>${r.hand} / ${r.setup.rounds} HANDS · ${esc(r.reason||'ACTIVE')}</p><button ${r.ended?'data-archive':'data-open'}="${r.id}">${r.ended?'HANDS / ACTIONS / CARDS':'RESUME GAME'}</button> <button data-delete="${r.id}">CLEAR THIS LOG</button></details>`).join('')+(rows.length?'':'<p>NO GAMES YET</p>'))}catch(e){error(e)}}
$('#history').onclick=listGames;
const savedLogClick=$('#logbody').onclick;
function forgetGame(){clearTimeout(timer);game=null;localStorage.removeItem('holdem-game');$('#game').hidden=true;$('#setup').hidden=false;document.querySelector('header > span').textContent="HOLD’EM";document.title="HOLD’EM / ASCII";}
$('#logbody').onclick=async e=>{
 if(e.target.id==='clearall'||e.target.dataset.delete){
  const all=e.target.id==='clearall',id=e.target.dataset.delete;
  if(!confirm(all?'Delete all saved games? Numbering will restart at Game 1.':'Delete this saved game?'))return;
  try{const r=await fetch('/api/games'+(all?'':'/'+id),{method:'DELETE'});if(!r.ok)throw Error('Could not clear logs');if(all||game?.id===id)forgetGame();await listGames()}catch(e){error(e)}
 }else savedLogClick(e);
};
window.addEventListener('storage',e=>{if(e.key==='holdem-game'&&!e.newValue)forgetGame()});

function updateFeed(meta){
 let feed=$('#feed');
 if(!feed||feed.dataset.game!==game.id){$('#publiclog').innerHTML='<h2 id="logheading"></h2><p id="logmeta" class="small"></p><div id="feed" role="log" aria-live="polite"></div>';feed=$('#feed');feed.dataset.game=game.id;feed.dataset.count='0'}
 $('#logheading').textContent=(meta.title||'GAME')+' / PUBLIC LOG';
 $('#logmeta').innerHTML=`${when(meta.started_local||meta.started_utc||meta.started_cst)}<br>BLINDS ${meta.small_blind} / ${meta.big_blind}<br>${game.seats.length} SEATS · ${game.limit} HANDS`;
 const atBottom=feed.scrollHeight-feed.scrollTop-feed.clientHeight<24;
 const count=Number(feed.dataset.count||0);
 game.events.slice(count).forEach(e=>{const node=document.createElement('div');node.className='feed-event '+(e.kind==='action'?'decision':'');const time=document.createElement('small');time.textContent='H'+e.hand+' / '+clock(e.time_local||e.time_cst);const text=document.createElement('p');text.textContent=eventText(e,game.seats);node.append(time,text);feed.append(node)});
 feed.dataset.count=String(game.events.length);
 if(atBottom)feed.scrollTop=feed.scrollHeight;
}
const preferenceFields=['rounds','smallblind','bigblind','startingchips','botdelay'];
try{const prefs=JSON.parse(localStorage.getItem('holdem-settings')||'{}');preferenceFields.forEach(id=>{if(prefs[id]!==undefined)$('#'+id).value=prefs[id]})}catch{}
function settingsSummary(){$('#setupsummary').textContent=`${$('#rounds').value} HANDS / ${$('#startingchips').value} CHIPS / BLINDS ${$('#smallblind').value} : ${$('#bigblind').value}`}
settingsSummary();
$('#settings').onclick=()=>{$('#rulesettings').disabled=!!game&&!game.ended;$('#settingserror').textContent='';$('#settingspanel').showModal()};
$('#settingsclose').onclick=()=>$('#settingspanel').close();
$('#settingsform').onsubmit=e=>{e.preventDefault();if(!(Number($('#smallblind').value)<Number($('#bigblind').value)&&Number($('#bigblind').value)<=Number($('#startingchips').value))){$('#settingserror').textContent='Require small blind < big blind ≤ starting chips';return}localStorage.setItem('holdem-settings',JSON.stringify(Object.fromEntries(preferenceFields.map(id=>[id,$('#'+id).value]))));settingsSummary();$('#settingspanel').close();schedule()};

let settingsBeforeOpen;
const openSettings=$('#settings').onclick;
$('#settings').onclick=()=>{settingsBeforeOpen=Object.fromEntries(preferenceFields.map(id=>[id,$('#'+id).value]));openSettings()};
$('#settingsclose').onclick=()=>{if(settingsBeforeOpen)preferenceFields.forEach(id=>$('#'+id).value=settingsBeforeOpen[id]);$('#settingspanel').close()};

const potRender=render;
render=function(){potRender();if(!game)return;document.querySelector('.pot-breakdown')?.remove();if(game.pots?.length>1&&(game.hand_done||game.seats.some(s=>s.live&&s.chips===0))){const row=document.createElement('div');row.className='pot-breakdown';row.textContent=game.pots.map(p=>p.name+' / '+p.amount).join(' · ');$('#pot').after(row)}};
