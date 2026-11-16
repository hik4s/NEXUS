import {render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {WorkspaceBoundary} from '../src/WorkspaceLoader';

it('offers a page reload when workspace loading fails',()=>{
 const error=vi.spyOn(console,'error').mockImplementation(()=>{});
 function FailedDownload():never{throw new Error('Failed to fetch dynamically imported module');}
 try{
  render(<WorkspaceBoundary><FailedDownload/></WorkspaceBoundary>);
  expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível abrir o workspace');
  expect(screen.getByRole('button',{name:'Recarregar página'})).toBeVisible();
 }finally{error.mockRestore();}
});
