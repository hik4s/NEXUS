export type EmailConfirmationLink={requested:boolean;tokenHash:string|null};

/** Capture once before React StrictMode mounts. Never verify during navigation. */
export function captureEmailConfirmationLink():EmailConfirmationLink{
 const url=new URL(window.location.href);
 const fragment=new URLSearchParams(url.hash.slice(1));
 const requested=url.pathname==='/auth/confirm';
 if(!requested)return {requested:false,tokenHash:null};
 const values=[...url.searchParams.getAll('token_hash'),...fragment.getAll('token_hash')];
 const types=[...url.searchParams.getAll('type'),...fragment.getAll('type')];
 const valid=values.length===1&&types.length===1&&types[0]==='email'&&/^[a-zA-Z0-9_-]{20,256}$/.test(values[0]);
 // Keep proof only in this page's memory. Fragments also avoid static HTTP logs.
 history.replaceState(null,'','/');
 return {requested:true,tokenHash:valid?values[0]:null};
}
export const emailConfirmationLink=captureEmailConfirmationLink();
