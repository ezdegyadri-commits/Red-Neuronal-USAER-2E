const {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
  useContext,
  createContext,
  useReducer,
  useLayoutEffect,
  useId,
  Fragment,
  Suspense,
  lazy,
  memo
} = React;
const API_BASE = window.location.origin;

// =============================================================
// COMPONENTE: LIMITADOR DE ERRORES (ERROR BOUNDARY) ANTI-PANTALLA BLANCA
// =============================================================
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }
  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error
    };
  }
  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary atrapó un error en tiempo de render:", error, errorInfo);
    this.setState({
      errorInfo
    });
    try {
      fetch(`${API_BASE}/api/logs/frontend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          error: String(error),
          message: error === null || error === void 0 ? void 0 : error.message,
          stack: error === null || error === void 0 ? void 0 : error.stack,
          componentStack: errorInfo === null || errorInfo === void 0 ? void 0 : errorInfo.componentStack,
          url: window.location.href,
          fecha: new Date().toISOString()
        })
      }).catch(() => {});
    } catch (_) {}
  }
  render() {
    if (this.state.hasError) {
      var _this$state$error, _this$state$error2, _this$state$errorInfo;
      return /*#__PURE__*/React.createElement("div", {
        className: "p-8 bg-slate-900 min-h-screen text-slate-100 flex items-center justify-center"
      }, /*#__PURE__*/React.createElement("div", {
        className: "bg-slate-800 border border-slate-700 max-w-lg w-full p-6 rounded-2xl shadow-2xl text-center space-y-4"
      }, /*#__PURE__*/React.createElement("div", {
        className: "text-3xl text-amber-400"
      }, "\u26A0\uFE0F"), /*#__PURE__*/React.createElement("h2", {
        className: "text-lg font-bold text-amber-300"
      }, "Aviso de Renderizado en M\xF3dulo"), /*#__PURE__*/React.createElement("p", {
        className: "text-xs text-slate-300 leading-relaxed"
      }, ((_this$state$error = this.state.error) === null || _this$state$error === void 0 ? void 0 : _this$state$error.message) || 'Ocurrió una excepción al procesar la vista interactiva.'), this.state.error && /*#__PURE__*/React.createElement("details", {
        className: "text-left bg-slate-900/80 p-3 rounded-lg border border-slate-700 text-[11px] text-red-300 font-mono overflow-x-auto max-h-40"
      }, /*#__PURE__*/React.createElement("summary", {
        className: "cursor-pointer text-slate-400 hover:text-slate-200 font-bold mb-1"
      }, "Ver Detalle T\xE9cnico"), /*#__PURE__*/React.createElement("div", null, String(((_this$state$error2 = this.state.error) === null || _this$state$error2 === void 0 ? void 0 : _this$state$error2.stack) || this.state.error)), ((_this$state$errorInfo = this.state.errorInfo) === null || _this$state$errorInfo === void 0 ? void 0 : _this$state$errorInfo.componentStack) && /*#__PURE__*/React.createElement("div", {
        className: "mt-2 text-slate-400"
      }, this.state.errorInfo.componentStack)), /*#__PURE__*/React.createElement("div", {
        className: "flex justify-center gap-3 pt-2"
      }, /*#__PURE__*/React.createElement("button", {
        onClick: () => {
          this.setState({
            hasError: false,
            error: null
          });
          window.location.reload();
        },
        className: "bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold px-4 py-2 rounded-lg transition"
      }, "Reintentar y Recargar"), /*#__PURE__*/React.createElement("button", {
        onClick: () => {
          sessionStorage.clear();
          localStorage.clear();
          window.location.href = '/';
        },
        className: "bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-bold px-4 py-2 rounded-lg transition"
      }, "Limpiar Sesi\xF3n"))));
    }
    return this.props.children;
  }
}

// Cliente API con Bearer Token y manejo de sesión
async function descargarArchivoAutenticado(endpoint, nombreArchivo) {
  try {
    const token = sessionStorage.getItem('usaer_token') || sessionStorage.getItem('token') || '';
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const fullUrl = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const res = await fetch(fullUrl, {
      method: 'GET',
      headers: headers
    });
    if (!res.ok) {
      let errText = 'Error en descarga';
      try {
        const errJson = await res.json();
        errText = errJson.detail || res.statusText;
      } catch (_) {
        errText = res.statusText;
      }
      if (res.status === 401) {
        throw new Error('Sesión expirada o no autorizada. Por favor inicie sesión nuevamente.');
      }
      throw new Error(errText);
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = nombreArchivo || 'documento.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 15000);
  } catch (err) {
    alert('Aviso de descarga: ' + err.message);
  }
}
async function apiRequest(endpoint, options = {}) {
  const token = sessionStorage.getItem('usaer_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? {
      'Authorization': `Bearer ${token}`
    } : {}),
    ...options.headers
  };
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  if (res.status === 401) {
    sessionStorage.removeItem('usaer_token');
    sessionStorage.removeItem('usaer_user');
    window.dispatchEvent(new Event('auth_expired'));
    throw new Error('Sesión expirada o credenciales inválidas');
  }
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Error ${res.status}`);
  }
  return await res.json();
}

// =============================================================
// COMPONENTE: PANTALLA DE INICIO DE SESIÓN
// =============================================================
function LoginScreen({
  onLoginSuccess
}) {
  const [usuario, setUsuario] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const handleSubmit = async e => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          usuario,
          password
        })
      });
      if (!res.ok) {
        throw new Error('Usuario o contraseña incorrectos.');
      }
      const data = await res.json();
      onLoginSuccess(data.user, data.token);
    } catch (err) {
      setError(err.message || 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "min-h-screen flex items-center justify-center bg-slate-900 px-4 py-12"
  }, /*#__PURE__*/React.createElement("div", {
    className: "max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-center space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-600 font-black text-3xl mb-2"
  }, "\u25C8"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-black tracking-tight text-slate-900"
  }, "USAER 02-E \xB7 2.0"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500 font-medium"
  }, "Plataforma Pedag\xF3gica y Administrativa Integral")), error && /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs font-semibold"
  }, "\u26A0\uFE0F ", error), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleSubmit,
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1"
  }, "Usuario"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    required: true,
    value: usuario,
    onChange: e => setUsuario(e.target.value),
    className: "w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500",
    placeholder: "ej. edgar, marycruz, ceci, zuemmy"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1"
  }, "Contrase\xF1a"), /*#__PURE__*/React.createElement("input", {
    type: "password",
    required: true,
    value: password,
    onChange: e => setPassword(e.target.value),
    className: "w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500",
    placeholder: "Tu contrase\xF1a institucional"
  })), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: loading,
    className: "w-full py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-bold text-sm shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50"
  }, loading ? /*#__PURE__*/React.createElement("span", null, "Iniciando sesi\xF3n...") : /*#__PURE__*/React.createElement("span", null, "Entrar al Sistema \u2192"))), /*#__PURE__*/React.createElement("div", {
    className: "border-t border-slate-100 pt-4 text-center"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-[11px] text-slate-400"
  }, "Acceso exclusivo para personal de USAER 02-E \xB7 Zona 001 Primarias"))));
}

