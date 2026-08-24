/* ── 즉시 실행: 레이아웃 교정 (gen.py 재배포 없이도 동작) ── */
(function(){
  // 1) AEO 안내 블록을 '최신 일정' 섹션 뒤로 이동
  try{
    var main=document.querySelector('main');
    var aeoSec=null, schedSec=null, secs=main? main.children : [];
    for(var i=0;i<secs.length;i++){
      var sec=secs[i];
      if(!aeoSec && sec.querySelector && sec.querySelector('.aeo')) aeoSec=sec;
      if(!schedSec && sec.querySelector && sec.querySelector('#event-cards')) schedSec=sec;
    }
    if(aeoSec && schedSec && aeoSec.compareDocumentPosition(schedSec) & Node.DOCUMENT_POSITION_FOLLOWING){
      schedSec.parentNode.insertBefore(aeoSec, schedSec.nextSibling);
    }
  }catch(e){}
  // 2) '자세히 보기' 버튼 스타일 주입
  try{
    var st=document.createElement('style');
    st.textContent='.card .detail{display:block;text-align:center;margin-top:9px;padding:9px;'
      +'font-size:13px;font-weight:600;color:#5f6672;border:1px solid #e6e8ec;border-radius:7px;'
      +'transition:.16s}.card .detail:hover{color:#12233d;border-color:#12233d;background:#f6f7f9}';
    document.head.appendChild(st);
  }catch(e){}
})();

/* 정적 카드가 이미 렌더돼 있음. 이 스크립트는 방문자에게 "빌드 이후 추가된 일정"을 보강한다.
   - 시트1(replyalba) + 수동추가(cpaad) 두 탭을 모두 읽어 병합
   - 정적 카드보다 결과가 적으면 덮어쓰지 않음 (SEO 콘텐츠 보호) */
