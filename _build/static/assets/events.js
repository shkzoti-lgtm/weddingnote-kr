/* 정적 카드가 이미 렌더돼 있음. 이 스크립트는 방문자에게만 "최신 상태"를 덧입힘.
   시트에 새 행사가 추가되면 재배포 전에도 반영되도록 보강하는 역할. */
(function(){
  var box=document.getElementById('event-cards');
  if(!box) return;
  var SHEET_ID='1R_lX8DcKXiHX50SuHrpLCgn1AhTqduAmEl_YhuhLnPI';
  var URL='https://docs.google.com/spreadsheets/d/'+SHEET_ID+'/gviz/tq?tqx=out:csv&t='+Date.now();
  var cities=(box.getAttribute('data-cities')||'').split(',').map(function(s){return s.trim();}).filter(Boolean);
  var multi=cities.length>1, cset={}; cities.forEach(function(c){cset[c]=1;});

  function parseCSV(t){var rows=[],row=[],cur='',q=false;
    for(var i=0;i<t.length;i++){var c=t[i];
      if(q){ if(c=='"'){ if(t[i+1]=='"'){cur+='"';i++;} else q=false; } else cur+=c; }
      else { if(c=='"')q=true; else if(c==','){row.push(cur);cur='';}
        else if(c=='\n'){row.push(cur);rows.push(row);row=[];cur='';}
        else if(c=='\r'){} else cur+=c; }}
    if(cur!==''||row.length){row.push(cur);rows.push(row);} return rows;}
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

  fetch(URL).then(function(r){return r.text();}).then(function(txt){
    var rows=parseCSV(txt); if(rows.length<2) return;
    var hd=rows[0].map(tr);
    function ix(n,d){var i=hd.indexOf(n);return i>=0?i:d;}
    var iR=ix('지역',0),iN=ix('행사명',1),iS=ix('시작일',2),iE=ix('종료일',3),
        iP=ix('장소',4),iIMG=ix('이미지',6),iL=ix('신청링크',7);
    var t0=new Date(); t0.setHours(0,0,0,0);
    var items=rows.slice(1).filter(function(r){
      if(!cset[tr(r[iR])]||!tr(r[iN])) return false;
      var e=key(r[iE])||key(r[iS]); var d=toD(e); return !d || d>=t0;
    });
    if(!items.length) return;                    // 정적 카드 유지
    items.sort(function(a,b){return key(a[iS]).localeCompare(key(b[iS]));});
    box.innerHTML=items.map(function(r){
      var name=tr(r[iN]),place=tr(r[iP]),img=tr(r[iIMG]),link=tr(r[iL])||'/초대권-신청/';
      var sk=key(r[iS]),ek=key(r[iE]);
      var dates=fmt(sk)+(ek&&ek!==sk? ' ~ '+fmtS(ek):'');
      var dd='', d=toD(sk);
      if(d){var diff=Math.ceil((d-t0)/86400000);
        dd = diff>0&&diff<=30 ? '<span class="dday">D-'+diff+'</span>' : (diff<=0?'<span class="dday now">진행중</span>':'');}
      var ct=multi? '<span class="ctag">'+esc(tr(r[iR]))+'</span>':'';
      var media=img? '<a class="poster" href="'+esc(link)+'" target="_blank" rel="noopener nofollow sponsored"><img src="'+esc(img)+'" alt="'+esc(name)+' 포스터" loading="lazy" onerror="this.parentNode.style.display=\'none\'"></a>':'';
      return '<article class="card">'+media+'<div class="body"><div class="tags">'+
        '<span class="status">모집중</span>'+ct+dd+'</div>'+
        '<h3>'+esc(name)+'</h3><div class="meta">일정 '+esc(dates)+'</div>'+
        (place?'<div class="meta">장소 '+esc(place)+'</div>':'')+
        '<a class="cta" href="'+esc(link)+'" target="_blank" rel="noopener nofollow sponsored">무료 초대권 신청</a>'+
        '</div></article>';
    }).join('');
  }).catch(function(){});   // 실패 시 정적 카드 그대로
})();