// =============================================================
// COMPONENTE PRINCIPAL (APP CON NAVEGACIÓN COMPLETA DE MÓDULOS)
// =============================================================
function App() {
  const [user, setUser] = React.useState(() => {
    try {
      const u = sessionStorage.getItem('usaer_user');
      const t = sessionStorage.getItem('usaer_token');
      return u && t ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  });
  const [currentView, setCurrentView] = React.useState('mis_documentos');
  const [activeDocId, setActiveDocId] = React.useState(null);
  const [activeAlumnoId, setActiveAlumnoId] = React.useState(null);
  const [metrics, setMetrics] = React.useState({
    latency: 12,
    requests: 1
  });
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const [notificacionEnVivo, setNotificacionEnVivo] = React.useState(null);

  // Sincronización en vivo entre sesiones concurrentes (Cero Recargas)
  React.useEffect(() => {
    if (!user) return;
    let lastTs = Date.now() / 1000;
    const poller = setInterval(async () => {
      try {
        const data = await apiRequest(`/api/novedades-en-vivo?desde=${lastTs}`);
        if (data && Array.isArray(data.novedades) && data.novedades.length > 0) {
          lastTs = data.servidor_tiempo || Date.now() / 1000;
          const ult = data.novedades[data.novedades.length - 1];
          if (ult && ult.usuario !== user.usuario) {
            setNotificacionEnVivo(`🔄 ${ult.resumen || 'Cambio registrado en plataforma'}`);
            setTimeout(() => setNotificacionEnVivo(null), 6000);
          }
        }
      } catch (_) {}
    }, 6000);
    return () => clearInterval(poller);
  }, [user]);
  React.useEffect(() => {
    const handleAuthExpired = () => {
      sessionStorage.clear();
      setUser(null);
    };
    window.addEventListener('auth_expired', handleAuthExpired);
    let idleTimer;
    const resetIdle = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        sessionStorage.clear();
        setUser(null);
      }, 45 * 60 * 1000);
    };
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    window.addEventListener('click', resetIdle);
    resetIdle();
    return () => {
      window.removeEventListener('auth_expired', handleAuthExpired);
      clearTimeout(idleTimer);
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
      window.removeEventListener('click', resetIdle);
    };
  }, []);
  const handleLoginSuccess = (userData, token) => {
    sessionStorage.setItem('usaer_token', token);
    sessionStorage.setItem('usaer_user', JSON.stringify(userData));
    setUser(userData);
  };
  const handleLogout = async () => {
    try {
      await apiRequest('/api/auth/logout', {
        method: 'POST'
      });
    } catch (_) {}
    sessionStorage.clear();
    setUser(null);
  };
  const navigateTo = view => {
    setCurrentView(view);
    setDropdownOpen(false);
  };
  if (!user) {
    return /*#__PURE__*/React.createElement(LoginScreen, {
      onLoginSuccess: handleLoginSuccess
    });
  }
  return /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col min-h-screen"
  }, /*#__PURE__*/React.createElement("header", {
    className: "bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40"
  }, /*#__PURE__*/React.createElement("div", {
    className: "max-w-7xl mx-auto px-4 h-14 flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3 cursor-pointer",
    onClick: () => navigateTo('mis_documentos')
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-amber-500 font-black text-xl"
  }, "\u25C8"), /*#__PURE__*/React.createElement("span", {
    className: "font-bold tracking-tight text-slate-100 text-lg"
  }, "USAER 02-E"), /*#__PURE__*/React.createElement("span", {
    className: "bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded font-semibold hidden sm:inline"
  }, "Zona 001 \xB7 SPA 2.0")), /*#__PURE__*/React.createElement("nav", {
    className: "hidden md:flex items-center space-x-1 text-sm font-medium"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('mis_documentos'),
    className: `px-3 py-1.5 rounded-lg transition ${currentView === 'mis_documentos' ? 'bg-slate-800 text-amber-400 font-bold' : 'text-slate-400 hover:text-slate-200'}`
  }, "\uD83D\uDCC1 Mis Documentos"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('expedientes'),
    className: `px-3 py-1.5 rounded-lg transition ${currentView === 'expedientes' ? 'bg-slate-800 text-amber-400 font-bold' : 'text-slate-400 hover:text-slate-200'}`
  }, "\uD83D\uDC64 Alumnos y Expedientes"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('epp'),
    className: `px-3 py-1.5 rounded-lg transition ${currentView === 'epp' ? 'bg-slate-800 text-amber-400 font-bold' : 'text-slate-400 hover:text-slate-200'}`
  }, "\uD83D\uDCCB EPP"), /*#__PURE__*/React.createElement("div", {
    className: "relative"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setDropdownOpen(!dropdownOpen),
    className: "px-3 py-1.5 rounded-lg text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "Todos los M\xF3dulos"), /*#__PURE__*/React.createElement("span", {
    className: "text-xs"
  }, "\u25BE")), dropdownOpen && /*#__PURE__*/React.createElement("div", {
    className: "absolute left-0 mt-2 w-80 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-2 z-50 text-xs grid grid-cols-2 gap-1 p-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "col-span-2 px-2 py-1 text-[10px] uppercase font-bold text-amber-400 tracking-wider border-b border-slate-800 mb-1"
  }, "\xC1rea Pedag\xF3gica y Anexos"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('anexo3'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDEA7 Anexo III BAP"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('anexo4'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCA1 Anexo IV Sugerencias"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('anexo5'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCCC Anexo V Eventos"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('anexo7'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCD1 Anexo VII Derivaci\xF3n"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('informes'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCC4 Informes"), /*#__PURE__*/React.createElement("div", {
    className: "col-span-2 px-2 py-1 text-[10px] uppercase font-bold text-amber-400 tracking-wider border-b border-slate-800 my-1"
  }, "Organizaci\xF3n y Gesti\xF3n"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('horarios'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\u23F0 Horarios de Apoyo"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('cronogramas'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCC5 Cronograma Mensual"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('calendario'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDDD3\uFE0F Calendario SEGEY"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('docentes_regulares'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDC65 Maestros Primaria"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('novedades'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCE2 Supervisi\xF3n Zona 001"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('juntas'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83E\uDD1D Juntas y Relator\xEDas"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('metas'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83C\uDFAF Metas Personales"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('tramites'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCE8 Tr\xE1mites"), /*#__PURE__*/React.createElement("div", {
    className: "col-span-2 px-2 py-1 text-[10px] uppercase font-bold text-amber-400 tracking-wider border-b border-slate-800 my-1"
  }, "Institucional y Direcci\xF3n"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('visitas'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCCB Actas y Oficios"), /*#__PURE__*/React.createElement("button", {
    onClick: () => navigateTo('estadisticas'),
    className: "p-2 text-left hover:bg-slate-800 rounded-lg text-slate-300 hover:text-amber-300 transition"
  }, "\uD83D\uDCCA Estad\xEDsticas Zona")))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hidden sm:flex items-center space-x-1.5 text-xs bg-slate-800/80 px-2.5 py-1 rounded border border-slate-700/50"
  }, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-emerald-400 animate-pulse"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400"
  }, "Latencia:"), /*#__PURE__*/React.createElement("strong", {
    className: "text-emerald-300 font-mono"
  }, metrics.latency, " ms")), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-right text-xs hidden lg:block"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-semibold text-slate-200"
  }, user.nombre), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-400"
  }, user.rol)), /*#__PURE__*/React.createElement("button", {
    onClick: handleLogout,
    className: "text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded border border-slate-700 transition",
    title: "Cerrar sesi\xF3n"
  }, "Salir"))))), notificacionEnVivo && /*#__PURE__*/React.createElement("div", {
    className: "bg-amber-500 text-slate-950 font-bold text-xs py-2 px-4 text-center sticky top-14 z-50 shadow-md flex items-center justify-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, notificacionEnVivo), /*#__PURE__*/React.createElement("button", {
    onClick: () => setNotificacionEnVivo(null),
    className: "ml-2 underline text-[11px] font-normal hover:text-white"
  }, "Cerrar")), /*#__PURE__*/React.createElement("main", {
    className: "flex-1 max-w-7xl w-full mx-auto px-4 py-6",
    onClick: () => dropdownOpen && setDropdownOpen(false)
  }, currentView === 'mis_documentos' && /*#__PURE__*/React.createElement(MisDocumentosView, {
    onOpenDoc: id => {
      setActiveDocId(id);
      setCurrentView('editor');
    },
    onOpenExpediente: id => {
      setActiveAlumnoId(id);
      setCurrentView('expedientes');
    },
    setMetrics: setMetrics
  }), currentView === 'editor' && /*#__PURE__*/React.createElement(PlaneacionEditorView, {
    docId: activeDocId,
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'expedientes' && /*#__PURE__*/React.createElement(ExpedientesView, {
    initialAlumnoId: activeAlumnoId,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'epp' && /*#__PURE__*/React.createElement(EPPView, {
    onBack: () => setCurrentView('mis_documentos'),
    onOpenAlumno: id => {
      setActiveAlumnoId(id);
      setCurrentView('expedientes');
    },
    setMetrics: setMetrics
  }), currentView === 'anexo3' && /*#__PURE__*/React.createElement(Anexo3View, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo4' && /*#__PURE__*/React.createElement(Anexo4View, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo5' && /*#__PURE__*/React.createElement(Anexo5View, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo7' && /*#__PURE__*/React.createElement(Anexo7View, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'horarios' && /*#__PURE__*/React.createElement(HorariosView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'cronogramas' && /*#__PURE__*/React.createElement(CronogramasView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'calendario' && /*#__PURE__*/React.createElement(CalendarioView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'docentes_regulares' && /*#__PURE__*/React.createElement(DocentesRegularesView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'novedades' && /*#__PURE__*/React.createElement(NovedadesView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'juntas' && /*#__PURE__*/React.createElement(JuntasView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'metas' && /*#__PURE__*/React.createElement(MetasView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'tramites' && /*#__PURE__*/React.createElement(TramitesView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'informes' && /*#__PURE__*/React.createElement(InformesView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'visitas' && /*#__PURE__*/React.createElement(ActasYOficiosView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'estadisticas' && /*#__PURE__*/React.createElement(EstadisticasView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  })), /*#__PURE__*/React.createElement("footer", {
    className: "border-t border-slate-200 bg-white py-3 text-center text-xs text-slate-400"
  }, "USAER 02-E \xB7 Sistema Pedag\xF3gico Integrado 2.0 \xB7 React SPA + FastAPI + PostgreSQL (Cero Recargas)"));
}

// =============================================================
// VISTA 1: MIS DOCUMENTOS (HUB CENTRAL EN 1 CLIC)
// =============================================================
function MisDocumentosView({
  onOpenDoc,
  onOpenExpediente,
  setMetrics
}) {
  const [planeaciones, setPlaneaciones] = React.useState([]);
  const [alumnos, setAlumnos] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [busqueda, setBusqueda] = React.useState('');
  const [modalAlumno, setModalAlumno] = React.useState(false);
  const [deleteTargetId, setDeleteTargetId] = React.useState(null);

  // Estado para nuevo alumno
  const [nuevoNombre, setNuevoNombre] = React.useState('');
  const [nuevoCURP, setNuevoCURP] = React.useState('');
  const [nuevoGrado, setNuevoGrado] = React.useState('2');
  const [nuevoGrupo, setNuevoGrupo] = React.useState('A');
  const [nuevaEscuela, setNuevaEscuela] = React.useState('ESC-001');
  const [nuevaCondicion, setNuevaCondicion] = React.useState('TDAH');
  const loadHub = React.useCallback(async () => {
    const t0 = performance.now();
    try {
      const [planesData, alumnosData] = await Promise.all([apiRequest('/api/planeaciones'), apiRequest('/api/alumnos')]);
      setPlaneaciones(planesData);
      setAlumnos(alumnosData);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 2
      }));
    } catch (e) {
      console.error("Error cargando hub:", e);
    } finally {
      setLoading(false);
    }
  }, [setMetrics]);
  React.useEffect(() => {
    loadHub();
  }, [loadHub]);
  const handleCrearAlumno = async e => {
    e.preventDefault();
    try {
      await apiRequest('/api/alumnos', {
        method: 'POST',
        body: JSON.stringify({
          nombre_completo: nuevoNombre,
          curp: nuevoCURP,
          grado: nuevoGrado,
          grupo: nuevoGrupo,
          id_escuela: nuevaEscuela,
          condicion_discapacidad: nuevaCondicion
        })
      });
      setModalAlumno(false);
      setNuevoNombre('');
      setNuevoCURP('');
      loadHub();
    } catch (err) {
      alert(`Error al crear alumno: ${err.message}`);
    }
  };
  const handleConfirmarEliminar = async () => {
    if (!deleteTargetId) return;
    try {
      await apiRequest(`/api/planeaciones/${deleteTargetId}`, {
        method: 'DELETE'
      });
      setPlaneaciones(prev => prev.filter(p => p.id !== deleteTargetId));
      setDeleteTargetId(null);
    } catch (err) {
      alert(`Error al eliminar: ${err.message}`);
    }
  };
  const planesFiltrados = planeaciones.filter(p => {
    var _p$metadatos, _p$datos, _p$datos2;
    const q = busqueda.toLowerCase();
    return (((_p$metadatos = p.metadatos) === null || _p$metadatos === void 0 ? void 0 : _p$metadatos.titulo) || '').toLowerCase().includes(q) || (((_p$datos = p.datos) === null || _p$datos === void 0 ? void 0 : _p$datos.Escuela) || '').toLowerCase().includes(q) || (((_p$datos2 = p.datos) === null || _p$datos2 === void 0 ? void 0 : _p$datos2.Docente_Especialista) || '').toLowerCase().includes(q) || (p.id || '').toLowerCase().includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Mis Documentos de Trabajo"), /*#__PURE__*/React.createElement("p", {
    className: "text-sm text-slate-500"
  }, "Historial completo de planeaciones y expedientes autorizados")), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalAlumno(true),
    className: "px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl font-semibold text-sm transition"
  }, "+ Alta R\xE1pida de Alumno"), /*#__PURE__*/React.createElement("button", {
    onClick: () => onOpenDoc(`plan-nuevo-${Date.now().toString(36)}`),
    className: "px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-semibold shadow-sm text-sm transition flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "+"), /*#__PURE__*/React.createElement("span", null, "Nueva Planeaci\xF3n (Anexo XXIII)")))), /*#__PURE__*/React.createElement("div", {
    className: "relative"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    placeholder: "Buscar por alumno, escuela, grado o aprendizaje esperado...",
    className: "w-full pl-4 pr-10 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 shadow-sm"
  })), /*#__PURE__*/React.createElement("div", {
    className: "space-y-3"
  }, /*#__PURE__*/React.createElement("h2", {
    className: "text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCDD Planeaciones y Planes de Intervenci\xF3n"), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full"
  }, planesFiltrados.length)), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200"
  }, /*#__PURE__*/React.createElement("div", {
    className: "inline-block animate-spin text-amber-600 text-2xl mb-2"
  }, "\u25C8"), /*#__PURE__*/React.createElement("p", {
    className: "text-sm text-slate-500"
  }, "Cargando documentos desde PostgreSQL...")) : planesFiltrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-8 bg-white rounded-xl border border-slate-200 text-slate-500 text-sm"
  }, "No hay planeaciones que coincidan con la b\xFAsqueda.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, planesFiltrados.map(plan => {
    var _plan$metadatos, _plan$datos, _plan$datos2, _plan$datos3;
    return /*#__PURE__*/React.createElement("div", {
      key: plan.id,
      className: "bg-white p-4 rounded-xl border border-slate-200 hover:border-amber-500/50 hover:shadow-md transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
    }, /*#__PURE__*/React.createElement("div", {
      className: "space-y-1 cursor-pointer flex-1",
      onClick: () => onOpenDoc(plan.id)
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "font-bold text-slate-900 group-hover:text-amber-700 transition"
    }, ((_plan$metadatos = plan.metadatos) === null || _plan$metadatos === void 0 ? void 0 : _plan$metadatos.titulo) || `Planeación Anexo ${plan.formato}`), /*#__PURE__*/React.createElement("span", {
      className: `text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${plan.estado === 'APROBADO' || plan.estado === 'AUTORIZADA' ? 'bg-emerald-100 text-emerald-800' : plan.estado === 'REVISIÓN' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}`
    }, plan.estado)), /*#__PURE__*/React.createElement("div", {
      className: "text-xs text-slate-500 flex items-center space-x-3"
    }, /*#__PURE__*/React.createElement("span", null, "\uD83C\uDFEB ", ((_plan$datos = plan.datos) === null || _plan$datos === void 0 ? void 0 : _plan$datos.Escuela) || 'Primaria Oficial'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Grado: ", ((_plan$datos2 = plan.datos) === null || _plan$datos2 === void 0 ? void 0 : _plan$datos2.Grado_Grupo) || 'Atención USAER'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, ((_plan$datos3 = plan.datos) === null || _plan$datos3 === void 0 ? void 0 : _plan$datos3.Docente_Especialista) || 'Docente USAER'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Guardado: ", plan.guardado_en || 'Reciente'))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-3"
    }, plan.observaciones_director && /*#__PURE__*/React.createElement("span", {
      className: "text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md border border-slate-200 font-medium hidden sm:inline"
    }, "\uD83D\uDCAC Con Vo. Bo."), /*#__PURE__*/React.createElement("button", {
      onClick: () => onOpenDoc(plan.id),
      className: "text-xs font-semibold text-amber-600 hover:text-amber-700 px-3 py-1.5 rounded-lg border border-amber-200 hover:bg-amber-50 transition"
    }, "Abrir \u2192"), /*#__PURE__*/React.createElement("button", {
      onClick: () => setDeleteTargetId(plan.id),
      className: "text-xs text-slate-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition",
      title: "Eliminar planeaci\xF3n"
    }, "\uD83D\uDDD1\uFE0F")));
  }))), /*#__PURE__*/React.createElement("div", {
    className: "space-y-3 pt-4"
  }, /*#__PURE__*/React.createElement("h2", {
    className: "text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDC65 Expedientes de Alumnos Asignados"), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full"
  }, alumnos.length)), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
  }, alumnos.slice(0, 15).map(al => /*#__PURE__*/React.createElement("div", {
    key: al.id,
    onClick: () => onOpenExpediente(al.id),
    className: "bg-white p-3.5 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-sm transition cursor-pointer space-y-1.5"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-800 text-sm"
  }, al.nombre_completo), /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500"
  }, /*#__PURE__*/React.createElement("span", null, al.grado, "\xB0 ", al.grupo), /*#__PURE__*/React.createElement("span", {
    className: "mx-1.5"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", null, al.escuela)), /*#__PURE__*/React.createElement("div", {
    className: "pt-1 flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-[11px] bg-amber-50 text-amber-800 font-semibold px-2 py-0.5 rounded border border-amber-200"
  }, al.condicion || 'Atención USAER'), /*#__PURE__*/React.createElement("span", {
    className: "text-xs text-slate-400 hover:text-slate-700 font-medium"
  }, "Ver expediente \u2192"))))), alumnos.length > 15 && /*#__PURE__*/React.createElement("div", {
    className: "text-center pt-2"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => onOpenExpediente(alumnos[0].id),
    className: "text-xs text-amber-700 font-bold hover:underline"
  }, "Ver todos los ", alumnos.length, " alumnos en el m\xF3dulo de Expedientes \u2192"))), deleteTargetId && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl space-y-4"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-lg"
  }, "\xBFEliminar planeaci\xF3n?"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-600"
  }, "Esta acci\xF3n remover\xE1 el borrador seleccionado de la base de datos de forma permanente."), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setDeleteTargetId(null),
    className: "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    onClick: handleConfirmarEliminar,
    className: "px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-sm"
  }, "Eliminar Documento")))), modalAlumno && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-base"
  }, "Registrar Nuevo Alumno"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalAlumno(false),
    className: "text-slate-400 hover:text-slate-600"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleCrearAlumno,
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Nombre Completo:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    required: true,
    value: nuevoNombre,
    onChange: e => setNuevoNombre(e.target.value),
    className: "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-1 focus:ring-amber-500",
    placeholder: "ej. Mateo Emiliano Poot Dzib"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "CURP:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: nuevoCURP,
    onChange: e => setNuevoCURP(e.target.value),
    className: "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-1 focus:ring-amber-500 uppercase",
    placeholder: "18 caracteres"
  })), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Grado:"), /*#__PURE__*/React.createElement("select", {
    value: nuevoGrado,
    onChange: e => setNuevoGrado(e.target.value),
    className: "w-full px-3 py-2 border rounded-lg"
  }, /*#__PURE__*/React.createElement("option", {
    value: "1"
  }, "1\xB0 Primaria"), /*#__PURE__*/React.createElement("option", {
    value: "2"
  }, "2\xB0 Primaria"), /*#__PURE__*/React.createElement("option", {
    value: "3"
  }, "3\xB0 Primaria"), /*#__PURE__*/React.createElement("option", {
    value: "4"
  }, "4\xB0 Primaria"), /*#__PURE__*/React.createElement("option", {
    value: "5"
  }, "5\xB0 Primaria"), /*#__PURE__*/React.createElement("option", {
    value: "6"
  }, "6\xB0 Primaria"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Grupo:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: nuevoGrupo,
    onChange: e => setNuevoGrupo(e.target.value),
    className: "w-full px-3 py-2 border rounded-lg uppercase",
    placeholder: "A, B, C"
  }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Condici\xF3n / BAP:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: nuevaCondicion,
    onChange: e => setNuevaCondicion(e.target.value),
    className: "w-full px-3 py-2 border rounded-lg",
    placeholder: "ej. TDAH, TEA, Dificultades de Aprendizaje"
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-3"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalAlumno(false),
    className: "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    className: "px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl font-bold shadow-sm"
  }, "Guardar Alumno"))))));
}

