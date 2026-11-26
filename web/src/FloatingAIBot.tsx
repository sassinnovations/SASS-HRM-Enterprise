import React, {useEffect, useRef, useState} from 'react';
class AIWidgetBoundary extends React.Component<{children: React.ReactNode},{failed:boolean}>{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true}}
  render(){return this.state.failed?<p className="sass-ai-alert error" role="alert">SASS AI could not open. The rest of the workspace is still available.</p>:this.props.children}
}
import {Bot, Maximize2, Minimize2, Minus, Move} from 'lucide-react';
import {SassAICopilot} from './SassAICopilot';

/**
 * Non-modal floating assistant: the launcher never takes space from the HRM
 * workspace, and the chat window has no page-blocking backdrop or focus trap.
 * The assistant remains mounted while minimized, preserving chat/actions.
 */
export function FloatingAIBot({
  open, onOpenChange, user, navigate, activeFeatureKey,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: {name: string; role: string};
  navigate: (key: string) => void;
  activeFeatureKey: string;
}) {
  const windowRef = useRef<HTMLElement | null>(null);
  const launcherRef = useRef<HTMLButtonElement | null>(null);
  const dragRef = useRef<{id: number; x: number; y: number; left: number; top: number} | null>(null);
  const [position, setPosition] = useState<{x: number; y: number} | null>(null);
  const [maximized, setMaximized] = useState(false);
  const [announce, setAnnounce] = useState('');

  useEffect(() => {
    function clampToViewport() {
      setPosition(previous => {
        if (!previous || !windowRef.current) return previous;
        const rect = windowRef.current.getBoundingClientRect();
        return {
          x: Math.min(Math.max(previous.x, 8), Math.max(8, window.innerWidth - rect.width - 8)),
          y: Math.min(Math.max(previous.y, 8), Math.max(8, window.innerHeight - rect.height - 8)),
        };
      });
    }
    window.addEventListener('resize', clampToViewport);
    return () => window.removeEventListener('resize', clampToViewport);
  }, []);

  function startDrag(event: React.PointerEvent<HTMLDivElement>) {
    // Mobile: keep the window anchored to a predictable, reachable position.
    if (maximized || event.button !== 0 || window.innerWidth <= 820) return;
    if ((event.target as Element).closest('button')) return;
    const rect = windowRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragRef.current = {id: event.pointerId, x: event.clientX, y: event.clientY, left: rect.left, top: rect.top};
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function moveDrag(event: React.PointerEvent<HTMLDivElement>) {
    const d = dragRef.current;
    if (!d || d.id !== event.pointerId || !windowRef.current) return;
    const rect = windowRef.current.getBoundingClientRect();
    setPosition({
      x: Math.min(Math.max(d.left + event.clientX - d.x, 8), Math.max(8, window.innerWidth - rect.width - 8)),
      y: Math.min(Math.max(d.top + event.clientY - d.y, 8), Math.max(8, window.innerHeight - rect.height - 8)),
    });
  }
  function endDrag(event: React.PointerEvent<HTMLDivElement>) {
    if (dragRef.current?.id === event.pointerId) {
      dragRef.current = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }
  function keyboardMove(event: React.KeyboardEvent<HTMLDivElement>) {
    if (maximized || window.innerWidth <= 820 || !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const rect = windowRef.current?.getBoundingClientRect();
    if (!rect) return;
    const step = event.shiftKey ? 40 : 16;
    const dx = event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0;
    const dy = event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0;
    setPosition({
      x: Math.min(Math.max(rect.left + dx, 8), Math.max(8, window.innerWidth - rect.width - 8)),
      y: Math.min(Math.max(rect.top + dy, 8), Math.max(8, window.innerHeight - rect.height - 8)),
    });
    setAnnounce('AI window moved.');
  }
  return <div className="sass-ai-floating-root" data-testid="sass-ai-floating-widget">
    <button ref={launcherRef} type="button" className={`sass-ai-floating-launcher ${open ? 'active' : ''}`}
      aria-label={open ? 'Minimize AI bot' : 'Open AI bot'}
      title={open ? 'Minimize SASS AI' : 'Chat with SASS AI'}
      aria-expanded={open} aria-controls="sass-ai-floating-window"
      onClick={() => onOpenChange(!open)}>
      <Bot size={28} aria-hidden="true"/>
      <span>AI</span>
    </button>
    <section ref={windowRef} id="sass-ai-floating-window"
      className={`sass-ai-floating-window ${open ? 'open' : 'closed'} ${maximized ? 'maximized' : ''}`}
      style={position && !maximized ? {left: position.x, top: position.y, right: 'auto', bottom: 'auto'} : undefined}
      role="dialog" aria-modal="false" aria-labelledby="sass-ai-floating-title"
      aria-hidden={!open} data-testid="sass-ai-floating-window">
      <div className="sass-ai-floating-titlebar" tabIndex={open ? 0 : -1}
        role="toolbar" aria-label="Move AI assistant window"
        title="Drag to move, or focus and use arrow keys"
        onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag}
        onPointerCancel={endDrag} onKeyDown={keyboardMove}>
        <span className="sass-ai-floating-title" id="sass-ai-floating-title"><Bot size={19}/> SASS AI Assistant <small>GenAI + RAG</small></span>
        <div className="sass-ai-floating-controls">
          <Move size={15} aria-hidden="true" className="sass-ai-move-hint"/>
          <button type="button" aria-label={maximized ? 'Restore AI window size' : 'Expand AI window'}
            title={maximized ? 'Restore window' : 'Expand window'} onClick={() => setMaximized(v => !v)}>
            {maximized ? <Minimize2 size={16}/> : <Maximize2 size={16}/>}
          </button>
          <button type="button" aria-label="Close AI bot" title="Minimize AI window"
            onClick={() => {onOpenChange(false); launcherRef.current?.focus();}}><Minus size={19}/></button>
        </div>
      </div>
      <div className="sass-ai-floating-content">
        <AIWidgetBoundary><SassAICopilot user={user} navigate={navigate} activeFeatureKey={activeFeatureKey}/></AIWidgetBoundary>
      </div>
    </section>
    <span className="sass-ai-sr-only" role="status" aria-live="polite">{announce}</span>
  </div>;
}
