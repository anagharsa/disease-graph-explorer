import type {Candidate,Disease,GraphData,Phenotype,Stats} from '../types'
const base=`${import.meta.env.VITE_API_URL||'http://127.0.0.1:8001'}/api`
async function request<T>(path:string,init?:RequestInit):Promise<T>{const res=await fetch(base+path,{...init,headers:{'Content-Type':'application/json',...init?.headers}});if(!res.ok){let detail:any;try{detail=await res.json()}catch{detail={detail:res.statusText}};throw new Error(typeof detail.detail==='string'?detail.detail:detail.detail?.message||detail.message||`Request failed (${res.status})`)}return res.json()}
export const api={
 health:()=>request<{status:string;database:string}>('/health'), stats:()=>request<Stats>('/stats'), sources:()=>request<any>('/sources'),
 searchPhenotypes:(q:string)=>request<{items:Phenotype[]}>(`/phenotypes/search?q=${encodeURIComponent(q)}`),
 searchDiseases:(q:string)=>request<{items:Disease[]}>(`/diseases/search?q=${encodeURIComponent(q)}`),
 disease:(id:string)=>request<Disease&{phenotypes:any[]}>(`/diseases/${encodeURIComponent(id)}`),
 match:(ids:string[])=>request<{items:Candidate[];method:string;interpretation:string}>('/match',{method:'POST',body:JSON.stringify({phenotype_ids:ids})}),
 compare:(ids:string[])=>request<any>('/compare',{method:'POST',body:JSON.stringify({disease_ids:ids})}),
 graph:(query='')=>request<GraphData>(`/graph${query}`), node:(id:string)=>request<any>(`/graph/nodes/${encodeURIComponent(id)}`),
 neighborhood:(id:string)=>request<GraphData>(`/graph/neighborhood/${encodeURIComponent(id)}`),
 graphSearch:(q:string)=>request<{items:Array<{id:string;name:string;kind:string}>}>(`/graph/search?q=${encodeURIComponent(q)}`),
 path:(disease_id:string,phenotype_ids:string[])=>request<{paths:any[]}>('/graph/path',{method:'POST',body:JSON.stringify({disease_id,phenotype_ids})})
}