// =============================================================
// VISTA 2: EDITOR DE PLANEACIÓN COMPATIBLE CON STREAMLIT + SPA
// =============================================================
function PlaneacionEditorView({
  docId,
  user,
  onBack,
  setMetrics
}) {
  var _doc$tablas4, _doc$tablas5, _doc$tablas6, _doc$tablas7, _doc$metadatos, _doc$datos2, _doc$datos3, _doc$datos4, _doc$datos5, _doc$metadatos2, _doc$textos, _doc$textos2, _doc$textos3, _doc$textos4, _doc$textos5, _doc$metadatos4, _doc$firmas_resueltas, _doc$datos6, _doc$firmas_resueltas2;
  const [doc, setDoc] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [activeTab, setActiveTab] = React.useState('aprendizajes');
  const [saveStatus, setSaveStatus] = React.useState('saved');
  const [conflictError, setConflictError] = React.useState(null);
  const [assistantOpen, setAssistantOpen] = React.useState(false);
  const [activeAlumnoId, setActiveAlumnoId] = React.useState('');
  const [borradorDisponible, setBorradorDisponible] = React.useState(null);
  const debounceTimer = React.useRef(null);
  const fetchDoc = React.useCallback(async () => {
    setLoading(true);
    setConflictError(null);
    const t0 = performance.now();
    try {
      const data = await apiRequest(`/api/planeaciones/${docId}`);
      setDoc(data);
      try {
        const draftRaw = localStorage.getItem(`usaer_borrador_plan_${docId}`);
        if (draftRaw) {
          var _draft$metadatos;
          const draft = JSON.parse(draftRaw);
          if (draft && draft.id === docId && (_draft$metadatos = draft.metadatos) !== null && _draft$metadatos !== void 0 && _draft$metadatos.titulo) {
            setBorradorDisponible(draft);
          }
        }
      } catch (_) {}
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 1
      }));
    } catch (e) {
      console.error("Error abriendo planeación:", e);
    } finally {
      setLoading(false);
    }
  }, [docId, setMetrics]);
  React.useEffect(() => {
    fetchDoc();
  }, [fetchDoc]);

  // Alumnos vinculados en la planeación (tolerante a estructuras nulas)
  const alumnosEnPlaneacion = React.useMemo(() => {
    if (!doc) return [];
    const map = new Map();
    try {
      var _doc$datos, _doc$tablas, _doc$tablas2, _doc$tablas3;
      if (Array.isArray((_doc$datos = doc.datos) === null || _doc$datos === void 0 ? void 0 : _doc$datos.Alumnos)) {
        doc.datos.Alumnos.forEach(a => {
          if (!a) return;
          const id = a.ID_Alumno || a.id || a.id_alumno || '';
          const nom = a.Nombre_Completo || a.nombre || a.alumno || id;
          if (id) map.set(id, {
            id,
            nombre: nom
          });
        });
      }
      const tNee = ((_doc$tablas = doc.tablas) === null || _doc$tablas === void 0 ? void 0 : _doc$tablas.nee) || ((_doc$tablas2 = doc.tablas) === null || _doc$tablas2 === void 0 ? void 0 : _doc$tablas2.aprendizajes) || ((_doc$tablas3 = doc.tablas) === null || _doc$tablas3 === void 0 ? void 0 : _doc$tablas3["Tabla principal"]) || [];
      if (Array.isArray(tNee)) {
        tNee.forEach(row => {
          if (!row) return;
          const id = row.id_alumno || row.ID_Alumno || '';
          const nom = row.alumno || row.Alumno || row.nombre_completo || '';
          if (id && !map.has(id)) {
            map.set(id, {
              id,
              nombre: nom || id
            });
          } else if (nom && !map.has(nom)) {
            map.set(nom, {
              id: id || nom,
              nombre: nom
            });
          }
        });
      }
    } catch (err) {
      console.warn("Aviso computando alumnos en planeación:", err);
    }
    return Array.from(map.values());
  }, [doc]);
  React.useEffect(() => {
    if (alumnosEnPlaneacion.length > 0 && !activeAlumnoId) {
      setActiveAlumnoId(alumnosEnPlaneacion[0].id);
    }
  }, [alumnosEnPlaneacion, activeAlumnoId]);
  const persistir = React.useCallback(async docActual => {
    if (!navigator.onLine) {
      setSaveStatus('offline');
      return;
    }
    setSaveStatus('saving');
    setConflictError(null);
    const t0 = performance.now();
    try {
      const res = await apiRequest('/api/planeaciones', {
        method: 'POST',
        body: JSON.stringify(docActual)
      });
      setSaveStatus('saved');
      try {
        localStorage.removeItem(`usaer_borrador_plan_${docId}`);
      } catch (_) {}
      setBorradorDisponible(null);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 1
      }));
      setDoc(d => ({
        ...d,
        revision: res.revision,
        guardado_en: res.guardado_en,
        firmas_resueltas: res.firmas,
        metadatos: res.metadatos || d.metadatos
      }));
    } catch (e) {
      console.error("Error al persistir:", e);
      if (e.message && e.message.includes('Conflicto de concurrencia')) {
        setSaveStatus('conflict');
        setConflictError(e.message);
      } else {
        setSaveStatus('error');
      }
    }
  }, [setMetrics]);
  const mutarDoc = updater => {
    setDoc(prev => {
      const next = typeof updater === 'function' ? updater(prev) : {
        ...prev,
        ...updater
      };
      setSaveStatus('dirty');
      try {
        localStorage.setItem(`usaer_borrador_plan_${docId}`, JSON.stringify(next));
      } catch (_) {}
      return next;
    });
  };
  React.useEffect(() => {
    if (saveStatus === 'dirty') {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        persistir(doc);
      }, 1500);
    }
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [doc, saveStatus, persistir]);
  if (loading || !doc) {
    return /*#__PURE__*/React.createElement("div", {
      className: "text-center py-24 bg-white rounded-xl border border-slate-200"
    }, /*#__PURE__*/React.createElement("div", {
      className: "inline-block animate-spin text-amber-600 text-3xl mb-3"
    }, "\u25C8"), /*#__PURE__*/React.createElement("p", {
      className: "text-slate-600 text-sm font-medium"
    }, "Abriendo planeaci\xF3n oficial..."));
  }

  // Compatibilidad canónica con todas las variantes de Streamlit
  const tablaNEE = ((_doc$tablas4 = doc.tablas) === null || _doc$tablas4 === void 0 ? void 0 : _doc$tablas4.nee) || ((_doc$tablas5 = doc.tablas) === null || _doc$tablas5 === void 0 ? void 0 : _doc$tablas5.aprendizajes) || ((_doc$tablas6 = doc.tablas) === null || _doc$tablas6 === void 0 ? void 0 : _doc$tablas6["Tabla principal"]) || [];
  const tablaDosificacion = ((_doc$tablas7 = doc.tablas) === null || _doc$tablas7 === void 0 ? void 0 : _doc$tablas7.dosificacion) || [];
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, borradorDisponible && /*#__PURE__*/React.createElement("div", {
    className: "bg-amber-50 border border-amber-300 p-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between text-xs text-amber-900 gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "font-bold"
  }, "\u26A0\uFE0F Borrador local detectado:"), " Tienes una versi\xF3n previa no sincronizada en este dispositivo."), /*#__PURE__*/React.createElement("div", {
    className: "flex space-x-2"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      setDoc(borradorDisponible);
      setBorradorDisponible(null);
      setSaveStatus('dirty');
    },
    className: "bg-amber-600 text-white px-3 py-1 rounded-lg font-bold hover:bg-amber-700 transition"
  }, "Restaurar Borrador"), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      try {
        localStorage.removeItem(`usaer_borrador_plan_${docId}`);
      } catch (_) {}
      setBorradorDisponible(null);
    },
    className: "bg-slate-200 text-slate-700 px-3 py-1 rounded-lg hover:bg-slate-300 transition"
  }, "Descartar"))), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 text-xs font-semibold transition"
  }, "\u2190 Volver a Mis Documentos"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$metadatos = doc.metadatos) === null || _doc$metadatos === void 0 ? void 0 : _doc$metadatos.titulo) || '',
    onChange: e => mutarDoc(d => ({
      ...d,
      metadatos: {
        ...d.metadatos,
        titulo: e.target.value
      }
    })),
    className: "font-bold text-slate-900 text-base md:text-lg border-b border-transparent hover:border-slate-300 focus:border-amber-500 focus:outline-none px-1 w-full max-w-lg",
    placeholder: "T\xEDtulo del Plan de Intervenci\xF3n"
  }), /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 px-1 flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "Escuela: ", ((_doc$datos2 = doc.datos) === null || _doc$datos2 === void 0 ? void 0 : _doc$datos2.Escuela) || ((_doc$datos3 = doc.datos) === null || _doc$datos3 === void 0 ? void 0 : _doc$datos3["Escuela regular"]) || 'Primaria Oficial'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Docente: ", ((_doc$datos4 = doc.datos) === null || _doc$datos4 === void 0 ? void 0 : _doc$datos4.Docente_Especialista) || ((_doc$datos5 = doc.datos) === null || _doc$datos5 === void 0 ? void 0 : _doc$datos5["Nombre del docente especialista"]) || 'USAER 2E'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Revisi\xF3n: ", doc.revision)))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2.5"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs font-medium px-3 py-1.5 rounded-lg border bg-slate-50 border-slate-200 flex items-center space-x-2"
  }, saveStatus === 'saved' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-emerald-500"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-600"
  }, "Guardado confirmado")), saveStatus === 'saving' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-amber-500 animate-ping"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-amber-700 font-semibold animate-saving"
  }, "Guardando cambios...")), saveStatus === 'dirty' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-amber-400"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500"
  }, "Cambios pendientes")), saveStatus === 'conflict' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-red-500"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-red-700 font-semibold"
  }, "Conflicto de edici\xF3n")), saveStatus === 'error' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-red-400"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-red-600"
  }, "Error al guardar"))), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => descargarArchivoAutenticado(`/api/planeaciones/${doc.id}/pdf`, `Planeacion_${doc.id}.pdf`),
    className: "px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm"
  }, /*#__PURE__*/React.createElement("span", null, "Descargar PDF"), /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCC4")), /*#__PURE__*/React.createElement("button", {
    onClick: () => setAssistantOpen(!assistantOpen),
    className: `px-3.5 py-1.5 rounded-lg text-xs font-bold shadow-sm transition flex items-center space-x-1.5 ${assistantOpen ? 'bg-amber-600 text-white ring-2 ring-amber-400' : 'bg-amber-50 text-amber-800 border border-amber-300 hover:bg-amber-100'}`
  }, /*#__PURE__*/React.createElement("span", null, "\uD83E\uDD16 Asistente IA")))), conflictError && /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-red-50 border border-red-300 rounded-xl text-xs text-red-800 flex items-center justify-between shadow-sm"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Aviso de Concurrencia:"), " ", conflictError), /*#__PURE__*/React.createElement("button", {
    onClick: fetchDoc,
    className: "px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold transition ml-3 shadow"
  }, "Sincronizar y Recargar")), typeof ((_doc$metadatos2 = doc.metadatos) === null || _doc$metadatos2 === void 0 ? void 0 : _doc$metadatos2.guia_grupal_manual) === 'string' && doc.metadatos.guia_grupal_manual && /*#__PURE__*/React.createElement("div", {
    className: "bg-blue-50/60 border border-blue-200 rounded-xl p-3.5 text-xs space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-blue-900"
  }, "\uD83D\uDCD8 Gu\xEDa Grupal de Intervenci\xF3n (Streamlit Hist\xF3rico)"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-700 whitespace-pre-wrap"
  }, doc.metadatos.guia_grupal_manual)), /*#__PURE__*/React.createElement("div", {
    className: "flex border-b border-slate-200 space-x-1 text-sm font-semibold overflow-x-auto"
  }, [{
    id: 'aprendizajes',
    label: '1. NEE y Descriptores Observables'
  }, {
    id: 'dosificacion',
    label: '2. Dosificación y Actividades'
  }, {
    id: 'evaluacion',
    label: '3. Evaluación Formativa'
  }, {
    id: 'aportaciones',
    label: '4. Aportaciones Interdisciplinarias'
  }, {
    id: 'firmas',
    label: '5. Firmas y Vo. Bo. Oficial'
  }].map(tab => /*#__PURE__*/React.createElement("button", {
    key: tab.id,
    onClick: () => setActiveTab(tab.id),
    className: `px-4 py-2.5 border-b-2 font-bold transition text-xs sm:text-sm whitespace-nowrap ${activeTab === tab.id ? 'border-amber-600 text-amber-700 bg-amber-50/50' : 'border-transparent text-slate-500 hover:text-slate-800'}`
  }, tab.label))), /*#__PURE__*/React.createElement("div", {
    className: "flex gap-4 items-start"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm min-h-[420px]"
  }, activeTab === 'aprendizajes' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Barreras, PDA y Descriptores Individualizados"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Indicador 5: Redactar con ", /*#__PURE__*/React.createElement("strong", null, "Sujeto + Verbo en Presente + Complemento Observable"), ".")), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      const nuevaFila = {
        alumno: 'Nuevo Alumno',
        Alumno: 'Nuevo Alumno',
        barreras_o_necesidades: 'Atención sostenida en lectura guiada.',
        'Necesidades educativas específicas': 'Atención sostenida en lectura guiada.',
        pda: 'Identifica ideas clave con apoyo visual.',
        'Aprendizaje y/u objetivo': 'Identifica ideas clave con apoyo visual.',
        descriptor: 'El alumno identifica elementos clave con apoyo visual.',
        'Descriptor de logro': 'El alumno identifica elementos clave con apoyo visual.',
        'Descriptor Observable': 'El alumno identifica elementos clave con apoyo visual.',
        apoyos: 'Cronómetro visual y tarjetas léxicas.',
        'Apoyos y Ajustes': 'Cronómetro visual y tarjetas léxicas.'
      };
      mutarDoc(d => ({
        ...d,
        tablas: {
          ...d.tablas,
          nee: [...tablaNEE, nuevaFila],
          aprendizajes: [...tablaNEE, nuevaFila]
        }
      }));
    },
    className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold"
  }, "+ Agregar Alumno a Planeaci\xF3n")), /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-xs text-left border-collapse"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    className: "bg-slate-50 text-slate-600 border-b border-slate-200 font-bold"
  }, /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Alumno"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Aprendizaje / PDA (Objetivo)"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Barrera o Necesidad (BAP)"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Descriptor Observable (Zona 001)"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Apoyos y Ajustes Razonables"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-8"
  }))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, tablaNEE.map((row, idx) => {
    var _alumnosEnPlaneacion$;
    return /*#__PURE__*/React.createElement("tr", {
      key: idx,
      className: "hover:bg-slate-50/70 transition"
    }, /*#__PURE__*/React.createElement("td", {
      className: "p-2"
    }, /*#__PURE__*/React.createElement("input", {
      type: "text",
      value: row.alumno || row.Alumno || ((_alumnosEnPlaneacion$ = alumnosEnPlaneacion[0]) === null || _alumnosEnPlaneacion$ === void 0 ? void 0 : _alumnosEnPlaneacion$.nombre) || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const copy = [...tablaNEE];
          copy[idx] = {
            ...copy[idx],
            alumno: val,
            Alumno: val
          };
          return {
            ...d,
            tablas: {
              ...d.tablas,
              nee: copy,
              aprendizajes: copy
            }
          };
        });
      },
      placeholder: "Nombre del Alumno",
      className: "w-full p-1.5 border border-slate-200 rounded font-semibold text-slate-800 focus:outline-none focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("td", {
      className: "p-2"
    }, /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: row.pda || row["Aprendizaje y/u objetivo"] || row.objetivo || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const copy = [...tablaNEE];
          copy[idx] = {
            ...copy[idx],
            pda: val,
            "Aprendizaje y/u objetivo": val,
            objetivo: val
          };
          return {
            ...d,
            tablas: {
              ...d.tablas,
              nee: copy,
              aprendizajes: copy
            }
          };
        });
      },
      placeholder: "Aprendizaje y/u objetivo curricular (PDA)...",
      className: "w-full p-1.5 border border-slate-200 rounded text-slate-700 focus:outline-none focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("td", {
      className: "p-2"
    }, /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: row.barreras_o_necesidades || row["Necesidades educativas específicas"] || row["Barrera o Necesidad"] || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const copy = [...tablaNEE];
          copy[idx] = {
            ...copy[idx],
            barreras_o_necesidades: val,
            "Necesidades educativas específicas": val,
            "Barrera o Necesidad": val
          };
          return {
            ...d,
            tablas: {
              ...d.tablas,
              nee: copy,
              aprendizajes: copy
            }
          };
        });
      },
      placeholder: "Barrera para el Aprendizaje o Necesidad...",
      className: "w-full p-1.5 border border-slate-200 rounded text-slate-700 focus:outline-none focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("td", {
      className: "p-2"
    }, /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: row.descriptor || row["Descriptor de logro"] || row["Descriptor Observable"] || row.descriptor_observable || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const copy = [...tablaNEE];
          copy[idx] = {
            ...copy[idx],
            descriptor: val,
            "Descriptor de logro": val,
            "Descriptor Observable": val
          };
          return {
            ...d,
            tablas: {
              ...d.tablas,
              nee: copy,
              aprendizajes: copy
            }
          };
        });
      },
      className: "w-full p-1.5 border border-amber-300 bg-amber-50/30 rounded text-slate-900 font-medium focus:outline-none focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("td", {
      className: "p-2"
    }, /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: row.apoyos || row["Apoyos y Ajustes"] || row["Apoyos o ajustes"] || row.ajustes_razonables || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const copy = [...tablaNEE];
          copy[idx] = {
            ...copy[idx],
            apoyos: val,
            "Apoyos y Ajustes": val,
            "Apoyos o ajustes": val,
            ajustes_razonables: val
          };
          return {
            ...d,
            tablas: {
              ...d.tablas,
              nee: copy,
              aprendizajes: copy
            }
          };
        });
      },
      className: "w-full p-1.5 border border-slate-200 rounded text-slate-700 focus:outline-none focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("td", {
      className: "p-2 text-center"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        mutarDoc(d => ({
          ...d,
          tablas: {
            ...d.tablas,
            nee: tablaNEE.filter((_, i) => i !== idx),
            aprendizajes: tablaNEE.filter((_, i) => i !== idx)
          }
        }));
      },
      className: "text-slate-400 hover:text-red-600 font-bold p-1"
    }, "\u2715")));
  }))))), activeTab === 'dosificacion' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Secuencia Did\xE1ctica y Modalidad"), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      const nuevaSesion = {
        Contextos: 'Aula de apoyo',
        contextos: 'Aula de apoyo',
        semana: 'Semana ' + (tablaDosificacion.length + 1),
        Actividades: 'Actividad de intervención pedagógica individual / grupal.',
        actividad: 'Actividad de intervención pedagógica individual / grupal.',
        Recursos: 'Material didáctico y apoyos visuales.',
        recursos: 'Material didáctico y apoyos visuales.',
        Temporalidad: '45 minutos',
        temporalidad: '45 minutos',
        "Ajustes Razonables": 'Pausas activas y estructuración secuencial.',
        ajustes_razonables: 'Pausas activas y estructuración secuencial.'
      };
      mutarDoc(d => ({
        ...d,
        tablas: {
          ...d.tablas,
          dosificacion: [...tablaDosificacion, nuevaSesion]
        }
      }));
    },
    className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold"
  }, "+ Agregar Sesi\xF3n")), /*#__PURE__*/React.createElement("div", {
    className: "space-y-3"
  }, tablaDosificacion.map((dos, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-3 border border-slate-200 rounded-xl bg-slate-50/50 space-y-2 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: dos.Contextos || dos.contextos || dos.semana || dos.modalidad || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[i] = {
          ...copy[i],
          Contextos: val,
          semana: val,
          contextos: val
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            dosificacion: copy
          }
        };
      });
    },
    className: "font-bold text-slate-800 bg-white px-2 py-1 border border-slate-200 rounded text-xs",
    placeholder: "Contexto / Modalidad (ej. Aula de apoyo)"
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      mutarDoc(d => ({
        ...d,
        tablas: {
          ...d.tablas,
          dosificacion: tablaDosificacion.filter((_, idx) => idx !== i)
        }
      }));
    },
    className: "text-red-500 hover:text-red-700 text-xs font-semibold"
  }, "Eliminar")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-3 gap-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "md:col-span-2 space-y-1"
  }, /*#__PURE__*/React.createElement("label", {
    className: "text-[10px] uppercase font-bold text-slate-400"
  }, "Actividades:"), /*#__PURE__*/React.createElement("textarea", {
    rows: "3",
    value: dos.Actividades || dos.actividades || dos.actividad || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[i] = {
          ...copy[i],
          Actividades: val,
          actividades: val,
          actividad: val
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            dosificacion: copy
          }
        };
      });
    },
    className: "w-full p-2 border border-slate-200 rounded bg-white text-slate-800",
    placeholder: "Descripci\xF3n de la actividad pedag\xF3gica..."
  })), /*#__PURE__*/React.createElement("div", {
    className: "space-y-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "text-[10px] uppercase font-bold text-slate-400"
  }, "Temporalidad / Per\xEDodo:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: dos.Temporalidad || dos.temporalidad || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[i] = {
          ...copy[i],
          Temporalidad: val,
          temporalidad: val
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            dosificacion: copy
          }
        };
      });
    },
    className: "w-full p-1.5 border border-slate-200 rounded bg-white text-xs mb-1.5",
    placeholder: "ej. Octubre 2026 / 45 min..."
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "text-[10px] uppercase font-bold text-slate-400"
  }, "Recursos:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: dos.Recursos || dos.recursos || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[i] = {
          ...copy[i],
          Recursos: val,
          recursos: val
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            dosificacion: copy
          }
        };
      });
    },
    className: "w-full p-1.5 border border-slate-200 rounded bg-white text-xs",
    placeholder: "Materiales y recursos..."
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "text-[10px] uppercase font-bold text-slate-400"
  }, "Ajustes Razonables:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: dos["Ajustes Razonables"] || dos.ajustes_razonables || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[i] = {
          ...copy[i],
          "Ajustes Razonables": val,
          ajustes_razonables: val
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            dosificacion: copy
          }
        };
      });
    },
    className: "w-full p-1.5 border border-slate-200 rounded bg-white text-xs",
    placeholder: "Ajustes espec\xEDficos..."
  })))))))), activeTab === 'evaluacion' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-5"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Criterios e Instrumentos de Evaluaci\xF3n Formativa"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500 mb-2"
  }, "Registra los indicadores de logro formativo y r\xFAbricas de la Zona 001."), /*#__PURE__*/React.createElement("textarea", {
    rows: "5",
    value: ((_doc$textos = doc.textos) === null || _doc$textos === void 0 ? void 0 : _doc$textos['Evaluación']) || ((_doc$textos2 = doc.textos) === null || _doc$textos2 === void 0 ? void 0 : _doc$textos2.evaluacion) || ((_doc$textos3 = doc.textos) === null || _doc$textos3 === void 0 ? void 0 : _doc$textos3.criterios_evaluacion) || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => ({
        ...d,
        textos: {
          ...d.textos,
          'Evaluación': val,
          evaluacion: val,
          criterios_evaluacion: val
        }
      }));
    },
    className: "w-full p-3 border border-slate-200 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-amber-500",
    placeholder: "Registra los indicadores de logro formativo y r\xFAbricas de la Zona 001..."
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Observaciones Generales de la Intervenci\xF3n"), /*#__PURE__*/React.createElement("textarea", {
    rows: "4",
    value: ((_doc$textos4 = doc.textos) === null || _doc$textos4 === void 0 ? void 0 : _doc$textos4['Observaciones']) || ((_doc$textos5 = doc.textos) === null || _doc$textos5 === void 0 ? void 0 : _doc$textos5.observaciones) || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => ({
        ...d,
        textos: {
          ...d.textos,
          'Observaciones': val,
          observaciones: val
        }
      }));
    },
    className: "w-full p-3 border border-slate-200 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-amber-500",
    placeholder: "Notas pedag\xF3gicas u observaciones de seguimiento..."
  }))), activeTab === 'aportaciones' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-5"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Aportaciones del Equipo Multidisciplinario"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Espacio de colaboraci\xF3n t\xE9cnica para Aprendizaje, Psicolog\xEDa, Comunicaci\xF3n y Trabajo Social."))), ['Aprendizaje', 'Psicología', 'Comunicación', 'Trabajo Social'].map(areaName => {
    var _doc$metadatos3;
    const aportes = (_doc$metadatos3 = doc.metadatos) === null || _doc$metadatos3 === void 0 ? void 0 : _doc$metadatos3.aportaciones_equipo;
    const aporteInfo = typeof aportes === 'object' && aportes !== null ? aportes[areaName] : null;
    const puedeEditar = Boolean((user === null || user === void 0 ? void 0 : user.director) || (user === null || user === void 0 ? void 0 : user.area) === areaName || !(user !== null && user !== void 0 && user.area) && (user === null || user === void 0 ? void 0 : user.rol) === areaName.toUpperCase());
    return /*#__PURE__*/React.createElement("div", {
      key: areaName,
      className: "p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between border-b border-slate-100 pb-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-base"
    }, areaName === 'Aprendizaje' ? '📖' : areaName === 'Psicología' ? '🧠' : areaName === 'Comunicación' ? '🗣️' : '👥'), /*#__PURE__*/React.createElement("span", {
      className: "font-bold text-slate-900 text-sm"
    }, areaName), puedeEditar && /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded border border-emerald-200"
    }, "Tu \xC1rea / Autorizado para Editar")), /*#__PURE__*/React.createElement("span", {
      className: "text-xs text-slate-500"
    }, aporteInfo !== null && aporteInfo !== void 0 && aporteInfo.autor ? `${aporteInfo.autor} (${aporteInfo.fecha ? aporteInfo.fecha.slice(0, 10) : 'Registrado'})` : 'Sin aportación registrada aún')), /*#__PURE__*/React.createElement("div", {
      className: "space-y-1"
    }, /*#__PURE__*/React.createElement("label", {
      className: "text-[11px] font-bold text-slate-600 uppercase"
    }, "Observaciones y Estrategias T\xE9cnicas:"), puedeEditar ? /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: (aporteInfo === null || aporteInfo === void 0 ? void 0 : aporteInfo.observaciones) || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          const meta = {
            ...(d.metadatos || {})
          };
          const ae = typeof meta.aportaciones_equipo === 'object' && meta.aportaciones_equipo !== null ? {
            ...meta.aportaciones_equipo
          } : {};
          const currentAporte = ae[areaName] || {};
          ae[areaName] = {
            ...currentAporte,
            observaciones: val,
            autor: (user === null || user === void 0 ? void 0 : user.nombre) || currentAporte.autor || 'Especialista',
            cuenta: (user === null || user === void 0 ? void 0 : user.usuario) || currentAporte.cuenta || '',
            fecha: new Date().toISOString()
          };
          return {
            ...d,
            metadatos: {
              ...meta,
              aportaciones_equipo: ae
            }
          };
        });
      },
      className: "w-full p-2 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-amber-500",
      placeholder: `Registra las observaciones y sugerencias de ${areaName}...`
    }) : /*#__PURE__*/React.createElement("div", {
      className: "p-2.5 bg-slate-50 rounded text-xs text-slate-700 whitespace-pre-wrap"
    }, (aporteInfo === null || aporteInfo === void 0 ? void 0 : aporteInfo.observaciones) || 'No hay observaciones específicas registradas para esta área.')));
  }), typeof ((_doc$metadatos4 = doc.metadatos) === null || _doc$metadatos4 === void 0 ? void 0 : _doc$metadatos4.aportaciones_equipo) === 'string' && doc.metadatos.aportaciones_equipo && /*#__PURE__*/React.createElement("div", {
    className: "p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl text-xs space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-amber-900"
  }, "Nota Hist\xF3rica Migrada de Streamlit:"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-700 whitespace-pre-wrap"
  }, doc.metadatos.aportaciones_equipo))), activeTab === 'firmas' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-6 max-w-2xl mx-auto py-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-amber-50/50 border border-amber-200 rounded-xl text-xs text-slate-700 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-amber-900"
  }, "Validaci\xF3n de Firmas Oficiales de Zona 001"), /*#__PURE__*/React.createElement("p", null, "Las firmas se computan autom\xE1ticamente desde el personal asignado a la escuela y la Direcci\xF3n de USAER 2E.")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 sm:grid-cols-2 gap-6 pt-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 border-2 border-dashed border-slate-300 rounded-xl text-center space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-400 uppercase font-semibold"
  }, "Elabor\xF3"), /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, ((_doc$firmas_resueltas = doc.firmas_resueltas) === null || _doc$firmas_resueltas === void 0 ? void 0 : _doc$firmas_resueltas.elaboro) || ((_doc$datos6 = doc.datos) === null || _doc$datos6 === void 0 ? void 0 : _doc$datos6.Docente_Especialista) || 'Docente Especialista USAER'), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-500"
  }, "Maestra de Apoyo / \xC1rea Especialista")), /*#__PURE__*/React.createElement("div", {
    className: "p-4 border-2 border-dashed border-amber-400 bg-amber-50/20 rounded-xl text-center space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-amber-700 uppercase font-bold"
  }, "Vo. Bo. Direcci\xF3n USAER"), /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, ((_doc$firmas_resueltas2 = doc.firmas_resueltas) === null || _doc$firmas_resueltas2 === void 0 ? void 0 : _doc$firmas_resueltas2.vo_bo) || 'Psic. Edgar Adrián Yam Briceño MD'), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-500"
  }, "Director USAER 02-E"))), doc.observaciones_director && /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-800"
  }, "Observaciones del Director:"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, doc.observaciones_director)))), assistantOpen && /*#__PURE__*/React.createElement("div", {
    className: "w-80 md:w-96 bg-white border border-slate-200 rounded-xl shadow-lg p-4 flex flex-col h-[520px]"
  }, /*#__PURE__*/React.createElement("div", {
    className: "mb-2 pb-2 border-b border-slate-100 flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs font-bold text-slate-700"
  }, "Enfoque de Alumno:"), /*#__PURE__*/React.createElement("select", {
    value: activeAlumnoId,
    onChange: e => setActiveAlumnoId(e.target.value),
    className: "text-xs font-semibold bg-amber-50 border border-amber-300 rounded px-2 py-1 max-w-[200px] truncate"
  }, alumnosEnPlaneacion.length > 0 ? alumnosEnPlaneacion.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre)) : /*#__PURE__*/React.createElement("option", {
    value: ""
  }, "(Sin alumno asignado)"))), /*#__PURE__*/React.createElement(PedagogicalChatComponent, {
    alumnoId: activeAlumnoId,
    onInsertProposal: propuesta => {
      mutarDoc(d => {
        var _alumnosEnPlaneacion$2;
        const aluNom = propuesta.alumno || ((_alumnosEnPlaneacion$2 = alumnosEnPlaneacion.find(a => a.id === activeAlumnoId)) === null || _alumnosEnPlaneacion$2 === void 0 ? void 0 : _alumnosEnPlaneacion$2.nombre) || 'Alumno';
        const nuevaFila = {
          alumno: aluNom,
          Alumno: aluNom,
          id_alumno: activeAlumnoId,
          barreras_o_necesidades: propuesta.barrera || propuesta.barreras_o_necesidades || 'Barrera identificada',
          'Necesidades educativas específicas': propuesta.barrera || propuesta.barreras_o_necesidades || 'Barrera identificada',
          pda: propuesta.pda || propuesta.aprendizaje || '',
          'Aprendizaje y/u objetivo': propuesta.pda || propuesta.aprendizaje || '',
          descriptor: propuesta.descriptor || propuesta.descriptor_observable || 'El alumno demuestra desempeño observable.',
          'Descriptor de logro': propuesta.descriptor || propuesta.descriptor_observable || 'El alumno demuestra desempeño observable.',
          'Descriptor Observable': propuesta.descriptor || propuesta.descriptor_observable || 'El alumno demuestra desempeño observable.',
          apoyos: propuesta.apoyos || propuesta.ajustes_razonables || 'Apoyos visuales y estructurados.',
          'Apoyos y Ajustes': propuesta.apoyos || propuesta.ajustes_razonables || 'Apoyos visuales y estructurados.'
        };
        return {
          ...d,
          tablas: {
            ...d.tablas,
            nee: [...tablaNEE, nuevaFila],
            aprendizajes: [...tablaNEE, nuevaFila]
          }
        };
      });
    }
  }))));
}

