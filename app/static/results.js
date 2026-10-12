const cell=(row,text)=>{const td=document.createElement('td');td.textContent=text;row.append(td);return td;};
async function refresh(){
  const error=document.querySelector('#error');
  try{
    const response=await fetch('/api/test-results');if(!response.ok)throw Error('Could not load saved results ('+response.status+').');
    const data=await response.json();error.textContent='';document.querySelector('#updated').textContent='Updated '+new Date(data.updated_at).toLocaleString();
    for(const kind of ['native','automated']){
      const body=document.querySelector('#'+kind);body.replaceChildren();
      for(const item of data.results.filter(r=>r.kind===kind)){
        const row=document.createElement('tr');row.dataset.resultId=item.id;
        const title=cell(row,item.title);const scope=document.createElement('small');scope.textContent=item.scope+(item.note?' '+item.note:'');title.append(scope);
        const date=document.createElement('small');date.textContent=item.at?new Date(item.at).toLocaleString():'';title.append(date);
        const status=cell(row,item.status.toUpperCase());status.className=item.status;
        const duration=typeof item.seconds==='number'?Math.round(item.seconds)+' s':'—';
        if(kind==='native'){cell(row,duration);cell(row,(item.prompt_tokens??'—')+' tokens / '+(item.turns??'—')+' turns');}
        else{cell(row,String(item.tests??'—'));cell(row,duration);}
        const evidence=cell(row,'');const link=document.createElement('a');link.textContent='View report';link.href='/api/test-results/'+encodeURIComponent(item.id);link.target='_blank';link.rel='noopener';evidence.append(link);body.append(row);
      }
    }
  }catch(e){error.textContent=e.message;}
}
document.querySelector('#refresh').addEventListener('click',refresh);
refresh();setInterval(()=>{if(!document.hidden)refresh();},10000);
