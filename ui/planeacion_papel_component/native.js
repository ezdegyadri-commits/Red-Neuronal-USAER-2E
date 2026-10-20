// Adaptador de transporte: reutiliza el mismo renderizador, dentro de la página.
// No crea marcos, no escucha mensajes externos ni realiza solicitudes de red.
export default function mount(component) {
  const host = component.parentElement;
  if (host.__usaerEditor) {
    const state = host.__usaerEditor;
    const generation = ++state.generation;
    state.component = component;
    state.update(component.data);
    // Un efecto asíncrono anterior puede terminar después del nuevo montaje.
    // Su cleanup no debe destruir el editor vigente ni sus timers/respaldo.
    return () => { if (state.generation === generation) state.dispose(); };
  }
  const nativeWindow = globalThis.window, nativeDocument = globalThis.document;
  const timeouts = new Set(), intervals = new Set(), observers = new Set(), listeners = [];
  const state = { component, receive: null, disposed: false, generation: 1 };
  host.__usaerEditor = state;
  const document = new Proxy(nativeDocument, { get(target, key) {
    if (key === 'getElementById') return id => host.querySelector('#' + id);
    if (key === 'activeElement') return host.activeElement || target.activeElement;
    const value = Reflect.get(target, key, target);
    return typeof value === 'function' ? value.bind(target) : value;
  }});
  const window = new Proxy(nativeWindow, { get(target, key) {
    if (key === 'addEventListener') return (type, callback) => {
      if (type === 'message') { state.receive = callback; return; }
      target.addEventListener(type, callback); listeners.push([type, callback]);
    };
    const value = Reflect.get(target, key, target);
    return typeof value === 'function' ? value.bind(target) : value;
  }});
  const setTimeout = (callback, delay) => {
    const id = globalThis.setTimeout(() => { timeouts.delete(id); if (!state.disposed) callback(); }, delay);
    timeouts.add(id); return id;
  };
  const clearTimeout = id => { timeouts.delete(id); globalThis.clearTimeout(id); };
  const setInterval = (callback, delay) => {
    const id = globalThis.setInterval(() => { if (!state.disposed) callback(); }, delay);
    intervals.add(id); return id;
  };
  const clearInterval = id => { intervals.delete(id); globalThis.clearInterval(id); };
  const ResizeObserver = class {
    constructor(callback) { this.observer = new globalThis.ResizeObserver(callback); observers.add(this.observer); }
    observe(element) { this.observer.observe(element); }
  };
  const parent = { postMessage(message) {
    if (state.disposed) return;
    if (message.type === 'streamlit:componentReady') {
      queueMicrotask(() => { if (!state.disposed) state.update(state.component.data); });
    } else if (message.type === 'streamlit:setComponentValue') {
      state.component.setStateValue('evento', message.value);
    }
    // La altura se calcula con el contenido nativo; no existe un iframe a redimensionar.
  }};
  state.update = data => state.receive?.({ source: parent, origin: globalThis.location.origin,
    data: { type: 'streamlit:render', args: data } });
  state.dispose = () => {
    if (state.disposed) return;
    state.disposed = true;
    for (const id of timeouts) globalThis.clearTimeout(id);
    for (const id of intervals) globalThis.clearInterval(id);
    for (const observer of observers) observer.disconnect();
    for (const [type, callback] of listeners) nativeWindow.removeEventListener(type, callback);
    if (host.__usaerEditor === state) delete host.__usaerEditor;
  };
  /* USAER_RENDERER */
  state.update(component.data);
  return () => { if (state.generation === 1) state.dispose(); };
}