// =============================================================
// COMPONENTE: ASISTENTE PEDAGÓGICO IA
// =============================================================
function PedagogicalChatComponent({
  alumnoId,
  onInsertProposal
}) {
  const [messages, setMessages] = React.useState([{
    sender: 'ai',
    text: 'Hola. Soy el Asistente Pedagógico de USAER 02-E. Puedo sugerir descriptores observables para tus alumnos alineados a los 14 indicadores de la Zona 001. ¿En qué aprendizaje o ajuste estás trabajando?'
  }]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [lastProposal, setLastProposal] = React.useState(null);
  const handleSend = async e => {
    if (e) e.preventDefault();
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, {
      sender: 'user',
      text: userMsg
    }]);
    setInput('');
    setLoading(true);
    try {
      const res = await apiRequest('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          mensaje: userMsg,
          alumno_id: alumnoId
        })
      });
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: res.respuesta
      }]);
      if (res.propuesta_tabla) {
        setLastProposal(res.propuesta_tabla);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        sender: 'ai',
        text: 'Error consultando el motor pedagógico.'
      }]);
    } finally {
      setLoading(false);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col h-full space-y-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center border-b border-slate-100 pb-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-amber-600 font-bold"
  }, "\uD83E\uDD16"), /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-xs text-slate-800"
  }, "Asistente Pedag\xF3gico Zona 001")), /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold"
  }, "Activo")), /*#__PURE__*/React.createElement("div", {
    className: "flex-1 overflow-y-auto space-y-2 text-xs pr-1"
  }, messages.map((m, idx) => /*#__PURE__*/React.createElement("div", {
    key: idx,
    className: `p-2.5 rounded-xl ${m.sender === 'user' ? 'bg-amber-600 text-white ml-6 font-medium' : 'bg-slate-50 text-slate-800 mr-2 border border-slate-200'}`
  }, /*#__PURE__*/React.createElement("div", {
    className: "whitespace-pre-wrap"
  }, m.text))), loading && /*#__PURE__*/React.createElement("div", {
    className: "p-2.5 bg-slate-50 rounded-xl text-slate-400 text-xs italic"
  }, "Elaborando propuesta contextualizada...")), lastProposal && /*#__PURE__*/React.createElement("div", {
    className: "p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1.5"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-amber-900 text-[11px]"
  }, "Propuesta lista para insertar:"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600 text-[11px] truncate"
  }, "\"", lastProposal.descriptor, "\""), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      onInsertProposal(lastProposal);
      setLastProposal(null);
    },
    className: "w-full py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded font-bold text-xs shadow-sm transition"
  }, "+ Insertar en Planeaci\xF3n (1 Clic)")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleSend,
    className: "flex gap-2"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: input,
    onChange: e => setInput(e.target.value),
    placeholder: "Instrucci\xF3n pedag\xF3gica...",
    className: "flex-1 px-3 py-2 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500"
  }), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: loading,
    className: "px-3 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition disabled:opacity-50"
  }, "Enviar")));
}

