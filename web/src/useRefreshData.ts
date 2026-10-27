import {useEffect, useRef} from 'react';

/**
 * Every mounted HRM module may refresh its own authorized API data when the
 * single top-bar "Refresh data" control is used. This avoids reloading the
 * browser and preserves in-progress forms, filters, and selections.
 *
 * The handler is held in a ref so changing local form state does not create
 * additional event subscriptions; listeners are removed on unmount.
 */
export const REFRESH_DATA_EVENT='sass-hrm:refresh-data';
export function useRefreshData(refresh:()=>void|Promise<unknown>):void {
  const callback=useRef(refresh);
  callback.current=refresh;
  useEffect(()=>{
    const onRefresh=()=>{void callback.current()};
    window.addEventListener(REFRESH_DATA_EVENT,onRefresh);
    return ()=>window.removeEventListener(REFRESH_DATA_EVENT,onRefresh);
  },[]);
}
