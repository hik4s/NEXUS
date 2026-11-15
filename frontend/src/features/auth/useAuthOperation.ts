import {useRef,useState} from 'react';

/** One gate for all confirmation operations that may replace the SDK session. */
export function useAuthOperation(){
 const lock=useRef(false);const [busy,setBusy]=useState(false);
 return {lock,busy,setBusy};
}
export type AuthOperation=ReturnType<typeof useAuthOperation>;