// =============================================================
// VISTA 3: EXPEDIENTES INTEGRALES (307 ALUMNOS, LÍNEA DE TIEMPO)
// =============================================================
function ExpedientesView({
  initialAlumnoId,
  onBack,
  setMetrics
}) {
  var _expediente$alumno, _expediente$alumno2, _expediente$alumno3, _expediente$alumno4, _expediente$alumno5, _expediente$alumno6, _expediente$alumno7, _expediente$anexo3_ba, _expediente$anexo4_su, _expediente$anexo5_ev, _expediente$alumno8, _expediente$alumno9, _expediente$alumno10, _expediente$alumno11, _expediente$anexo3_ba2, _expediente$anexo4_su2, _expediente$anexo5_ev2, _expediente$anexo7_de, _expediente$anexo7_de2, _expediente$anexo7_de3, _expediente$anexo7_de4;
  const [alumnos, setAlumnos] = React.useState([]);
  const [loadingAlumnos, setLoadingAlumnos] = React.useState(true);
  const [errorAlumnos, setErrorAlumnos] = React.useState(null);
  const [busqueda, setBusqueda] = React.useState('');
  const [filtroMaestra, setFiltroMaestra] = React.useState('TODAS');
  const [selectedId, setSelectedId] = React.useState(initialAlumnoId || null);
  const [expediente, setExpediente] = React.useState(null);
  const [loadingExp, setLoadingExp] = React.useState(false);
  const [activeExpTab, setActiveExpTab] = React.useState('resumen');
  React.useEffect(() => {
    setLoadingAlumnos(true);
    setErrorAlumnos(null);
    apiRequest('/api/alumnos').then(data => {
      const list = Array.isArray(data) ? data : [];
      setAlumnos(list);
      setLoadingAlumnos(false);
      if (!selectedId && list.length > 0) {
        setSelectedId(list[0].id);
      }
    }).catch(err => {
      console.error("Error al cargar padrón de alumnos:", err);
      setErrorAlumnos(err.message || 'Error cargando padrón');
      setLoadingAlumnos(false);
    });
  }, []);
  React.useEffect(() => {
    if (!selectedId) return;
    setLoadingExp(true);
    const t0 = performance.now();
    apiRequest(`/api/expedientes/${selectedId}`).then(exp => {
      setExpediente(exp);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 1
      }));
      setLoadingExp(false);
    }).catch(() => setLoadingExp(false));
  }, [selectedId, setMetrics]);
  const maestrasDisponibles = Array.from(new Set(alumnos.map(a => a.maestra_apoyo || a['Maestra de Apoyo']).filter(Boolean))).sort();
  const alumnosFiltrados = alumnos.filter(al => {
    const nom = (al.nombre_completo || al.Nombre_Completo || al.nombre || '').toLowerCase();
    const curp = (al.curp || al.CURP || '').toLowerCase();
    const esc = (al.escuela || al.Nombre_Escuela || al.Escuela || '').toLowerCase();
    const q = (busqueda || '').toLowerCase();
    const matchesBusqueda = !q || nom.includes(q) || curp.includes(q) || esc.includes(q);
    const m = al.maestra_apoyo || al['Maestra de Apoyo'] || '';
    const matchesMaestra = filtroMaestra === 'TODAS' || m === filtroMaestra;
    return matchesBusqueda && matchesMaestra;
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver a Mis Documentos"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Expedientes de Alumnos")), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/alumnos/exportar', 'Padron_Alumnos_USAER_2E.csv'),
    className: "text-xs px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg border border-slate-300 transition cursor-pointer"
  }, "Exportar Padr\xF3n CSV \uD83D\uDCE5")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 lg:grid-cols-12 gap-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "lg:col-span-4 bg-white p-4 rounded-xl border border-slate-200 space-y-3 self-start"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-xs uppercase text-slate-500 tracking-wider"
  }, "Matr\xEDcula de Atenci\xF3n"), /*#__PURE__*/React.createElement("span", {
    className: "text-[11px] font-bold bg-amber-50 text-amber-800 px-2 py-0.5 rounded-full border border-amber-200"
  }, alumnosFiltrados.length, " alumnos")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por nombre, CURP, escuela...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
  }), maestrasDisponibles.length > 1 && /*#__PURE__*/React.createElement("div", {
    className: "space-y-1"
  }, /*#__PURE__*/React.createElement("label", {
    className: "text-[10px] uppercase font-bold text-slate-400"
  }, "Filtrar por Maestra:"), /*#__PURE__*/React.createElement("select", {
    value: filtroMaestra,
    onChange: e => setFiltroMaestra(e.target.value),
    className: "w-full text-xs p-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium text-slate-700 focus:outline-none"
  }, /*#__PURE__*/React.createElement("option", {
    value: "TODAS"
  }, "Todas las maestras de la escuela"), maestrasDisponibles.map(m => /*#__PURE__*/React.createElement("option", {
    key: m,
    value: m
  }, m)))), loadingAlumnos ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-8 text-xs text-slate-400"
  }, "Cargando matr\xEDcula de atenci\xF3n...") : errorAlumnos ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-6 text-xs text-red-500 bg-red-50 rounded-lg p-3"
  }, /*#__PURE__*/React.createElement("div", null, "\u26A0\uFE0F ", errorAlumnos), /*#__PURE__*/React.createElement("button", {
    onClick: () => location.reload(),
    className: "mt-2 text-[11px] underline font-bold text-amber-700"
  }, "Reintentar")) : alumnosFiltrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-8 text-xs text-slate-400"
  }, "No se encontraron alumnos para tu escuela o criterio de b\xFAsqueda.") : /*#__PURE__*/React.createElement("div", {
    className: "space-y-1.5 max-h-96 overflow-y-auto pr-1"
  }, alumnosFiltrados.map(al => /*#__PURE__*/React.createElement("div", {
    key: al.id,
    onClick: () => setSelectedId(al.id),
    className: `p-2.5 rounded-lg text-xs cursor-pointer transition ${selectedId === al.id ? 'bg-amber-100/70 border border-amber-300 font-bold text-slate-900' : 'hover:bg-slate-50 text-slate-700'}`
  }, /*#__PURE__*/React.createElement("div", null, al.nombre_completo || al.Nombre_Completo), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-500"
  }, al.grado, "\xB0 ", al.grupo, " \u2022 ", al.escuela), /*#__PURE__*/React.createElement("div", {
    className: "text-[10px] text-amber-700 font-semibold mt-0.5"
  }, "\uD83D\uDC64 ", al.maestra_apoyo))))), /*#__PURE__*/React.createElement("div", {
    className: "lg:col-span-8 bg-white p-6 rounded-xl border border-slate-200 space-y-5"
  }, loadingAlumnos ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando padr\xF3n escolar...") : alumnos.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-2xl mb-2"
  }, "\uD83D\uDCCB"), /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-700"
  }, "No hay alumnos asignados a este perfil o escuela."), /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-400 mt-1"
  }, "Si perteneces a una escuela espec\xEDfica, verifica haber iniciado sesi\xF3n con tu cuenta correspondiente.")) : loadingExp || !expediente ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando expediente integral desde base relacional...") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "border-b border-slate-200 pb-4 flex justify-between items-start"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    className: "text-xl font-bold text-slate-900"
  }, (_expediente$alumno = expediente.alumno) === null || _expediente$alumno === void 0 ? void 0 : _expediente$alumno.nombre_completo), /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 mt-1"
  }, /*#__PURE__*/React.createElement("span", null, "ID: ", (_expediente$alumno2 = expediente.alumno) === null || _expediente$alumno2 === void 0 ? void 0 : _expediente$alumno2.id), /*#__PURE__*/React.createElement("span", {
    className: "mx-2"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "CURP: ", ((_expediente$alumno3 = expediente.alumno) === null || _expediente$alumno3 === void 0 ? void 0 : _expediente$alumno3.curp) || 'No registrada'), /*#__PURE__*/React.createElement("span", {
    className: "mx-2"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", null, (_expediente$alumno4 = expediente.alumno) === null || _expediente$alumno4 === void 0 ? void 0 : _expediente$alumno4.escuela), /*#__PURE__*/React.createElement("span", {
    className: "mx-2"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Grado: ", (_expediente$alumno5 = expediente.alumno) === null || _expediente$alumno5 === void 0 ? void 0 : _expediente$alumno5.grado, "\xB0 ", (_expediente$alumno6 = expediente.alumno) === null || _expediente$alumno6 === void 0 ? void 0 : _expediente$alumno6.grupo))), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, ((_expediente$alumno7 = expediente.alumno) === null || _expediente$alumno7 === void 0 ? void 0 : _expediente$alumno7.condicion) || 'Atención USAER')), /*#__PURE__*/React.createElement("div", {
    className: "flex border-b border-slate-200 space-x-1 text-xs font-bold overflow-x-auto pb-1"
  }, [{
    id: 'resumen',
    label: 'Resumen e Historia'
  }, {
    id: 'epp',
    label: 'Evaluación Psicopedagógica (EPP)'
  }, {
    id: 'bap',
    label: `BAP (${((_expediente$anexo3_ba = expediente.anexo3_bap) === null || _expediente$anexo3_ba === void 0 ? void 0 : _expediente$anexo3_ba.length) || 0})`
  }, {
    id: 'sugerencias',
    label: `Sugerencias (${((_expediente$anexo4_su = expediente.anexo4_sugerencias) === null || _expediente$anexo4_su === void 0 ? void 0 : _expediente$anexo4_su.length) || 0})`
  }, {
    id: 'eventos',
    label: `Eventos (${((_expediente$anexo5_ev = expediente.anexo5_eventos) === null || _expediente$anexo5_ev === void 0 ? void 0 : _expediente$anexo5_ev.length) || 0})`
  }, {
    id: 'derivacion',
    label: 'Derivación y Salud'
  }].map(t => /*#__PURE__*/React.createElement("button", {
    key: t.id,
    onClick: () => setActiveExpTab(t.id),
    className: `px-3 py-2 border-b-2 whitespace-nowrap transition ${activeExpTab === t.id ? 'border-amber-600 text-amber-800 bg-amber-50/50' : 'border-transparent text-slate-400 hover:text-slate-700'}`
  }, t.label))), activeExpTab === 'resumen' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-4 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-700"
  }, "Maestra de Apoyo Asignada"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-900"
  }, ((_expediente$alumno8 = expediente.alumno) === null || _expediente$alumno8 === void 0 ? void 0 : _expediente$alumno8.maestra_apoyo) || 'Por asignar')), /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-700"
  }, "Tipo de Atenci\xF3n"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-900"
  }, ((_expediente$alumno9 = expediente.alumno) === null || _expediente$alumno9 === void 0 ? void 0 : _expediente$alumno9.tipo_atencion) || 'Atención Focalizada')), /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-700"
  }, "Turno y CCT"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-900"
  }, (_expediente$alumno10 = expediente.alumno) === null || _expediente$alumno10 === void 0 ? void 0 : _expediente$alumno10.turno, " \u2022 ", (_expediente$alumno11 = expediente.alumno) === null || _expediente$alumno11 === void 0 ? void 0 : _expediente$alumno11.cct)), /*#__PURE__*/React.createElement("div", {
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-700"
  }, "Documentos Vinculados"), /*#__PURE__*/React.createElement("div", {
    className: "text-amber-700 font-bold"
  }, expediente.total_documentos, " registros en expediente"))), expediente.linea_tiempo && expediente.linea_tiempo.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "pt-2 space-y-2"
  }, /*#__PURE__*/React.createElement("h4", {
    className: "text-xs font-bold uppercase text-slate-600"
  }, "\uD83D\uDCDC L\xEDnea de Tiempo del Expediente (", expediente.linea_tiempo.length, ")"), /*#__PURE__*/React.createElement("div", {
    className: "space-y-1.5 max-h-56 overflow-y-auto pr-1"
  }, expediente.linea_tiempo.map((lt, idx) => /*#__PURE__*/React.createElement("div", {
    key: idx,
    className: "p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs flex justify-between items-start"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "font-semibold text-slate-800"
  }, lt.tipo || lt.evento || 'Evento de Expediente'), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600 text-[11px] mt-0.5"
  }, lt.descripcion || lt.detalle || '')), /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] text-slate-400 font-mono ml-3"
  }, lt.fecha || '2026-2027')))))), activeExpTab === 'epp' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-3 text-xs"
  }, expediente.epp ? /*#__PURE__*/React.createElement("div", {
    className: "space-y-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center text-slate-500"
  }, /*#__PURE__*/React.createElement("span", null, "Ciclo Escolar: ", expediente.epp.ciclo), /*#__PURE__*/React.createElement("span", null, "Revisi\xF3n: ", expediente.epp.revision)), Object.entries(expediente.epp.partes || {}).map(([area, datos]) => {
    if (area === 'META') return null;
    return /*#__PURE__*/React.createElement("div", {
      key: area,
      className: "p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "font-bold text-slate-900 uppercase tracking-wider text-[11px] text-amber-700"
    }, "\xC1rea: ", area), typeof datos === 'object' ? Object.entries(datos).map(([k, v]) => /*#__PURE__*/React.createElement("div", {
      key: k,
      className: "text-slate-700"
    }, /*#__PURE__*/React.createElement("strong", {
      className: "text-slate-800"
    }, k.replace(/_/g, ' '), ":"), " ", String(v))) : /*#__PURE__*/React.createElement("div", {
      className: "text-slate-700"
    }, String(datos)));
  })) : /*#__PURE__*/React.createElement("div", {
    className: "text-center py-8 text-slate-500"
  }, "No hay Evaluaci\xF3n Psicopedag\xF3gica cargada para este ciclo.")), activeExpTab === 'bap' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 text-xs"
  }, (_expediente$anexo3_ba2 = expediente.anexo3_bap) === null || _expediente$anexo3_ba2 === void 0 ? void 0 : _expediente$anexo3_ba2.map(b => /*#__PURE__*/React.createElement("div", {
    key: b.id,
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-800"
  }, /*#__PURE__*/React.createElement("span", null, "Detecci\xF3n BAP ", b.tipo_deteccion === 'GRUPAL' ? '· GRUPAL DE AULA' : ''), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, b.fecha)), b.fisicas && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "F\xEDsicas:"), " ", b.fisicas), b.actitudinales && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Actitudinales:"), " ", b.actitudinales), b.pedagogicas && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Pedag\xF3gicas:"), " ", b.pedagogicas), b.organizativas && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Organizativas:"), " ", b.organizativas)))), activeExpTab === 'sugerencias' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 text-xs"
  }, (_expediente$anexo4_su2 = expediente.anexo4_sugerencias) === null || _expediente$anexo4_su2 === void 0 ? void 0 : _expediente$anexo4_su2.map(sug => /*#__PURE__*/React.createElement("div", {
    key: sug.id,
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-800"
  }, /*#__PURE__*/React.createElement("span", null, "\xC1rea: ", sug.area), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, sug.fecha)), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Sugerencias:"), " ", sug.sugerencias), sug.motivo && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Motivo:"), " ", sug.motivo), sug.cumplimiento && /*#__PURE__*/React.createElement("div", {
    className: "text-amber-800"
  }, /*#__PURE__*/React.createElement("strong", null, "Resultado:"), " ", sug.cumplimiento)))), activeExpTab === 'eventos' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 text-xs"
  }, (_expediente$anexo5_ev2 = expediente.anexo5_eventos) === null || _expediente$anexo5_ev2 === void 0 ? void 0 : _expediente$anexo5_ev2.map(ev => /*#__PURE__*/React.createElement("div", {
    key: ev.id,
    className: "p-3 bg-slate-50 rounded-xl border border-slate-200 flex justify-between items-start"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-800"
  }, ev.especialista), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600 mt-1"
  }, ev.evento)), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-mono text-[11px] whitespace-nowrap ml-4"
  }, ev.fecha)))), activeExpTab === 'derivacion' && /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900"
  }, "Anexo VII \u2014 Formato de Derivaci\xF3n"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Docente Regular:"), " ", ((_expediente$anexo7_de = expediente.anexo7_derivacion) === null || _expediente$anexo7_de === void 0 ? void 0 : _expediente$anexo7_de.docente_regular) || 'No registrado'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Salud:"), " ", ((_expediente$anexo7_de2 = expediente.anexo7_derivacion) === null || _expediente$anexo7_de2 === void 0 ? void 0 : _expediente$anexo7_de2.salud) || 'Buena salud reportada'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Seguimiento M\xE9dico:"), " ", ((_expediente$anexo7_de3 = expediente.anexo7_derivacion) === null || _expediente$anexo7_de3 === void 0 ? void 0 : _expediente$anexo7_de3.seguimiento_medico) || 'Sin seguimiento activo'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Aspecto Relevante:"), " ", ((_expediente$anexo7_de4 = expediente.anexo7_derivacion) === null || _expediente$anexo7_de4 === void 0 ? void 0 : _expediente$anexo7_de4.aspecto_relevante) || 'Ninguno'))))));
}