(function(){
  var box=document.getElementById('event-cards');
  if(!box) return;
  var SHEET='1R_lX8DcKXiHX50SuHrpLCgn1AhTqduAmEl_YhuhLnPI';
  var staticCount=box.querySelectorAll('.card').length;
  var cities=(box.getAttribute('data-cities')||'').split(',').map(function(s){return s.trim();}).filter(Boolean);
  var multi=cities.length>1, cset={}; cities.forEach(function(c){cset[c]=1;});

  function url(tab){
    var u='https://docs.google.com/spreadsheets/d/'+SHEET+'/gviz/tq?tqx=out:csv&t='+Date.now();
    return tab? u+'&sheet='+encodeURIComponent(tab) : u;
  }
  function parseCSV(t){var rows=[],row=[],cur='',q=false;
    for(var i=0;i<t.length;i++){var c=t[i];
      if(q){ if(c=='"'){ if(t[i+1]=='"'){cur+='"';i++;} else q=false; } else cur+=c; }
      else { if(c=='"')q=true; else if(c==','){row.push(cur);cur='';}
        else if(c=='\n'){row.push(cur);rows.push(row);row=[];cur='';}
        else if(c=='\r'){} else cur+=c; }}
    if(cur!==''||row.length){row.push(cur);rows.push(row);} return rows;}
  var BANNER='https://replyalba.com/banner/', PT='https://replyalba.com/pt/';
  // 이미 절대 URL이면 그대로, 코드/파일명일 때만 접두어를 붙인다 (cpaad 등 외부 매체 대응)
  function absUrl(prefix,v){ v=(v||'').trim(); if(!v) return '';
    if(/^https?:\/\//i.test(v)) return v;
    if(v.indexOf('//')===0) return 'https:'+v;
    return prefix+v; }
  function esc(s){return (s||'').replace(/[&<>"]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m];});}
  function tr(s){return (s||'').trim();}
  function pad(n){return ('0'+n).slice(-2);}
  function key(s){s=tr(s);var d=s.match(/Date\((\d+),(\d+),(\d+)/);
    if(d) return d[1]+pad(+d[2]+1)+pad(+d[3]);
    var m=s.match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/); return m? m[1]+pad(m[2])+pad(m[3]) : '';}
  function toD(k){return k.length===8? new Date(+k.slice(0,4),+k.slice(4,6)-1,+k.slice(6,8)) : null;}
  var DOW=['일','월','화','수','목','금','토'];
  function fmt(k){var d=toD(k); return d? d.getFullYear()+'.'+pad(d.getMonth()+1)+'.'+pad(d.getDate())+'('+DOW[d.getDay()]+')':'';}
  function fmtS(k){var d=toD(k); return d? pad(d.getMonth()+1)+'.'+pad(d.getDate())+'('+DOW[d.getDay()]+')':'';}
  function nm(n){return String(n).replace(/\s+/g,'').replace(/[·\/,()\-…\.]/g,'');}
  function slugify(n){
    var t=String(n).normalize('NFC').trim().toLowerCase();   // 대문자 경로는 301 되므로 소문자 고정
    t=t.replace(/[^\w가-힣]+/g,'-').replace(/^-+|-+$/g,'');
    return t.slice(0,60);
  }
  var ALWAYS_RE=/^(상시|상시진행|상시모집|연중|수시)/;
  // 상시 판별 — 시트 날짜칸이 서식 때문에 텍스트를 못 받는 경우가 있어
  // '상태' 칸으로도 지정할 수 있게 열어 둔다.
  function alwaysLabel(start,end,status){
    var st=String(start||'').trim(), en=String(end||'').trim(), sc=String(status||'').trim();
    if(/^(상시|상시진행|상시모집|연중|수시)$/.test(st)) return en||'상시 진행';
    var m=sc.match(ALWAYS_RE);
    if(m){ var tail=sc.slice(m[1].length).replace(/^[\s·\-—|/]+/,''); return tail||en||'상시 진행'; }
    return null;
  }
  function detailUrl(e){
    return '/행사/'+encodeURIComponent(slugify(e.name)+'-'+(e.always?'상시':e.sk))+'/';
  }
  function cat(n){n=String(n).replace(/\s+/g,'');
    if(/허니문|신혼여행/.test(n))return'h'; if(/혼수|가전/.test(n))return'o';
    if(/드레스/.test(n))return'd'; if(/예물|주얼리|한복|예복/.test(n))return'j';
    if(/웨딩홀/.test(n))return'l'; return'w';}

  function rowsFrom(txt){
    var rows=parseCSV(txt); if(rows.length<2) return [];
    var hd=rows[0].map(tr);
    function ix(n,d){var i=hd.indexOf(n);return i>=0?i:d;}
    var iR=ix('지역',0),iN=ix('행사명',1),iS=ix('시작일',2),iE=ix('종료일',3),
        iP=ix('장소',4),iIMG=ix('이미지',6),iL=ix('신청링크',7),iB=hd.indexOf('혜택'),
        iST=ix('상태',5);
    var t0=new Date(); t0.setHours(0,0,0,0);
    return rows.slice(1).map(function(r){
      var lab = alwaysLabel(r[iS], r[iE], iST>=0? r[iST] : '');
      var always = lab !== null;
      return {city:tr(r[iR]), name:tr(r[iN]),
              sk: always? '' : key(r[iS]), ek: always? '' : key(r[iE]),
              always: always,
              dateText: always? lab : '',
              place:tr(r[iP]), img:absUrl(BANNER,tr(r[iIMG])),
              link:absUrl(PT,tr(r[iL]))||'/초대권-신청/',
              ben: iB>=0? tr(r[iB]) : ''};
    }).filter(function(e){
      if(!e.city||!e.name||!cset[e.city]) return false;
      if(e.always) return true;
      if(!e.sk) return false;
      var d=toD(e.ek||e.sk); return !d || d>=t0;
    });
  }

  function fetchTab(tab){
    return fetch(url(tab)).then(function(r){return r.text();}).then(rowsFrom).catch(function(){return [];});
  }

  Promise.all([fetchTab(null), fetchTab('수동추가')]).then(function(res){
    var all=res[0], seenN={}, seenP={};
    all.forEach(function(e){ var _s=e.always?'상시':e.sk;
      seenN[nm(e.name)+'|'+_s]=1;
      seenP[e.city+'|'+_s+'|'+e.place.replace(/\s+/g,'').slice(0,10)+'|'+cat(e.name)]=1; });
    res[1].forEach(function(e){
      var _sk=e.always?'상시':e.sk;
      var k1=nm(e.name)+'|'+_sk, k2=e.city+'|'+_sk+'|'+e.place.replace(/\s+/g,'').slice(0,10)+'|'+cat(e.name);
      if(seenN[k1]||seenP[k2]) return;
      seenN[k1]=1; seenP[k2]=1; all.push(e);
    });
    // 정적 카드보다 적으면 덮어쓰지 않음
    if(all.length < staticCount) return;
    all.sort(function(a,b){
      if(a.always!==b.always) return a.always?-1:1;   // 상시를 맨 위로
      return String(a.sk).localeCompare(String(b.sk));
    });
    var t0=new Date(); t0.setHours(0,0,0,0);
    box.innerHTML=all.map(function(e){
      var dates, dd='';
      if(e.always){
        dates = e.dateText || '상시 진행';
        dd = '<span class="dday now">상시</span>';
      } else {
        dates = fmt(e.sk)+(e.ek&&e.ek!==e.sk? ' ~ '+fmtS(e.ek):'');
        var d=toD(e.sk);
        if(d){var diff=Math.ceil((d-t0)/86400000);
          dd = diff>0&&diff<=30 ? '<span class="dday">D-'+diff+'</span>'
             : (diff<=0?'<span class="dday now">진행중</span>':'');}
      }
      var ct=multi? '<span class="ctag">'+esc(e.city)+'</span>':'';
      var du=detailUrl(e);
      var media=e.img? '<a class="poster" href="'+esc(e.link)+'" target="_blank" rel="noopener nofollow sponsored" aria-label="'+esc(e.name)+' 무료 초대권 신청"><img src="'+esc(e.img)+'" alt="'+esc(e.name)+' 포스터" loading="lazy" onerror="this.parentNode.style.display=\'none\'"></a>':'';
      var ben=e.ben? '<div class="benefit">혜택 '+esc(e.ben)+'</div>':'';
      return '<article class="card">'+media+'<div class="body"><div class="tags">'+
        '<span class="status">모집중</span>'+ct+dd+'</div>'+
        '<h3><a href="'+du+'">'+esc(e.name)+'</a></h3><div class="meta">일정 '+esc(dates)+'</div>'+
        (e.place?'<div class="meta">장소 '+esc(e.place)+'</div>':'')+ben+
        '<a class="cta" href="'+esc(e.link)+'" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청</a>'+
        '<a class="detail" href="'+du+'">박람회 정보 자세히 보기</a>'+
        '</div></article>';
    }).join('');

    /* 정적 빌드 이후 시트가 바뀌면 카드 수와 상단 숫자가 어긋난다.
       화면에 실제로 그려진 카드 수로 상단 통계와 소제목을 맞춰 준다. */
    try{
      var stat=document.querySelector('.hero .stats b');
      if(stat) stat.textContent=String(all.length);
      var sec=box.closest? box.closest('section') : null;
      var h2=sec? sec.querySelector('h2.sec') : null;
      if(h2){
        var base=h2.textContent.replace(/\s*\(\s*\d+\s*건\s*\)\s*$/,'').trim();
        h2.textContent = all.length? (base+' ('+all.length+'건)') : base;
      }
    }catch(_e){}
  }).catch(function(){});
})();

/* ── 정적 카드에 '자세히 보기' 버튼 보강 (JS 렌더 전에도 표시) ── */
(function(){
  function slugify2(n){
    var t=String(n).normalize('NFC').trim().toLowerCase();   // 대문자 경로는 301 되므로 소문자 고정
    return t.replace(/[^\w가-힣]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60);
  }
  document.addEventListener('DOMContentLoaded', function(){
    var box=document.getElementById('event-cards'); if(!box) return;
    box.querySelectorAll('.card').forEach(function(c){
      if(c.querySelector('.detail')) return;
      var a=c.querySelector('h3 a'), body=c.querySelector('.body');
      if(!a || !body) return;
      var d=document.createElement('a');
      d.className='detail'; d.href=a.getAttribute('href');
      d.textContent='박람회 정보 자세히 보기';
      body.appendChild(d);
    });
  });
})();
