let CFG={};
const MG=[[1400,220.55],[2720,359.76],[5440,521.35],[7000,721.75],[14000,962.47],[28000,1243.47],[42000,1564.07],[56000,1925.31],[70000,2326.51],[105000,2928.06],[140000,3721.52],[175000,3979.69],[210000,4238.32],[280000,4772.07],[350000,4903.53],[420000,5035.59],[560000,5523.14],[700000,5826.70],[840000,6130.87],[1120000,6866.53],[1400000,7437.64],[1680000,8009.72],[3200000,8582.97]];
/* tabela de cartório: a de Padrões, se houver; senão a TJMG 2026 acima */
function tabCart(){ const t=CFG.cartorio; return Array.isArray(t)&&t.length?t.map(x=>[+x.ate,+x.valor]):MG; }
function cartMG(v){ if(v<=0) return 0; const t=tabCart(); for(const [lim,val] of t){ if(v<=lim) return val; } return t[t.length-1][1]; }
function irPF(g){ if(g<=0) return 0; const f=[[5e6,.15],[10e6,.175],[30e6,.2],[Infinity,.225]]; let t=0,prev=0; for(const [lim,a] of f){ if(g>prev){ t+=(Math.min(g,lim)-prev)*a; } prev=lim; } return t; }
function calc(p,lance,giro){
  const leil=lance*p.leiloeiro/100;
  const itbi=lance*p.itbi/100;
  let esc,reg;
  if(p.cartModo==="manual"){ esc=p.escrManual; reg=p.regManual; }
  else { reg=cartMG(lance); esc=p.escritura? cartMG(lance):0; }
  const mRec=giro; /* condomínio e IPTU contam desde o 1º mês */
  const cond=p.condominio*mRec, iptu=p.iptu*mRec;
  const inicial=lance+leil+itbi+esc+reg+p.debitos+p.reforma+p.desocupacao;
  const custo=inicial+cond+iptu;
  let oport=0;
  if(p.oport>0){
    const r=Math.pow(1+p.oport/100,1/12)-1;
    oport=inicial*(Math.pow(1+r,giro)-1);
    const m=p.condominio+p.iptu;
    if(m>0&&mRec>0) oport+=m*((Math.pow(1+r,mRec)-1)/r)-m*mRec;
  }
  const venda=p.venda, corr=venda*p.corretagem/100;
  const ganho=venda-corr-lance-leil-itbi-esc-reg-p.reforma;
  const ir= p.trib==="pf"? irPF(ganho) : p.trib==="pj"? venda*p.pjAliq/100 : 0;
  const res=venda-corr-custo-ir-oport;
  const roi=custo>0? res/custo : NaN;
  const mes=(isFinite(roi)&&roi>-1)? Math.pow(1+roi,1/giro)-1 : NaN;
  return {venda,corr,lance,leil,itbi,esc,reg,debitos:p.debitos,reforma:p.reforma,desoc:p.desocupacao,cond,iptu,oport,ir,custo,res,roi,mes};
}
function lanceMax(p,giro){
  const alvo=p.minimo/100; if(p.venda<=0) return NaN;
  let lo=0,hi=p.venda; if(calc(p,1,giro).roi<alvo) return NaN;
  for(let i=0;i<60;i++){ const mid=(lo+hi)/2; if(calc(p,mid,giro).roi>=alvo) lo=mid; else hi=mid; }
  return Math.floor(lo/100)*100;
}
const casos=JSON.parse(require('fs').readFileSync(process.argv[2]));
const out=casos.map(p=>{const r=calc(p,p.lance,p.giro);return {roi:+r.roi.toFixed(6),custo:+r.custo.toFixed(2),max:lanceMax(p,p.giro)};});
console.log(JSON.stringify(out));