// =============================================================
// VISTA 4: EVALUACIÓN PSICOPEDAGÓGICA (EPP MULTI-ÁREA VIVA)
// =============================================================
function EPPView({
  onBack,
  onOpenAlumno,
  setMetrics
}) {
  const [listaEPP, setListaEPP] = React.useState([]);
  const [alumnosList, setAlumnosList] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedAlumnoId, setSelectedAlumnoId] = React.useState(null);
  const [eppDoc, setEppDoc] = React.useState(null);
  const [loadingDoc, setLoadingDoc] = React.useState(false);
  const [activeArea, setActiveArea] = React.useState('Aprendizaje');
  const [guardando, setGuardando] = React.useState(false);
  const [guardadoExito, setGuardadoExito] = React.useState(false);
  const [busqueda, setBusqueda] = React.useState('');
  const cargarLista = React.useCallback(async () => {
    setLoading(true);
    const t0 = performance.now();
    try {
      const [epps, alus] = await Promise.all([apiRequest('/api/epp'), apiRequest('/api/alumnos')]);
      setListaEPP(epps || []);
      setAlumnosList(alus || []);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 2
      }));
    } catch (err) {
      console.error("Error cargando lista EPP:", err);
    } finally {
      setLoading(false);
    }
  }, [setMetrics]);
  React.useEffect(() => {
    cargarLista();
  }, [cargarLista]);
  const abrirEPP = async alumnoId => {
    setSelectedAlumnoId(alumnoId);
    setLoadingDoc(true);
    setGuardadoExito(false);
    try {
      const doc = await apiRequest(`/api/epp/${alumnoId}`);
      setEppDoc(doc);
    } catch (err) {
      console.error("Error abriendo EPP:", err);
      alert("Error abriendo informe EPP: " + err.message);
    } finally {
      setLoadingDoc(false);
    }
  };
  const guardarEPP = async () => {
    if (!eppDoc) return;
    setGuardando(true);
    setGuardadoExito(false);
    try {
      await apiRequest('/api/epp', {
        method: 'POST',
        body: JSON.stringify({
          id: eppDoc.id || `epp-${selectedAlumnoId}`,
          alumno: selectedAlumnoId,
          ciclo: eppDoc.ciclo || '2026-2027',
          partes: eppDoc.partes || {}
        })
      });
      setGuardadoExito(true);
      setTimeout(() => setGuardadoExito(false), 3000);
      cargarLista();
    } catch (err) {
      console.error("Error guardando EPP:", err);
      alert("Error al guardar EPP: " + err.message);
    } finally {
      setGuardando(false);
    }
  };
  const mutarParte = (area, campo, valor) => {
    setEppDoc(prev => {
      if (!prev) return prev;
      const partes = {
        ...prev.partes
      };
      const areaObj = {
        ...(partes[area] || {})
      };
      areaObj[campo] = valor;
      partes[area] = areaObj;
      return {
        ...prev,
        partes
      };
    });
  };
  const filtrados = listaEPP.filter(e => {
    const nom = (e.nombre_alumno || e.alumno_nombre || '').toLowerCase();
    const esc = (e.escuela || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q) || (e.alumno_id || '').toLowerCase().includes(q);
  });
  const alumnoSeleccionadoInfo = alumnosList.find(a => a.id === selectedAlumnoId) || {};
  if (selectedAlumnoId && eppDoc) {
    const partes = eppDoc.partes || {};
    const pAprendizaje = partes.Aprendizaje || partes.APRENDIZAJE || {};
    const pPsicologia = partes.Psicología || partes.PSICOLOGIA || {};
    const pComunicacion = partes.Comunicación || partes.COMUNICACION || {};
    const pTrabajoSocial = partes['Trabajo Social'] || partes.TRABAJO_SOCIAL || {};
    const pConclusion = partes.Conclusión || partes.CONCLUSION || {};
    return /*#__PURE__*/React.createElement("div", {
      className: "space-y-5"
    }, /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-3"
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => {
        setSelectedAlumnoId(null);
        setEppDoc(null);
      },
      className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
    }, "\u2190 Volver a Lista EPP"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
      className: "text-lg font-bold text-slate-900"
    }, alumnoSeleccionadoInfo.nombre_completo || eppDoc.nombre_alumno || selectedAlumnoId), /*#__PURE__*/React.createElement("div", {
      className: "text-xs text-slate-500"
    }, "Escuela: ", alumnoSeleccionadoInfo.escuela || 'USAER 2E', " \u2022 Ciclo: ", eppDoc.ciclo || '2026-2027', " \u2022 Revisi\xF3n: ", eppDoc.revision || 'Actual'))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, guardadoExito && /*#__PURE__*/React.createElement("span", {
      className: "text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200"
    }, "\u2713 Guardado confirmado"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => descargarArchivoAutenticado(`/api/epp/${selectedAlumnoId}/pdf`, `EPP_${selectedAlumnoId}.pdf`),
      className: "px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm"
    }, /*#__PURE__*/React.createElement("span", null, "Descargar PDF (Anexo XVII)"), /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCC4")), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: guardarEPP,
      disabled: guardando,
      className: "px-4 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow"
    }, /*#__PURE__*/React.createElement("span", null, guardando ? 'Guardando...' : '💾 Guardar EPP')))), /*#__PURE__*/React.createElement("div", {
      className: "flex border-b border-slate-200 space-x-1 text-sm font-semibold overflow-x-auto"
    }, [{
      id: 'Aprendizaje',
      label: '1. Área Pedagógica / Aprendizaje'
    }, {
      id: 'Psicología',
      label: '2. Área de Psicología'
    }, {
      id: 'Comunicación',
      label: '3. Área de Comunicación'
    }, {
      id: 'Trabajo Social',
      label: '4. Área de Trabajo Social'
    }, {
      id: 'Conclusión',
      label: '5. Conclusión, BAP y NEE'
    }].map(tab => /*#__PURE__*/React.createElement("button", {
      key: tab.id,
      onClick: () => setActiveArea(tab.id),
      className: `px-4 py-2.5 border-b-2 font-bold transition text-xs sm:text-sm whitespace-nowrap ${activeArea === tab.id ? 'border-amber-600 text-amber-700 bg-amber-50/50' : 'border-transparent text-slate-500 hover:text-slate-800'}`
    }, tab.label))), activeArea === 'Aprendizaje' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "Evaluaci\xF3n Pedag\xF3gica del Aprendizaje"), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-1 md:grid-cols-2 gap-4 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Estilo de Aprendizaje Predominante:"), /*#__PURE__*/React.createElement("input", {
      type: "text",
      value: pAprendizaje.estilo_aprendizaje || pAprendizaje['5.2. Estilo de aprendizaje'] || '',
      onChange: e => mutarParte('Aprendizaje', 'estilo_aprendizaje', e.target.value),
      placeholder: "ej. Visual y kinest\xE9sico, requiere apoyos gr\xE1ficos...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Nivel de Competencia Curricular:"), /*#__PURE__*/React.createElement("input", {
      type: "text",
      value: pAprendizaje.nivel_competencia_curricular || pAprendizaje['5.1. Competencia curricular'] || '',
      onChange: e => mutarParte('Aprendizaje', 'nivel_competencia_curricular', e.target.value),
      placeholder: "ej. Fase 3 / 2\xB0 Primaria en proceso...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Lectura y Escritura Funcional:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pAprendizaje['4.1. Lectura y escritura funcional'] || '',
      onChange: e => mutarParte('Aprendizaje', '4.1. Lectura y escritura funcional', e.target.value),
      placeholder: "Nivel presil\xE1bico/sil\xE1bico, reconocimiento de graf\xEDas, segmentaci\xF3n...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Pensamiento Matem\xE1tico Funcional:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pAprendizaje['4.1. Matemáticas funcionales'] || '',
      onChange: e => mutarParte('Aprendizaje', '4.1. Matemáticas funcionales', e.target.value),
      placeholder: "Conteo oral, resoluci\xF3n de problemas con material concreto, correspondencia 1 a 1...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Conceptos Relativos al Dinero y Vida Diaria:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pAprendizaje['4.1. Conceptos relativos al dinero'] || '',
      onChange: e => mutarParte('Aprendizaje', '4.1. Conceptos relativos al dinero', e.target.value),
      placeholder: "Reconocimiento de monedas/billetes, uso aut\xF3nomo en transacciones b\xE1sicas...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Avances Observables y Desempe\xF1o en Aula:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pAprendizaje.avances_observables || '',
      onChange: e => mutarParte('Aprendizaje', 'avances_observables', e.target.value),
      placeholder: "Logros observables en el per\xEDodo de evaluaci\xF3n...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Apoyos y Ajustes Razonables Requeridos:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pAprendizaje.apoyos_requeridos || '',
      onChange: e => mutarParte('Aprendizaje', 'apoyos_requeridos', e.target.value),
      placeholder: "Ajustes DUA, temporales, materiales y espaciales...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })))), activeArea === 'Psicología' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "Evaluaci\xF3n Psicol\xF3gica y Madurativa"), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Atenci\xF3n y Concentraci\xF3n:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia['3.1. Atención'] || pPsicologia.atencion_y_memoria || '',
      onChange: e => mutarParte('Psicología', '3.1. Atención', e.target.value),
      placeholder: "Focalizaci\xF3n, sostenimiento, distractores visuales o auditivos...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Memoria y Procesamiento Cognitivo:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia['3.2. Memoria'] || '',
      onChange: e => mutarParte('Psicología', '3.2. Memoria', e.target.value),
      placeholder: "Memoria inmediata auditivo-verbal, retenci\xF3n secuencial...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Percepci\xF3n Visomotora e Integraci\xF3n (Bender / Koppitz / Frostig):"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia['3.3. Percepción'] || '',
      onChange: e => mutarParte('Psicología', '3.3. Percepción', e.target.value),
      placeholder: "Edad visomotora equivalente, indicadores neurol\xF3gicos o de madurez...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Desarrollo Socioemocional, Autoestima y Conducta:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia.desarrollo_emocional || pPsicologia['4.2. Autoestima'] || '',
      onChange: e => mutarParte('Psicología', 'desarrollo_emocional', e.target.value),
      placeholder: "Autorregulaci\xF3n, interacci\xF3n con pares y figuras de autoridad...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Recomendaciones y Estrategias Espec\xEDficas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia.recomendaciones || '',
      onChange: e => mutarParte('Psicología', 'recomendaciones', e.target.value),
      placeholder: "Pautas psicol\xF3gicas para el docente regular y la familia...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })))), activeArea === 'Comunicación' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "Evaluaci\xF3n de la Comunicaci\xF3n y el Lenguaje"), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Comprensi\xF3n Receptiva y Seguimiento de Instrucciones:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pComunicacion['4.1. Comprensión receptiva'] || pComunicacion.lenguaje_comprensivo || '',
      onChange: e => mutarParte('Comunicación', '4.1. Comprensión receptiva', e.target.value),
      placeholder: "Comprensi\xF3n en interacci\xF3n social y seguimiento de consignas acad\xE9micas...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Expresi\xF3n Oral y Articulaci\xF3n Fonol\xF3gica:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pComunicacion['4.1. Comprensión expresiva'] || pComunicacion['4.1. Lenguaje oral: fonológico'] || pComunicacion.lenguaje_expresivo || '',
      onChange: e => mutarParte('Comunicación', '4.1. Comprensión expresiva', e.target.value),
      placeholder: "Articulaci\xF3n, repertorio l\xE9xico, estructuraci\xF3n sint\xE1ctica...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Pragm\xE1tica e Intenci\xF3n Comunicativa:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pComunicacion['4.1. Lenguaje oral: pragmático'] || pComunicacion['4.1. Comunicación y lenguaje: intención comunicativa'] || '',
      onChange: e => mutarParte('Comunicación', '4.1. Lenguaje oral: pragmático', e.target.value),
      placeholder: "Contacto visual, turnos de habla, adaptaci\xF3n al contexto escolar...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Recomendaciones y Estrategias Comunicativas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pComunicacion.recomendaciones || '',
      onChange: e => mutarParte('Comunicación', 'recomendaciones', e.target.value),
      placeholder: "Estrategias de modelado, apoyos visuales, sistemas aumentativos si aplica...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })))), activeArea === 'Trabajo Social' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "Estudio y Contexto Sociofamiliar"), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Din\xE1mica Familiar y Cuidadores Principales:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pTrabajoSocial.dinamica_familiar || pTrabajoSocial['6.2. Contexto familiar'] || '',
      onChange: e => mutarParte('Trabajo Social', 'dinamica_familiar', e.target.value),
      placeholder: "Composici\xF3n del hogar, roles parentales, pautas de crianza...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Antecedentes de Embarazo, Parto y Salud Temprana:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pTrabajoSocial['2.1. Embarazo'] || pTrabajoSocial['2.2. Parto'] || pTrabajoSocial['2.4. Salud'] || '',
      onChange: e => mutarParte('Trabajo Social', '2.1. Embarazo', e.target.value),
      placeholder: "Gestaci\xF3n, complicaciones pre/perinatales, antecedentes m\xE9dicos...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Autonom\xEDa en el Hogar y Utilizaci\xF3n de la Comunidad:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pTrabajoSocial['4.3. Autocuidado'] || pTrabajoSocial['4.3. Actividades en la casa'] || pTrabajoSocial['4.3. Utilización de la comunidad'] || '',
      onChange: e => mutarParte('Trabajo Social', '4.3. Autocuidado', e.target.value),
      placeholder: "Higiene personal, responsabilidades en casa, desenvolvimiento en el entorno...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Acuerdos y Compromisos de la Familia:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pTrabajoSocial.acuerdos_casa || '',
      onChange: e => mutarParte('Trabajo Social', 'acuerdos_casa', e.target.value),
      placeholder: "Compromisos asumidos por los tutores para el seguimiento escolar...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })))), activeArea === 'Conclusión' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "S\xEDntesis Interdisciplinaria, BAP y NEE Oficiales"), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "S\xEDntesis Diagn\xF3stica Integral (7.1):"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pConclusion.sintesis || pConclusion['7.1. Conclusión'] || '',
      onChange: e => mutarParte('Conclusión', 'sintesis', e.target.value),
      placeholder: "Conclusi\xF3n diagn\xF3stica consensuada por el equipo interdisciplinario...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "\xC9nfasis de Atenci\xF3n y Apoyos Acordados:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pConclusion['Énfasis de atención acordado'] || pConclusion['Acuerdos y apoyos del equipo'] || '',
      onChange: e => mutarParte('Conclusión', 'Énfasis de atención acordado', e.target.value),
      placeholder: "Prioridades de intervenci\xF3n y acuerdos entre USAER y Escuela Regular...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
    })))));
  }
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Evaluaci\xF3n Psicopedag\xF3gica (EPP)"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Gesti\xF3n de informes cl\xEDnicos y pedag\xF3gicos oficiales (Anexos XVII y XVIII)"))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " Evaluaciones Disponibles"))), /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row gap-3"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar evaluaci\xF3n por nombre de alumno, escuela o ID...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "flex-1 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 shadow-sm"
  }), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("select", {
    onChange: e => {
      if (e.target.value) abrirEPP(e.target.value);
    },
    className: "px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition shadow",
    defaultValue: ""
  }, /*#__PURE__*/React.createElement("option", {
    value: "",
    disabled: true
  }, "+ Abrir / Evaluar Alumno..."), alumnosList.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre_completo, " (", a.escuela || 'USAER', ")"))))), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-20 bg-white rounded-xl border border-slate-200"
  }, /*#__PURE__*/React.createElement("div", {
    className: "inline-block animate-spin text-amber-600 text-3xl mb-3"
  }, "\u25C8"), /*#__PURE__*/React.createElement("p", {
    className: "text-slate-600 text-sm font-medium"
  }, "Cargando evaluaciones psicopedag\xF3gicas...")) : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-4"
  }, filtrados.map(epp => /*#__PURE__*/React.createElement("div", {
    key: epp.id,
    className: "p-4 bg-white rounded-xl border border-slate-200 space-y-3 shadow-sm hover:border-amber-300 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row sm:items-center justify-between gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-base"
  }, epp.nombre_alumno || epp.alumno_nombre || epp.alumno_id || epp.id), /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500"
  }, "ID: ", /*#__PURE__*/React.createElement("span", {
    className: "font-mono font-bold text-slate-700"
  }, epp.alumno_id || epp.id), " \u2022 Escuela: ", epp.escuela || 'Primaria', " \u2022 Ciclo: ", epp.ciclo || '2026-2027', " \u2022 Revisi\xF3n: ", epp.revision || 'Actual')), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => descargarArchivoAutenticado(`/api/epp/${epp.alumno_id || epp.id}/pdf`, `EPP_${epp.alumno_id || epp.id}.pdf`),
    className: "text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg border border-slate-200 transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCC4 PDF")), /*#__PURE__*/React.createElement("button", {
    onClick: () => abrirEPP(epp.alumno_id || epp.id),
    className: "text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 px-3 py-1.5 rounded-lg shadow transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "Editar EPP Viva \u2192")), /*#__PURE__*/React.createElement("button", {
    onClick: () => onOpenAlumno(epp.alumno_id || epp.id),
    className: "text-xs font-semibold text-slate-500 hover:text-slate-800 px-2 py-1.5 transition"
  }, "Expediente"))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 text-xs"
  }, ['Aprendizaje', 'Psicología', 'Comunicación', 'Trabajo Social'].map(area => {
    const tieneDatos = Array.isArray(epp.areas_registradas) && (epp.areas_registradas.includes(area) || epp.areas_registradas.includes(area.toUpperCase()));
    return /*#__PURE__*/React.createElement("div", {
      key: area,
      className: `p-2.5 rounded-lg border ${tieneDatos ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' : 'bg-slate-50 border-slate-200 text-slate-500'}`
    }, /*#__PURE__*/React.createElement("div", {
      className: "font-bold flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("span", null, area), /*#__PURE__*/React.createElement("span", null, tieneDatos ? '✓' : '•')), /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] mt-0.5"
    }, tieneDatos ? 'Evaluación registrada' : 'Pendiente de captura'));
  }))))));
}

