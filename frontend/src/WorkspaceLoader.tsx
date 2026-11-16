import {Component,lazy,Suspense} from 'react';
import type {ReactNode,ComponentProps} from 'react';
import {AuthFrame} from './features/auth/AuthFrame';

const Workspace=lazy(()=>import('./Workspace'));

export class WorkspaceBoundary extends Component<{children:ReactNode},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){
  if(this.state.failed)return <AuthFrame note="Se necessário, entre novamente após recarregar."><div role="alert" className="notice error">Não foi possível abrir o workspace. Recarregue a página para tentar novamente.</div><button className="button primary" onClick={()=>window.location.reload()}>Recarregar página</button></AuthFrame>;
  return this.props.children;
 }
}

export function WorkspaceLoader(props:ComponentProps<typeof Workspace>){
 return <WorkspaceBoundary><Suspense fallback={<AuthFrame note="Preparando suas ferramentas."><div role="status">Carregando workspace…</div></AuthFrame>}><Workspace {...props}/></Suspense></WorkspaceBoundary>;
}