// =============================================================
// VISTA 5: ANEXO III - DETECCIÓN DE BAP (INDIVIDUAL Y GRUPAL)
// =============================================================
function Anexo3View({
  onBack,
  setMetrics
}) {
  const [baps, setBaps] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/anexo3').then(data => {
      setBaps(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const filtrados = baps.filter(b => {
    const nom = (b.nombre_alumno || b.Nombre_Alumno || '').toLowerCase();
    const esc = (b.escuela || b.Escuela || '').toLowerCase();
    const fis = (b.fisicas || b.Fisicas || '').toLowerCase();
    const ped = (b.pedagogicas || b.Pedagogicas || b.Curriculares || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q) || fis.includes(q) || ped.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo III \u2014 Detecci\xF3n de BAP")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " registros")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, escuela o barrera...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando detecciones de BAP...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay registros de BAP para este criterio de b\xFAsqueda o escuela asignada.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, filtrados.map((b, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-2 hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, b.nombre_alumno || b.Nombre_Alumno || 'Detección Grupal'), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, b.fecha || b.Fecha), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/anexo3/${b.id || b.ID_Anexo3 || b.id_alumno || b.ID_Alumno}/pdf`, `Anexo_III_${b.id || b.ID_Anexo3 || b.id_alumno || b.ID_Alumno}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Anexo III Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500"
  }, "Escuela: ", b.escuela || b.Escuela, " \u2022 Alumno/Grupo: ", b.id_alumno || b.ID_Alumno), (b.fisicas || b.Fisicas) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "F\xEDsicas/Arquitect\xF3nicas:"), " ", b.fisicas || b.Fisicas), (b.actitudinales || b.Actitudinales) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Actitudinales:"), " ", b.actitudinales || b.Actitudinales), (b.pedagogicas || b.Pedagogicas || b.Curriculares) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Curriculares/Pedag\xF3gicas:"), " ", b.pedagogicas || b.Pedagogicas || b.Curriculares), (b.organizativas || b.Organizativas) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Organizativas:"), " ", b.organizativas || b.Organizativas)))));
}

// =============================================================
// VISTA 6: ANEXO IV - HOJA DE SUGERENCIAS
// =============================================================
function Anexo4View({
  onBack,
  setMetrics
}) {
  const [sugerencias, setSugerencias] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/anexo4').then(data => {
      setSugerencias(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const filtradas = sugerencias.filter(s => {
    const nom = (s.nombre_alumno || s.Nombre_Alumno || s.Alumno || '').toLowerCase();
    const sug = (s.sugerencias || s.Sugerencias || '').toLowerCase();
    const area = (s.area || s.Area || '').toLowerCase();
    const esc = (s.escuela || s.Escuela || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || sug.includes(q) || area.includes(q) || esc.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo IV \u2014 Hojas de Sugerencias")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtradas.length, " hojas")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, \xE1rea o contenido...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando hojas de sugerencias...") : filtradas.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay hojas de sugerencias registradas para este criterio o escuela asignada.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, filtradas.map((s, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-2 hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, s.nombre_alumno || s.Nombre_Alumno || s.Alumno || 'Sugerencias de Grupo'), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, s.fecha || s.Fecha), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/anexo4/${s.id || s.ID_Anexo4 || s.id_alumno || s.ID_Alumno}/pdf`, `Anexo_IV_${s.id || s.ID_Anexo4 || s.id_alumno || s.ID_Alumno}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Anexo IV Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500"
  }, /*#__PURE__*/React.createElement("span", null, "\xC1rea: ", /*#__PURE__*/React.createElement("strong", {
    className: "text-amber-800"
  }, s.area || s.Area || 'Pedagógica')), /*#__PURE__*/React.createElement("span", {
    className: "mx-2"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Especialista: ", s.docente_especialista || s.Docente_Especialista || s.Especialista || 'USAER'), (s.escuela || s.Escuela) && /*#__PURE__*/React.createElement("span", null, " \u2022 Escuela: ", s.escuela || s.Escuela)), (s.motivo || s.Motivo) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Motivo:"), " ", s.motivo || s.Motivo), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Sugerencias para el Docente Regular:"), " ", s.sugerencias || s.Sugerencias), (s.cumplimiento || s.Cumplimiento) && /*#__PURE__*/React.createElement("div", {
    className: "text-emerald-700"
  }, /*#__PURE__*/React.createElement("strong", null, "Resultado / Seguimiento:"), " ", s.cumplimiento || s.Cumplimiento)))));
}

// =============================================================
// VISTA 7: ANEXO V - EVENTOS SIGNIFICATIVOS (408 REGISTROS)
// =============================================================
function Anexo5View({
  onBack,
  setMetrics
}) {
  const [eventos, setEventos] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/anexo5').then(data => {
      setEventos(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const filtrados = eventos.filter(ev => {
    const nom = (ev.nombre_alumno || ev.Nombre_Alumno || ev.alumno_nombre || '').toLowerCase();
    const txt = (ev.evento || ev.Evento || '').toLowerCase();
    const esp = (ev.especialista || ev.Especialista || '').toLowerCase();
    const esc = (ev.escuela || ev.Escuela || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || txt.includes(q) || esp.includes(q) || esc.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo V \u2014 Eventos Significativos")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " eventos hist\xF3ricos")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, especialista o descripci\xF3n del evento...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando eventos significativos...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay eventos significativos registrados en tu b\xFAsqueda.") : /*#__PURE__*/React.createElement("div", {
    className: "space-y-2"
  }, filtrados.map((ev, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-3.5 bg-white rounded-xl border border-slate-200 text-xs flex justify-between items-start hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, ev.nombre_alumno || ev.Nombre_Alumno || ev.alumno_nombre || 'Alumno USAER'), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-700"
  }, ev.evento || ev.Evento), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-500"
  }, /*#__PURE__*/React.createElement("span", null, "Registrado por: ", /*#__PURE__*/React.createElement("strong", null, ev.especialista || ev.Especialista)), (ev.escuela || ev.Escuela) && /*#__PURE__*/React.createElement("span", {
    className: "ml-2"
  }, "\u2022 Escuela: ", ev.escuela || ev.Escuela))), /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col items-end space-y-2 ml-4"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-mono text-xs whitespace-nowrap"
  }, ev.fecha || ev.Fecha), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/anexo5/${ev.id || ev.ID_Evento || ev.id_alumno || ev.ID_Alumno}/pdf`, `Anexo_V_${ev.id || ev.ID_Evento || ev.id_alumno || ev.ID_Alumno}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Anexo V Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))))));
}

// =============================================================
// VISTA 8: ANEXO VII - DERIVACIÓN Y SEGUIMIENTO MÉDICO
// =============================================================
function Anexo7View({
  onBack,
  setMetrics
}) {
  const [derivaciones, setDerivaciones] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/anexo7').then(data => {
      setDerivaciones(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo VII \u2014 Derivaci\xF3n y Salud")), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando derivaciones...") : derivaciones.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay derivaciones m\xE9dicas ni de salud registradas para tus alumnos.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, derivaciones.map((d, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-2 hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, d.nombre_alumno || d.Nombre_Alumno || d.Alumno), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, d.fecha || d.Fecha), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/anexo7/${d.id || d.ID_Anexo7 || d.id_alumno || d.ID_Alumno}/pdf`, `Anexo_VII_${d.id || d.ID_Anexo7 || d.id_alumno || d.ID_Alumno}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Anexo VII Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))), (d.escuela || d.Escuela) && /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 font-semibold"
  }, "Escuela: ", d.escuela || d.Escuela), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Docente Regular:"), " ", d.docente_regular || d.Docente_Regular || 'No registrado'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Salud:"), " ", d.salud || d.Salud || 'Buena salud'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Seguimiento M\xE9dico:"), " ", d.seguimiento_medico || d.Seguimiento_Medico || 'En observación'), (d.aspecto_relevante || d.Aspecto_Relevante) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Aspecto Relevante:"), " ", d.aspecto_relevante || d.Aspecto_Relevante)))));
}

// =============================================================
// VISTA 9: HORARIOS DE APOYO
// =============================================================
function HorariosView({
  onBack,
  setMetrics
}) {
  var _horarios$horarios_ap, _horarios$restriccion, _horarios$borradores;
  const [horarios, setHorarios] = React.useState(null);
  React.useEffect(() => {
    apiRequest('/api/horarios').then(setHorarios);
  }, []);
  if (!horarios) return /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando horarios de apoyo...");
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Horarios de Apoyo Semanal")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-3 gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Sesiones de Apoyo Registradas"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-amber-600 mt-1"
  }, ((_horarios$horarios_ap = horarios.horarios_apoyo) === null || _horarios$horarios_ap === void 0 ? void 0 : _horarios$horarios_ap.length) || 0)), /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Restricciones de Aula"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-slate-900 mt-1"
  }, ((_horarios$restriccion = horarios.restricciones) === null || _horarios$restriccion === void 0 ? void 0 : _horarios$restriccion.length) || 0)), /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Borradores de Horarios"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-emerald-600 mt-1"
  }, ((_horarios$borradores = horarios.borradores) === null || _horarios$borradores === void 0 ? void 0 : _horarios$borradores.length) || 0))), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-5 rounded-xl border border-slate-200 space-y-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-sm"
  }, "Distribuci\xF3n de Apoyo en Escuelas"), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-2 max-h-96 overflow-y-auto"
  }, (horarios.horarios_apoyo || []).slice(0, 30).map((h, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-900"
  }, h.Dia || 'Lunes', " \u2022 ", h.Hora || '08:00'), /*#__PURE__*/React.createElement("span", {
    className: "mx-2"
  }, "\u2022"), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-600"
  }, h.Escuela, " (", h.Grado_Grupo, ")")), /*#__PURE__*/React.createElement("span", {
    className: "text-amber-800 font-semibold"
  }, h.Maestra_Apoyo || h.Especialista))))));
}

// =============================================================
// VISTA 10: CRONOGRAMA MENSUAL
// =============================================================
function CronogramasView({
  onBack,
  setMetrics
}) {
  const [cronogramas, setCronogramas] = React.useState(null);
  React.useEffect(() => {
    apiRequest('/api/cronogramas').then(setCronogramas);
  }, []);
  if (!cronogramas) return /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando cronogramas mensuales...");
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Cronogramas Mensuales del Equipo")), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, (cronogramas.cronogramas || []).map((c, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, c.Personal || c.Especialista, " \u2014 ", c.Mes || 'Mensual'), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, c.Ciclo || '2026-2027')), /*#__PURE__*/React.createElement("div", null, c.Actividad || c.Detalle || 'Actividades de acompañamiento técnico en escuelas asignadas.')))));
}

// =============================================================
// VISTA 11: CALENDARIO DE ACTIVIDADES SEGEY / USAER (130 EVENTOS)
// =============================================================
function CalendarioView({
  onBack,
  setMetrics
}) {
  const [eventos, setEventos] = React.useState([]);
  const [filtroMes, setFiltroMes] = React.useState('TODOS');
  React.useEffect(() => {
    apiRequest('/api/calendario').then(setEventos);
  }, []);
  const meses = ['TODOS', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio'];
  const filtrados = eventos.filter(ev => {
    if (filtroMes === 'TODOS') return true;
    return (ev.mes || ev.Mes || '').toLowerCase().includes(filtroMes.toLowerCase());
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Calendario Oficial de Actividades SEGEY / USAER")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " actividades")), /*#__PURE__*/React.createElement("div", {
    className: "flex space-x-2 overflow-x-auto pb-2 text-xs"
  }, meses.map(m => /*#__PURE__*/React.createElement("button", {
    key: m,
    onClick: () => setFiltroMes(m),
    className: `px-3 py-1.5 rounded-lg font-bold transition whitespace-nowrap ${filtroMes === m ? 'bg-amber-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}`
  }, m))), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-2.5"
  }, filtrados.map((ev, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-3.5 bg-white rounded-xl border border-slate-200 text-xs flex justify-between items-center shadow-sm"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, ev.actividad || ev.Actividad || ev.nombre), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 mt-0.5"
  }, ev.tipo || 'Actividad Institucional', " \u2022 ", ev.responsable || 'Dirección / Zona')), /*#__PURE__*/React.createElement("span", {
    className: "text-amber-800 font-bold bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200 whitespace-nowrap ml-4"
  }, ev.fecha || ev.Fecha)))));
}

// =============================================================
// VISTA 12: DOCENTES REGULARES (71 MAESTROS DE PRIMARIA)
// =============================================================
function DocentesRegularesView({
  onBack,
  setMetrics
}) {
  const [docentes, setDocentes] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/docentes-regulares').then(data => {
      setDocentes(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const filtrados = docentes.filter(d => {
    const nom = (d.nombre_docente || d.Nombre_Docente || d.Nombre || d.Docente || '').toLowerCase();
    const esc = (d.nombre_escuela || d.Nombre_Escuela || d.Escuela || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Directorio de Maestros de Primaria (7 Escuelas)")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " maestros")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por nombre de maestro o escuela primaria...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando directorio docente...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No se encontraron docentes regulares con ese criterio.") : /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
  }, filtrados.map((d, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-3.5 bg-white rounded-xl border border-slate-200 text-xs space-y-1 shadow-sm hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, d.nombre_docente || d.Nombre_Docente || d.Nombre || d.Docente), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, "Escuela: ", d.nombre_escuela || d.Nombre_Escuela || d.Escuela), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500"
  }, /*#__PURE__*/React.createElement("span", null, "Grado y Grupo: ", /*#__PURE__*/React.createElement("strong", null, d.grado || d.Grado, " ", d.grupo || d.Grupo)), (d.turno || d.Turno) && /*#__PURE__*/React.createElement("span", {
    className: "ml-2"
  }, "\u2022 ", d.turno || d.Turno)), (d.telefono || d.Telefono) && /*#__PURE__*/React.createElement("div", {
    className: "text-slate-400 text-[11px]"
  }, "\uD83D\uDCDE ", d.telefono || d.Telefono), (d.email || d.Email) && /*#__PURE__*/React.createElement("div", {
    className: "text-slate-400 text-[11px]"
  }, "\u2709\uFE0F ", d.email || d.Email)))));
}

// =============================================================
// VISTA 13: NOVEDADES DE SUPERVISIÓN (111 DOCUMENTOS ZONA 001)
// =============================================================
function NovedadesView({
  onBack,
  setMetrics
}) {
  const [novedades, setNovedades] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/novedades').then(data => {
      setNovedades(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  const filtradas = novedades.filter(n => {
    const tit = (n.Nombre || n.nombre || n.Titulo || n.asunto || n.Asunto || '').toLowerCase();
    const ext = (n.Extracto || n.extracto || n.Descripcion || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return tit.includes(q) || ext.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Novedades de Supervisi\xF3n \xB7 ATP Zona 001")), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtradas.length, " documentos oficiales")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar en circulares y documentos oficiales...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando circulares oficiales...") : filtradas.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No se encontraron novedades o circulares con ese criterio.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-2.5"
  }, filtradas.map((n, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs flex justify-between items-center shadow-sm hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-900 text-sm"
  }, n.Nombre || n.nombre || n.Titulo || n.asunto || n.Asunto), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500"
  }, n.Extracto || n.extracto || n.Descripcion || 'Circular oficial emitida por la Supervisión Escolar Zona 001.')), (n.Enlace || n.enlace) && /*#__PURE__*/React.createElement("a", {
    href: n.Enlace || n.enlace,
    target: "_blank",
    rel: "noreferrer",
    className: "text-xs font-bold text-amber-700 bg-amber-50 hover:bg-amber-100 px-3 py-1.5 rounded-lg border border-amber-200 whitespace-nowrap ml-4 transition"
  }, "Ver Documento \u2197")))));
}

// =============================================================
// VISTA 14: JUNTAS ACADÉMICAS Y RELATORÍAS
// =============================================================
function JuntasView({
  onBack,
  setMetrics
}) {
  const [juntas, setJuntas] = React.useState(null);
  React.useEffect(() => {
    apiRequest('/api/juntas').then(setJuntas);
  }, []);
  if (!juntas) return /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando cat\xE1logo metodol\xF3gico...");
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Juntas Acad\xE9micas y Cat\xE1logo de Metodolog\xEDas")), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-5 rounded-xl border border-slate-200 space-y-4"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-sm"
  }, "Cat\xE1logo Oficial de Metodolog\xEDas Pedag\xF3gicas"), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 gap-3 text-xs"
  }, Object.entries(juntas.catalogo_metodologias || {}).map(([clave, desc]) => /*#__PURE__*/React.createElement("div", {
    key: clave,
    className: "p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-amber-800"
  }, clave), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, desc))))));
}

// =============================================================
// VISTA 15: METAS PERSONALES
// =============================================================
function MetasView({
  onBack,
  setMetrics
}) {
  const [metas, setMetas] = React.useState([]);
  React.useEffect(() => {
    apiRequest('/api/metas').then(setMetas);
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Metas Personales Trimestrales")), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, metas.map((m, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, m.Docente || m.Especialista), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, m.Ciclo || '2026-2027')), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Meta:"), " ", m.Meta || m.Descripcion), m.Avance && /*#__PURE__*/React.createElement("div", {
    className: "text-emerald-700"
  }, /*#__PURE__*/React.createElement("strong", null, "Avance Reportado:"), " ", m.Avance)))));
}

// =============================================================
// VISTA 16: TRÁMITES
// =============================================================
function TramitesView({
  onBack,
  setMetrics
}) {
  const [tramites, setTramites] = React.useState([]);
  React.useEffect(() => {
    apiRequest('/api/tramites').then(setTramites);
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Tr\xE1mites y Solicitudes Administrativas")), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, tramites.map((t, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, t.Tipo || t.Asunto), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, t.Fecha)), /*#__PURE__*/React.createElement("div", null, "Solicitante: ", t.Solicitante, " \u2022 Estatus: ", /*#__PURE__*/React.createElement("strong", {
    className: "text-amber-800"
  }, t.Estatus || 'En Proceso'))))));
}

// =============================================================
// VISTA 17: INFORMES
// =============================================================
function InformesView({
  onBack,
  setMetrics
}) {
  const [informes, setInformes] = React.useState([]);
  React.useEffect(() => {
    apiRequest('/api/informes').then(setInformes);
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Informes y Documentos Pedag\xF3gicos")), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, informes.map((inf, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center font-bold text-slate-900"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-sm"
  }, inf.Titulo || inf.Asunto), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400 font-normal"
  }, inf.Fecha)), /*#__PURE__*/React.createElement("div", null, "Alumno / Grupo: ", inf.Alumno || inf.Escuela)))));
}

// =============================================================
// VISTA 18: ACTAS DE VISITA Y OFICIOS DE COMISIÓN
// =============================================================
function ActasYOficiosView({
  onBack,
  setMetrics
}) {
  const [visitas, setVisitas] = React.useState([]);
  const [oficios, setOficios] = React.useState([]);
  const [subTab, setSubTab] = React.useState('visitas');
  React.useEffect(() => {
    const t0 = performance.now();
    Promise.all([apiRequest('/api/visitas'), apiRequest('/api/oficios')]).then(([v, o]) => {
      setVisitas(v);
      setOficios(o);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 2
      }));
    });
  }, [setMetrics]);
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Actas de Visita y Oficios de Comisi\xF3n")), /*#__PURE__*/React.createElement("div", {
    className: "flex border-b border-slate-200 space-x-2 text-xs font-bold"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setSubTab('visitas'),
    className: `px-4 py-2 border-b-2 transition ${subTab === 'visitas' ? 'border-amber-600 text-amber-800 bg-amber-50/50' : 'border-transparent text-slate-500'}`
  }, "\uD83D\uDCCB Actas de Visita de Acompa\xF1amiento (", visitas.length, ")"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setSubTab('oficios'),
    className: `px-4 py-2 border-b-2 transition ${subTab === 'oficios' ? 'border-amber-600 text-amber-800 bg-amber-50/50' : 'border-transparent text-slate-500'}`
  }, "\uD83D\uDCDC Oficios de Comisi\xF3n (", oficios.length, ")")), subTab === 'visitas' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-3"
  }, visitas.map((v, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-1 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-900 text-sm"
  }, "Escuela: ", v.Escuela), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400"
  }, v.Fecha), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/visitas/${v.id || v.ID_Visita || v.Folio}/pdf`, `Visita_${v.id || v.ID_Visita || v.Folio}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Acta de Visita Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Personal de Acompa\xF1amiento:"), " ", v.Personal), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Motivo:"), " ", v.Motivo), v.Observaciones && /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, /*#__PURE__*/React.createElement("strong", null, "Observaciones:"), " ", v.Observaciones)))), subTab === 'oficios' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-3"
  }, oficios.map((o, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-1 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center"
  }, /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-900 text-sm"
  }, "Folio: ", o.Folio), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-400"
  }, "Emisi\xF3n: ", o.Fecha_Emision), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado(`/api/oficios/${o.id || o.Folio}/pdf`, `Oficio_${o.id || o.Folio}.pdf`),
    className: "px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
    title: "Descargar Oficio de Comisi\xF3n Oficial PDF"
  }, "\uD83D\uDCC4 PDF"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Destino:"), " ", o.Destino, " (", o.Escuela, ")"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Personal comisionado:"), " ", o.Maestra_Apoyo), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Asunto:"), " ", o.Asunto), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Horario:"), " ", o.Horario)))));
}

// =============================================================
// VISTA 19: ESTADÍSTICAS INSTITUCIONALES DE ZONA
// =============================================================
function EstadisticasView({
  onBack,
  setMetrics
}) {
  const [stats, setStats] = React.useState(null);
  React.useEffect(() => {
    const t0 = performance.now();
    apiRequest('/api/estadisticas/zona').then(data => {
      setStats(data);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 1
      }));
    });
  }, [setMetrics]);
  if (!stats) {
    return /*#__PURE__*/React.createElement("div", {
      className: "text-center py-16 text-slate-500 text-sm"
    }, "Calculando indicadores relacionales...");
  }
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Estad\xEDsticas de Zona 001")), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/descargar-concentrado', 'Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx'),
    className: "px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow transition cursor-pointer flex items-center space-x-1.5",
    title: "Descargar Concentrado Excel Oficial"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCCA Concentrado XLSX"))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-4 gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Total Alumnos en Padr\xF3n"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-slate-900 mt-1"
  }, stats.total_alumnos), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-emerald-600 mt-1"
  }, "Activos en ciclo ", stats.ciclo_activo)), /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Escuelas de la Zona"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-amber-600 mt-1"
  }, stats.total_escuelas), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-400 mt-1"
  }, "Primarias p\xFAblicas")), /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Cumplimiento EPP"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-emerald-600 mt-1"
  }, stats.cumplimiento_epp), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-400 mt-1"
  }, "Avance curricular")), /*#__PURE__*/React.createElement("div", {
    className: "p-4 bg-white rounded-xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-slate-500 text-xs font-semibold"
  }, "Actas y Oficios"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-slate-900 mt-1"
  }, stats.visitas_registradas + stats.oficios_emitidos), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-400 mt-1"
  }, "Supervisi\xF3n t\xE9cnica"))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 gap-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-5 bg-white rounded-xl border border-slate-200 space-y-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-sm"
  }, "Distribuci\xF3n por Condici\xF3n o Discapacidad"), /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 text-xs"
  }, Object.entries(stats.distribucion_condicion || {}).map(([cond, count]) => /*#__PURE__*/React.createElement("div", {
    key: cond,
    className: "flex justify-between items-center py-1 border-b border-slate-100"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-700"
  }, cond), /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded"
  }, count))))), /*#__PURE__*/React.createElement("div", {
    className: "p-5 bg-white rounded-xl border border-slate-200 space-y-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-sm"
  }, "Matr\xEDcula por Escuela"), /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 text-xs"
  }, Object.entries(stats.distribucion_escuela || {}).map(([esc, count]) => /*#__PURE__*/React.createElement("div", {
    key: esc,
    className: "flex justify-between items-center py-1 border-b border-slate-100"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-700"
  }, esc), /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded"
  }, count)))))));
}
ReactDOM.createRoot(document.getElementById('root')).render( /*#__PURE__*/React.createElement(ErrorBoundary, null, /*#__PURE__*/React.createElement(App, null)));