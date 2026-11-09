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
    console.error("ErrorBoundary atrap\u00f3 un error en tiempo de render:", error, errorInfo);
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
      }, ((_this$state$error = this.state.error) === null || _this$state$error === void 0 ? void 0 : _this$state$error.message) || 'Ocurri\u00f3 una excepci\u00f3n al procesar la vista interactiva.'), this.state.error && /*#__PURE__*/React.createElement("details", {
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

// Cliente API con Bearer Token y manejo de sesi\u00f3n
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
        throw new Error('Sesi\u00f3n expirada o no autorizada. Por favor inicie sesi\u00f3n nuevamente.');
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
    throw new Error('Sesi\u00f3n expirada o credenciales inv\u00e1lidas');
  }
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Error ${res.status}`);
  }
  return await res.json();
}

// =============================================================
// COMPONENTE: PANTALLA DE INICIO DE SESI\u00d3N
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
        throw new Error('Usuario o contrase\u00f1a incorrectos.');
      }
      const data = await res.json();
      onLoginSuccess(data.user, data.token);
    } catch (err) {
      setError(err.message || 'Error de conexi\u00f3n');
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
// COMPONENTE PRINCIPAL (APP CON NAVEGACI\u00d3N COMPLETA DE M\u00d3DULOS)
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

  // Sincronizaci\u00f3n en vivo entre sesiones concurrentes (Cero Recargas)
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
            setNotificacionEnVivo(`\u1f504 ${ult.resumen || 'Cambio registrado en plataforma'}`);
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
  }, "\uD83D\uDC65 Maestros Primaria"), ((user === null || user === void 0 ? void 0 : user.director) || (user === null || user === void 0 ? void 0 : user.rol) === 'DIRECTOR') && /*#__PURE__*/React.createElement("button", {
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
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    onOpenAlumno: id => {
      setActiveAlumnoId(id);
      setCurrentView('expedientes');
    },
    setMetrics: setMetrics
  }), currentView === 'anexo3' && /*#__PURE__*/React.createElement(Anexo3View, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo4' && /*#__PURE__*/React.createElement(Anexo4View, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo5' && /*#__PURE__*/React.createElement(Anexo5View, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'anexo7' && /*#__PURE__*/React.createElement(Anexo7View, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'horarios' && /*#__PURE__*/React.createElement(HorariosView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'cronogramas' && /*#__PURE__*/React.createElement(CronogramasView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'calendario' && /*#__PURE__*/React.createElement(CalendarioView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'docentes_regulares' && /*#__PURE__*/React.createElement(DocentesRegularesView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'novedades' && /*#__PURE__*/React.createElement(NovedadesView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'juntas' && /*#__PURE__*/React.createElement(JuntasView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'metas' && /*#__PURE__*/React.createElement(MetasView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'tramites' && /*#__PURE__*/React.createElement(TramitesView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'informes' && /*#__PURE__*/React.createElement(InformesView, {
    user: user,
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'visitas' && /*#__PURE__*/React.createElement(ActasYOficiosView, {
    onBack: () => setCurrentView('mis_documentos'),
    setMetrics: setMetrics
  }), currentView === 'estadisticas' && /*#__PURE__*/React.createElement(EstadisticasView, {
    user: user,
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
    }, ((_plan$metadatos = plan.metadatos) === null || _plan$metadatos === void 0 ? void 0 : _plan$metadatos.titulo) || `Planeaci\u00f3n Anexo ${plan.formato}`), /*#__PURE__*/React.createElement("span", {
      className: `text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${plan.estado === 'APROBADO' || plan.estado === 'AUTORIZADA' ? 'bg-emerald-100 text-emerald-800' : plan.estado === 'REVISI\u00d3N' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}`
    }, plan.estado)), /*#__PURE__*/React.createElement("div", {
      className: "text-xs text-slate-500 flex items-center space-x-3"
    }, /*#__PURE__*/React.createElement("span", null, "\uD83C\uDFEB ", ((_plan$datos = plan.datos) === null || _plan$datos === void 0 ? void 0 : _plan$datos.Escuela) || 'Primaria Oficial'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Grado: ", ((_plan$datos2 = plan.datos) === null || _plan$datos2 === void 0 ? void 0 : _plan$datos2.Grado_Grupo) || 'Atenci\u00f3n USAER'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, ((_plan$datos3 = plan.datos) === null || _plan$datos3 === void 0 ? void 0 : _plan$datos3.Docente_Especialista) || 'Docente USAER'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Guardado: ", plan.guardado_en || 'Reciente'))), /*#__PURE__*/React.createElement("div", {
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
  }, al.condicion || 'Atenci\u00f3n USAER'), /*#__PURE__*/React.createElement("span", {
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
// VISTA 2: EDITOR DE PLANEACI\u00d3N COMPATIBLE CON STREAMLIT + SPA
// =============================================================
function PlaneacionEditorView({
  docId,
  user,
  onBack,
  setMetrics
}) {
  var _doc$tablas, _doc$tablas2, _doc$tablas3, _doc$datos2, _doc$tablas4, _doc$metadatos, _doc$metadatos2, _doc$metadatos3, _doc$metadatos4, _doc$metadatos5, _doc$metadatos6, _doc$datos3, _doc$datos4, _doc$datos5, _doc$datos6, _doc$datos7, _doc$datos8, _doc$datos9, _doc$datos10, _doc$datos11, _doc$datos12, _doc$datos13;
  const [doc, setDoc] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [activeTab, setActiveTab] = React.useState('vivo');
  const [saveStatus, setSaveStatus] = React.useState('saved');
  const [conflictError, setConflictError] = React.useState(null);
  const [assistantOpen, setAssistantOpen] = React.useState(false);
  const [borradorDisponible, setBorradorDisponible] = React.useState(null);
  const debounceTimer = React.useRef(null);
  const [modalAsistente, setModalAsistente] = React.useState(false);
  const [alumnoAsistente, setAlumnoAsistente] = React.useState(null);
  const [idxAlumnoAsistente, setIdxAlumnoAsistente] = React.useState(null);
  const [nivelAprendizaje, setNivelAprendizaje] = React.useState('Presil\u00e1bico / Inicial');
  const [metodoSeleccionado, setMetodoSeleccionado] = React.useState('M\u00e9todo Troncoso y Material Multisensorial');
  const [apoyosSeleccionados, setApoyosSeleccionados] = React.useState(['Material concreto manipulable', 'Claves visuales']);
  const [propuestaIA, setPropuestaIA] = React.useState(null);
  const [textoEditadoPropuesta, setTextoEditadoPropuesta] = React.useState('');
  const [generandoPropuesta, setGenerandoPropuesta] = React.useState(false);
  const handleContinuidadTrimestre = async () => {
    try {
      var _prevDoc$metadatos, _prevDoc$tablas;
      const listado = await apiRequest('/api/planeaciones');
      const anteriores = listado.filter(p => p.id !== docId);
      if (anteriores.length === 0) {
        alert('No se encontraron planeaciones de trimestres previos para arrastrar antecedentes.');
        return;
      }
      const prevDoc = await apiRequest('/api/planeaciones/' + anteriores[0].id);
      const prevNEE = ((_prevDoc$metadatos = prevDoc.metadatos) === null || _prevDoc$metadatos === void 0 ? void 0 : _prevDoc$metadatos.necesidades_confirmadas) || ((_prevDoc$tablas = prevDoc.tablas) === null || _prevDoc$tablas === void 0 ? void 0 : _prevDoc$tablas.nee) || [];
      mutarDoc(d => {
        return {
          ...d,
          metadatos: {
            ...d.metadatos,
            antecedentes_continuidad: prevNEE,
            aviso_continuidad: `Antecedentes recuperados de planeaci\u00f3n previa (${anteriores[0].fecha || 'Trimestre anterior'}). Revisa y ajusta seg\u00fan los avances observados.`
          }
        };
      });
      alert('Continuidad pedag\u00f3gica aplicada: antecedentes y NEE vigentes vinculados con \u00e9xito.');
    } catch (err) {
      alert('Error al recuperar continuidad: ' + err.message);
    }
  };
  const abrirAsistenteParaAlumno = (row, idx) => {
    setAlumnoAsistente(row);
    setIdxAlumnoAsistente(idx);
    setPropuestaIA(null);
    setTextoEditadoPropuesta('');
    setModalAsistente(true);
  };
  const ejecutarGeneradorPropuesta = async () => {
    setGenerandoPropuesta(true);
    try {
      var _doc$datos;
      const res = await apiRequest('/api/ai/proponer-actividades', {
        method: 'POST',
        body: JSON.stringify({
          alumno_id: (alumnoAsistente === null || alumnoAsistente === void 0 ? void 0 : alumnoAsistente.id_alumno) || (alumnoAsistente === null || alumnoAsistente === void 0 ? void 0 : alumnoAsistente.id) || '',
          nivel_aprendizaje: nivelAprendizaje,
          metodo: metodoSeleccionado,
          area: (doc === null || doc === void 0 || (_doc$datos = doc.datos) === null || _doc$datos === void 0 ? void 0 : _doc$datos['Funci\u00f3n']) || (user === null || user === void 0 ? void 0 : user.rol) || 'Aprendizaje',
          apoyos: apoyosSeleccionados,
          duracion_min: 30
        })
      });
      setPropuestaIA(res);
      const formatoTexto = `[${res.titulo}]\nProp\u00f3sito: ${res.proposito_observable}\n- Inicio: ${res.inicio}\n- Desarrollo: ${res.desarrollo}\n- Cierre: ${res.cierre}\nMateriales: ${(res.materiales_especificos || []).join(', ')}\nEvaluaci\u00f3n: ${res.criterio_evaluacion}`;
      setTextoEditadoPropuesta(formatoTexto);
    } catch (err) {
      alert('Error al generar propuesta: ' + err.message);
    } finally {
      setGenerandoPropuesta(false);
    }
  };
  const aceptarPropuestaEnPlaneacion = () => {
    if (idxAlumnoAsistente === null) return;
    mutarDoc(d => {
      var _d$tablas, _d$datos;
      let lista = [...(((_d$tablas = d.tablas) === null || _d$tablas === void 0 ? void 0 : _d$tablas.nee) || ((_d$datos = d.datos) === null || _d$datos === void 0 ? void 0 : _d$datos.Alumnos) || [])];
      if (lista[idxAlumnoAsistente]) {
        lista[idxAlumnoAsistente] = {
          ...lista[idxAlumnoAsistente],
          actividades: textoEditadoPropuesta,
          ajustes: textoEditadoPropuesta,
          ['Ajustes razonables']: textoEditadoPropuesta,
          propuesta_origen: (propuestaIA === null || propuestaIA === void 0 ? void 0 : propuestaIA.origen) || 'Asistente USAER 2E'
        };
      }
      return {
        ...d,
        tablas: {
          ...d.tablas,
          nee: lista,
          aprendizajes: lista
        }
      };
    });
    setModalAsistente(false);
  };
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
      console.error("Error abriendo planeaci\u00f3n:", e);
    } finally {
      setLoading(false);
    }
  }, [docId, setMetrics]);
  React.useEffect(() => {
    fetchDoc();
  }, [fetchDoc]);
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
  }, [docId, setMetrics]);
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

  // Reconciliaci\u00f3n bidireccional de filas de alumnos desde datos o tablas
  let tablaNEE = ((_doc$tablas = doc.tablas) === null || _doc$tablas === void 0 ? void 0 : _doc$tablas.nee) || ((_doc$tablas2 = doc.tablas) === null || _doc$tablas2 === void 0 ? void 0 : _doc$tablas2.aprendizajes) || ((_doc$tablas3 = doc.tablas) === null || _doc$tablas3 === void 0 ? void 0 : _doc$tablas3["Tabla principal"]) || [];
  if ((!Array.isArray(tablaNEE) || tablaNEE.length === 0) && Array.isArray((_doc$datos2 = doc.datos) === null || _doc$datos2 === void 0 ? void 0 : _doc$datos2.Alumnos)) {
    tablaNEE = doc.datos.Alumnos.map((a, idx) => ({
      id_alumno: a.ID_Alumno || a.id || `ALU-${idx}`,
      alumno: a['Nombre del alumno'] || a.Nombre_Completo || a.nombre || 'Alumno/a',
      grado: a.Grado || a.grado || '',
      grupo: a.Grupo || a.grupo || 'A',
      condicion: a['Condici\u00f3n'] || a.condicion || 'Atenci\u00f3n prioritaria',
      pda: a.pda || 'Identifica ideas clave y consolida habilidades prioritarias.',
      barreras_o_necesidades: a.barreras || a['Condici\u00f3n'] || 'Barrera curricular / metodol\u00f3gica.',
      descriptor: a.descriptor || 'El alumno participa y consolida aprendizajes con apoyos diversificados.',
      apoyos: a.apoyos || 'Material visual, adecuaci\u00f3n de tiempos y consignas claras.'
    }));
  }
  let tablaDosificacion = ((_doc$tablas4 = doc.tablas) === null || _doc$tablas4 === void 0 ? void 0 : _doc$tablas4.dosificacion) || [];
  if (!Array.isArray(tablaDosificacion) || tablaDosificacion.length === 0) {
    tablaDosificacion = [{
      contexto: 'Aula regular',
      Contextos: 'Aula regular',
      fecha: '',
      actividades: 'Ajustes a la metodolog\u00eda y acompa\u00f1amiento en tareas prioritarias.',
      recursos: 'Material concreto y apoyos gr\u00e1ficos.'
    }, {
      contexto: 'Escuela',
      Contextos: 'Escuela',
      fecha: '',
      actividades: 'Participaci\u00f3n en din\u00e1micas inclusivas y sensibilizaci\u00f3n comunitaria.',
      recursos: 'Gu\u00edas de trabajo.'
    }, {
      contexto: 'Familia',
      Contextos: 'Familia',
      fecha: '',
      actividades: 'Orientaci\u00f3n para el acompa\u00f1amiento en casa y rutinas de estudio.',
      recursos: 'C\u00e9dula de acuerdos familiares.'
    }];
  }
  const textoNecesidades = ((_doc$metadatos = doc.metadatos) === null || _doc$metadatos === void 0 ? void 0 : _doc$metadatos.necesidades_confirmadas) || ((_doc$metadatos2 = doc.metadatos) === null || _doc$metadatos2 === void 0 || (_doc$metadatos2 = _doc$metadatos2.campos_autoprellenados) === null || _doc$metadatos2 === void 0 ? void 0 : _doc$metadatos2.necesidades_confirmadas) || '';
  const textoCurricular = ((_doc$metadatos3 = doc.metadatos) === null || _doc$metadatos3 === void 0 ? void 0 : _doc$metadatos3.referente_curricular) || '';
  const textoGuia = ((_doc$metadatos4 = doc.metadatos) === null || _doc$metadatos4 === void 0 ? void 0 : _doc$metadatos4.guia_grupal_manual) || '';
  const aportacionesEquipo = ((_doc$metadatos5 = doc.metadatos) === null || _doc$metadatos5 === void 0 ? void 0 : _doc$metadatos5.aportaciones_equipo) || {};
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
    className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 text-xs font-semibold transition cursor-pointer"
  }, "\u2190 Volver a Mis Documentos"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$metadatos6 = doc.metadatos) === null || _doc$metadatos6 === void 0 ? void 0 : _doc$metadatos6.titulo) || `Planeaci\u00f3n Anexo ${doc.formato || 'XXI'}`,
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
    className: "text-xs text-slate-500 px-1 flex flex-wrap items-center gap-2"
  }, /*#__PURE__*/React.createElement("span", null, "Anexo ", /*#__PURE__*/React.createElement("strong", null, doc.formato || 'XXI')), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Escuela: ", ((_doc$datos3 = doc.datos) === null || _doc$datos3 === void 0 ? void 0 : _doc$datos3.Escuela) || ((_doc$datos4 = doc.datos) === null || _doc$datos4 === void 0 ? void 0 : _doc$datos4["Escuela regular"]) || 'Primaria'), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Especialista: ", ((_doc$datos5 = doc.datos) === null || _doc$datos5 === void 0 ? void 0 : _doc$datos5.Docente_Especialista) || ((_doc$datos6 = doc.datos) === null || _doc$datos6 === void 0 ? void 0 : _doc$datos6["Nombre del especialista"]) || (user === null || user === void 0 ? void 0 : user.nombre)), /*#__PURE__*/React.createElement("span", null, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Revisi\xF3n: ", doc.revision || 'Guardada')))), /*#__PURE__*/React.createElement("div", {
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
    className: "text-amber-700 font-semibold"
  }, "Guardando...")), saveStatus === 'dirty' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-amber-400"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500"
  }, "Cambios pendientes")), saveStatus === 'error' && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", {
    className: "w-2 h-2 rounded-full bg-red-400"
  }), /*#__PURE__*/React.createElement("span", {
    className: "text-red-600"
  }, "Error al guardar"))), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: handleContinuidadTrimestre,
    className: "px-3.5 py-1.5 bg-indigo-700 hover:bg-indigo-800 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm cursor-pointer",
    title: "Arrastrar antecedentes, NEE y referentes del trimestre anterior"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDD04 Continuidad")), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => descargarArchivoAutenticado(`/api/planeaciones/${doc.id}/pdf`, `Planeacion_${doc.formato || 'XXI'}_${doc.id}.pdf`),
    className: "px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm cursor-pointer"
  }, /*#__PURE__*/React.createElement("span", null, "Descargar PDF"), /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCC4")), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setAssistantOpen(!assistantOpen),
    className: `px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer flex items-center space-x-1 ${assistantOpen ? 'bg-amber-600 text-white' : 'bg-amber-50 text-amber-800 border border-amber-300 hover:bg-amber-100'}`
  }, /*#__PURE__*/React.createElement("span", null, "\uD83E\uDD16 Asistente IA")))), /*#__PURE__*/React.createElement("div", {
    className: "flex border-b border-slate-200 space-x-1 text-sm font-semibold overflow-x-auto"
  }, [{
    id: 'vivo',
    label: '\u1f4c4 1. Formato Vivo Institucional'
  }, {
    id: 'alumnos',
    label: '\u1f465 2. Matriz de Alumnos y BAP'
  }, {
    id: 'dosificacion',
    label: '\u1f4c5 3. Dosificaci\u00f3n y Actividades'
  }, {
    id: 'interdisciplinario',
    label: '\u1f91d 4. Equipo Multidisciplinario'
  }, {
    id: 'evaluacion',
    label: '\u2713 5. Evaluaci\u00f3n Formativa'
  }].map(tab => /*#__PURE__*/React.createElement("button", {
    key: tab.id,
    onClick: () => setActiveTab(tab.id),
    className: `px-4 py-2.5 border-b-2 font-bold transition text-xs sm:text-sm whitespace-nowrap cursor-pointer ${activeTab === tab.id ? 'border-amber-600 text-amber-700 bg-amber-50/50' : 'border-transparent text-slate-500 hover:text-slate-800'}`
  }, tab.label))), /*#__PURE__*/React.createElement("div", {
    className: "flex gap-4 items-start"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm min-h-[420px] space-y-5"
  }, activeTab === 'vivo' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-5 font-sans"
  }, /*#__PURE__*/React.createElement("div", {
    className: "border border-slate-300 p-4 rounded-xl bg-slate-50/70 space-y-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-center border-b border-slate-200 pb-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs tracking-wider text-slate-500 uppercase font-bold"
  }, "Secretar\xEDa de Educaci\xF3n del Gobierno del Estado de Yucat\xE1n \xB7 Direcci\xF3n de Educaci\xF3n Especial"), /*#__PURE__*/React.createElement("div", {
    className: "text-sm font-black text-slate-800"
  }, "USAER 02E \xB7 ZONA 001 PRIMARIAS"), /*#__PURE__*/React.createElement("div", {
    className: "text-base font-bold text-amber-800 uppercase mt-1"
  }, "PLAN DE INTERVENCI\xD3N \xB7 ANEXO ", doc.formato || 'XXI', " (FORMATO VIVO)")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500 block"
  }, "Escuela Primaria:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$datos7 = doc.datos) === null || _doc$datos7 === void 0 ? void 0 : _doc$datos7.Escuela) || ((_doc$datos8 = doc.datos) === null || _doc$datos8 === void 0 ? void 0 : _doc$datos8["Escuela regular"]) || '',
    onChange: e => mutarDoc(d => ({
      ...d,
      datos: {
        ...d.datos,
        Escuela: e.target.value,
        "Escuela regular": e.target.value
      }
    })),
    className: "w-full p-1 border border-slate-200 rounded font-semibold text-slate-800"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500 block"
  }, "Clave CCT:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$datos9 = doc.datos) === null || _doc$datos9 === void 0 ? void 0 : _doc$datos9.CCT) || '',
    onChange: e => mutarDoc(d => ({
      ...d,
      datos: {
        ...d.datos,
        CCT: e.target.value
      }
    })),
    className: "w-full p-1 border border-slate-200 rounded font-semibold text-slate-800"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500 block"
  }, "Ciclo Escolar:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$datos10 = doc.datos) === null || _doc$datos10 === void 0 ? void 0 : _doc$datos10["Curso escolar"]) || '2026-2027',
    onChange: e => mutarDoc(d => ({
      ...d,
      datos: {
        ...d.datos,
        "Curso escolar": e.target.value
      }
    })),
    className: "w-full p-1 border border-slate-200 rounded font-semibold text-slate-800"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-500 block"
  }, "Docente / Especialista:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: ((_doc$datos11 = doc.datos) === null || _doc$datos11 === void 0 ? void 0 : _doc$datos11.Docente_Especialista) || ((_doc$datos12 = doc.datos) === null || _doc$datos12 === void 0 ? void 0 : _doc$datos12["Nombre del especialista"]) || (user === null || user === void 0 ? void 0 : user.nombre) || '',
    onChange: e => mutarDoc(d => ({
      ...d,
      datos: {
        ...d.datos,
        Docente_Especialista: e.target.value,
        "Nombre del especialista": e.target.value
      }
    })),
    className: "w-full p-1 border border-slate-200 rounded font-semibold text-slate-800"
  })))), /*#__PURE__*/React.createElement("div", {
    className: "space-y-1.5"
  }, /*#__PURE__*/React.createElement("label", {
    className: "text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("span", null, "1. Antecedentes y Necesidades Educativas Espec\xEDficas Confirmadas (Historial E1-E5)"), /*#__PURE__*/React.createElement("span", {
    className: "text-[11px] font-normal text-slate-500"
  }, "Texto capturado e importado desde expedientes")), /*#__PURE__*/React.createElement("textarea", {
    rows: "6",
    value: textoNecesidades,
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        var _d$metadatos;
        return {
          ...d,
          metadatos: {
            ...d.metadatos,
            necesidades_confirmadas: val,
            campos_autoprellenados: {
              ...(((_d$metadatos = d.metadatos) === null || _d$metadatos === void 0 ? void 0 : _d$metadatos.campos_autoprellenados) || {}),
              necesidades_confirmadas: val
            }
          }
        };
      });
    },
    placeholder: "Redacci\xF3n de antecedentes pedag\xF3gicos, valoraciones previas, eventos significativos y NEE detectadas...",
    className: "w-full p-3 border border-slate-300 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-amber-500 font-mono leading-relaxed bg-amber-50/20"
  })), /*#__PURE__*/React.createElement("div", {
    className: "space-y-1.5"
  }, /*#__PURE__*/React.createElement("label", {
    className: "text-xs font-bold text-slate-800 uppercase tracking-wide"
  }, "2. Referente Curricular (Campos Formativos, Ejes Articuladores y Metodolog\xEDas NEM)"), /*#__PURE__*/React.createElement("textarea", {
    rows: "3",
    value: textoCurricular,
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => ({
        ...d,
        metadatos: {
          ...d.metadatos,
          referente_curricular: val
        }
      }));
    },
    placeholder: "Campos formativos: Lenguajes, Saberes y pensamiento cient\xEDfico. Ejes: Inclusi\xF3n, Pensamiento cr\xEDtico...",
    className: "w-full p-2.5 border border-slate-300 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-amber-500"
  })), textoGuia && /*#__PURE__*/React.createElement("div", {
    className: "space-y-1.5"
  }, /*#__PURE__*/React.createElement("label", {
    className: "text-xs font-bold text-slate-800 uppercase tracking-wide"
  }, "3. Gu\xEDa Grupal de Intervenci\xF3n (Anexo XIX)"), /*#__PURE__*/React.createElement("textarea", {
    rows: "3",
    value: textoGuia,
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => ({
        ...d,
        metadatos: {
          ...d.metadatos,
          guia_grupal_manual: val
        }
      }));
    },
    className: "w-full p-2.5 border border-slate-300 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-amber-500"
  }))), activeTab === 'alumnos' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Matriz de Alumnos del Grupo y Ajustes Razonables"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Cada alumno cuenta con su vinculaci\xF3n individual de barreras, PDA y apoyos pertinentes.")), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => {
      const nuevaFila = {
        id_alumno: `ALU-${Date.now()}`,
        alumno: 'Nuevo Alumno',
        pda: 'Identifica ideas clave con apoyo visual.',
        barreras_o_necesidades: 'Atenci\u00f3n sostenida en lectura guiada.',
        descriptor: 'El alumno participa activamente con apoyo visual.',
        apoyos: 'Material concreto y consignas cortas.'
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
    className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold cursor-pointer"
  }, "+ Agregar Fila de Alumno")), /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto border border-slate-200 rounded-xl"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-xs text-left border-collapse"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    className: "bg-slate-50 text-slate-600 border-b border-slate-200 font-bold"
  }, /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Alumno / Alumna"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Aprendizaje / PDA Prioritario"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Barrera o Necesidad (BAP)"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Descriptor Observable (Zona 001)"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/5"
  }, "Apoyos y Ajustes Razonables"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-8"
  }))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, tablaNEE.map((row, idx) => /*#__PURE__*/React.createElement("tr", {
    key: idx,
    className: "hover:bg-slate-50/70 transition"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: row.alumno || row.Alumno || '',
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
    className: "w-full p-1.5 border border-slate-200 rounded font-semibold text-slate-800"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.pda || row['Aprendizaje y/u objetivo'] || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaNEE];
        copy[idx] = {
          ...copy[idx],
          pda: val,
          'Aprendizaje y/u objetivo': val
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
    className: "w-full p-1.5 border border-slate-200 rounded text-slate-700"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.barreras_o_necesidades || row['Necesidades educativas espec\u00edficas'] || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaNEE];
        copy[idx] = {
          ...copy[idx],
          barreras_o_necesidades: val,
          'Necesidades educativas espec\u00edficas': val
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
    className: "w-full p-1.5 border border-slate-200 rounded text-slate-700"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.descriptor || row['Descriptor de logro'] || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaNEE];
        copy[idx] = {
          ...copy[idx],
          descriptor: val,
          'Descriptor de logro': val
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
    className: "w-full p-1.5 border border-slate-200 rounded text-slate-700"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.apoyos || row['Apoyos y Ajustes'] || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaNEE];
        copy[idx] = {
          ...copy[idx],
          apoyos: val,
          'Apoyos y Ajustes': val
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
    className: "w-full p-1.5 border border-slate-200 rounded text-slate-700"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2 text-center"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => {
      mutarDoc(d => {
        const copy = tablaNEE.filter((_, i) => i !== idx);
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
    className: "text-red-500 hover:text-red-700 font-bold p-1 cursor-pointer",
    title: "Eliminar fila"
  }, "\u2715"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => abrirAsistenteParaAlumno(row, idx),
    className: "mt-1 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 px-2 py-1 rounded text-[10px] font-bold block whitespace-nowrap shadow-xs cursor-pointer",
    title: "Proponer actividades para este alumno con filtro pedag\xF3gico de pertinencia"
  }, "\u26A1 Proponer actividad")))))))), activeTab === 'dosificacion' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Dosificaci\xF3n de Actividades por Contexto"), /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto border border-slate-200 rounded-xl"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-xs text-left border-collapse"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    className: "bg-slate-50 text-slate-600 border-b border-slate-200 font-bold"
  }, /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/4"
  }, "Contexto"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/4"
  }, "Fecha / Periodo"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/4"
  }, "Actividades Diversificadas"), /*#__PURE__*/React.createElement("th", {
    className: "p-2.5 w-1/4"
  }, "Recursos y Apoyos"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, tablaDosificacion.map((row, idx) => /*#__PURE__*/React.createElement("tr", {
    key: idx
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-2 font-bold text-slate-800"
  }, row.contexto || row.Contextos), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: row.fecha || row.Fecha || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[idx] = {
          ...copy[idx],
          fecha: val,
          Fecha: val
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
    placeholder: "ej. Octubre - Diciembre",
    className: "w-full p-1.5 border border-slate-200 rounded"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.actividades || row.Actividades || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[idx] = {
          ...copy[idx],
          actividades: val,
          Actividades: val
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
    className: "w-full p-1.5 border border-slate-200 rounded"
  })), /*#__PURE__*/React.createElement("td", {
    className: "p-2"
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: "2",
    value: row.recursos || row.Recursos || '',
    onChange: e => {
      const val = e.target.value;
      mutarDoc(d => {
        const copy = [...tablaDosificacion];
        copy[idx] = {
          ...copy[idx],
          recursos: val,
          Recursos: val
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
    className: "w-full p-1.5 border border-slate-200 rounded"
  })))))))), activeTab === 'interdisciplinario' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Aportaciones Interdisciplinarias del Equipo USAER 2E"), /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, ['Psicolog\u00eda', 'Comunicaci\u00f3n', 'Trabajo Social'].map(area => {
    var _aporte$fecha;
    const aporte = aportacionesEquipo[area] || {};
    return /*#__PURE__*/React.createElement("div", {
      key: area,
      className: "p-3.5 border border-slate-200 rounded-xl bg-slate-50/50 space-y-2"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center text-xs font-bold text-slate-800"
    }, /*#__PURE__*/React.createElement("span", null, "\xC1rea de ", area), /*#__PURE__*/React.createElement("span", {
      className: "text-slate-400 font-normal"
    }, aporte.autor ? `Por ${aporte.autor} (${(_aporte$fecha = aporte.fecha) === null || _aporte$fecha === void 0 ? void 0 : _aporte$fecha.slice(0, 10)})` : 'Pendiente de aportaci\u00f3n')), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: aporte.observaciones || '',
      onChange: e => {
        const val = e.target.value;
        mutarDoc(d => {
          var _d$metadatos2, _d$metadatos3;
          return {
            ...d,
            metadatos: {
              ...d.metadatos,
              aportaciones_equipo: {
                ...(((_d$metadatos2 = d.metadatos) === null || _d$metadatos2 === void 0 ? void 0 : _d$metadatos2.aportaciones_equipo) || {}),
                [area]: {
                  ...(((_d$metadatos3 = d.metadatos) === null || _d$metadatos3 === void 0 || (_d$metadatos3 = _d$metadatos3.aportaciones_equipo) === null || _d$metadatos3 === void 0 ? void 0 : _d$metadatos3[area]) || {}),
                  observaciones: val,
                  autor: (user === null || user === void 0 ? void 0 : user.nombre) || 'Especialista USAER',
                  fecha: new Date().toISOString()
                }
              }
            }
          };
        });
      },
      placeholder: `Aportaciones, observaciones y estrategias sugeridas para el \u00e1rea de ${area}...`,
      className: "w-full p-2 border border-slate-200 rounded-lg text-xs bg-white focus:outline-none focus:border-amber-500"
    }));
  }))), activeTab === 'evaluacion' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-4 text-xs"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
  }, "Evaluaci\xF3n Formativa y Firmas Oficiales"), /*#__PURE__*/React.createElement("div", {
    className: "grid sm:grid-cols-2 gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "border border-slate-200 p-4 rounded-xl space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-800"
  }, "Docente de Educaci\xF3n Especial"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, ((_doc$datos13 = doc.datos) === null || _doc$datos13 === void 0 ? void 0 : _doc$datos13.Docente_Especialista) || (user === null || user === void 0 ? void 0 : user.nombre)), /*#__PURE__*/React.createElement("div", {
    className: "text-emerald-700 font-semibold text-[11px]"
  }, "\u2713 Elabor\xF3 y firma digitalmente")), /*#__PURE__*/React.createElement("div", {
    className: "border border-slate-200 p-4 rounded-xl space-y-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-slate-800"
  }, "Direcci\xF3n USAER 02E"), /*#__PURE__*/React.createElement("div", {
    className: "text-slate-600"
  }, "Psic. Edgar Adrian Yam Brice\xF1o"), /*#__PURE__*/React.createElement("div", {
    className: "text-amber-700 font-semibold text-[11px]"
  }, "Vo. Bo. Institucional emitido"))))), assistantOpen && /*#__PURE__*/React.createElement("div", {
    className: "w-80 bg-white border border-slate-200 rounded-xl p-4 shadow-lg space-y-3 shrink-0"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center border-b border-slate-100 pb-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-xs text-amber-900 flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83E\uDD16 Asistente de Redacci\xF3n USAER")), /*#__PURE__*/React.createElement("button", {
    onClick: () => setAssistantOpen(false),
    className: "text-slate-400 hover:text-slate-600 font-bold"
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    className: "text-[11px] text-slate-600 leading-relaxed bg-amber-50/60 p-2.5 rounded-lg border border-amber-200"
  }, /*#__PURE__*/React.createElement("strong", null, "Regla Oficial Zona 001:"), " Escribir siempre con verbo observable en presente (ej. ", /*#__PURE__*/React.createElement("em", null, "Identifica, reconoce, produce, autorregula"), "), evitando juicios no medibles."), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => {
      const textoSugerido = "\n[Ajuste propuesto]: Segmentaci\u00f3n de tareas en bloques de 15 minutos con retroalimentaci\u00f3n visual inmediata.";
      mutarDoc(d => {
        var _d$metadatos4;
        return {
          ...d,
          metadatos: {
            ...d.metadatos,
            necesidades_confirmadas: (((_d$metadatos4 = d.metadatos) === null || _d$metadatos4 === void 0 ? void 0 : _d$metadatos4.necesidades_confirmadas) || '') + textoSugerido
          }
        };
      });
    },
    className: "w-full py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition shadow-sm cursor-pointer"
  }, "Insertar Ajuste Razonable"))));
}

// =============================================================
// COMPONENTE: ASISTENTE PEDAG\u00d3GICO IA
// =============================================================
function PedagogicalChatComponent({
  alumnoId,
  onInsertProposal
}) {
  var _alumnoAsistente, _alumnoAsistente2;
  const [messages, setMessages] = React.useState([{
    sender: 'ai',
    text: 'Hola. Soy el Asistente Pedag\u00f3gico de USAER 02-E. Puedo sugerir descriptores observables para tus alumnos alineados a los 14 indicadores de la Zona 001. \u00bfEn qu\u00e9 aprendizaje o ajuste est\u00e1s trabajando?'
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
        text: 'Error consultando el motor pedag\u00f3gico.'
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
  }, "Enviar")), modalAsistente && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-base flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "\u26A1 Asistente Pedag\xF3gico Contextualizado USAER 2E")), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Alumno: ", /*#__PURE__*/React.createElement("strong", {
    className: "text-slate-800"
  }, ((_alumnoAsistente = alumnoAsistente) === null || _alumnoAsistente === void 0 ? void 0 : _alumnoAsistente.alumno) || ((_alumnoAsistente2 = alumnoAsistente) === null || _alumnoAsistente2 === void 0 ? void 0 : _alumnoAsistente2.Nombre) || 'Alumno'), " \xB7 Zona 001 Yucat\xE1n")), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalAsistente(false),
    className: "text-slate-400 hover:text-slate-600 font-bold text-sm"
  }, "\u2715")), /*#__PURE__*/React.createElement("div", {
    className: "bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 leading-relaxed"
  }, /*#__PURE__*/React.createElement("strong", null, "\uD83D\uDCA1 Filtro de Pertinencia Pedag\xF3gica Activo:"), " Las propuestas se adaptan estrictamente al nivel real de aprendizaje y al m\xE9todo docente elegido. Para alumnos en etapa inicial/presil\xE1bica, se omiten tareas abstractas y se prioriza la estimulaci\xF3n multisensorial y fonol\xF3gica."), /*#__PURE__*/React.createElement("div", {
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 sm:grid-cols-2 gap-3"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Nivel Real de Desempe\xF1o:"), /*#__PURE__*/React.createElement("select", {
    value: nivelAprendizaje,
    onChange: e => setNivelAprendizaje(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white font-semibold"
  }, /*#__PURE__*/React.createElement("option", {
    value: "Presil\xE1bico / Inicial"
  }, "Presil\xE1bico / Inicial (Sin lectoescritura aut\xF3noma)"), /*#__PURE__*/React.createElement("option", {
    value: "Sil\xE1bico"
  }, "Sil\xE1bico (Reconoce s\xEDlabas directas / palabras breves)"), /*#__PURE__*/React.createElement("option", {
    value: "Alfab\xE9tico"
  }, "Alfab\xE9tico (Lectura de enunciados cotidianos)"), /*#__PURE__*/React.createElement("option", {
    value: "Consolidado / Funcional"
  }, "Consolidado / Funcional (Comprensi\xF3n aut\xF3noma)"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "M\xE9todo Pedag\xF3gico Docente:"), /*#__PURE__*/React.createElement("select", {
    value: metodoSeleccionado,
    onChange: e => setMetodoSeleccionado(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white font-semibold"
  }, /*#__PURE__*/React.createElement("option", {
    value: "M\xE9todo Troncoso y Material Multisensorial"
  }, "M\xE9todo Troncoso y Material Multisensorial"), /*#__PURE__*/React.createElement("option", {
    value: "Conciencia Fonol\xF3gica y Asociaci\xF3n"
  }, "Conciencia Fonol\xF3gica y Asociaci\xF3n"), /*#__PURE__*/React.createElement("option", {
    value: "M\xE9todo Minjares"
  }, "M\xE9todo Minjares"), /*#__PURE__*/React.createElement("option", {
    value: "M\xE9todo Singapur / COPISI (Matem\xE1ticas)"
  }, "M\xE9todo Singapur / COPISI (Matem\xE1ticas)"), /*#__PURE__*/React.createElement("option", {
    value: "SAAC / Pictogramas PECS (Comunicaci\xF3n)"
  }, "SAAC / Pictogramas PECS (Comunicaci\xF3n)"), /*#__PURE__*/React.createElement("option", {
    value: "Proyectos Comunitarios NEM"
  }, "Proyectos Comunitarios NEM"), /*#__PURE__*/React.createElement("option", {
    value: "Secuencia Did\xE1ctica Adaptada"
  }, "Secuencia Did\xE1ctica Adaptada")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Apoyos DUA y Recursos Requeridos:"), /*#__PURE__*/React.createElement("div", {
    className: "flex flex-wrap gap-2"
  }, ['Material concreto manipulable', 'Claves visuales y pictogramas', 'Modelado previo', 'Pasos cortos y claros', 'Tiempo flexible', 'Bandeja sensorial'].map(ap => {
    const sel = apoyosSeleccionados.includes(ap);
    return /*#__PURE__*/React.createElement("button", {
      key: ap,
      type: "button",
      onClick: () => {
        if (sel) setApoyosSeleccionados(apoyosSeleccionados.filter(x => x !== ap));else setApoyosSeleccionados([...apoyosSeleccionados, ap]);
      },
      className: `px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition ${sel ? 'bg-amber-600 text-white border-amber-600' : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'}`
    }, sel ? '\u2713 ' : '+ ', ap);
  }))), /*#__PURE__*/React.createElement("div", {
    className: "pt-2"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: ejecutarGeneradorPropuesta,
    disabled: generandoPropuesta,
    className: "w-full bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold py-2.5 rounded-xl transition flex items-center justify-center space-x-2 shadow"
  }, /*#__PURE__*/React.createElement("span", null, generandoPropuesta ? 'Analizando antecedentes y generando propuesta...' : '\u26a1 Generar Propuesta de Actividad Pertinente'))), propuestaIA && /*#__PURE__*/React.createElement("div", {
    className: "space-y-3 pt-3 border-t border-slate-200"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded"
  }, "Propuesta Generada \xB7 ", propuestaIA.origen), /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] text-slate-500"
  }, "Puedes editar el texto antes de insertarlo")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-800 block mb-1"
  }, "Revisi\xF3n y Ajuste Docente (Editable):"), /*#__PURE__*/React.createElement("textarea", {
    rows: "6",
    value: textoEditadoPropuesta,
    onChange: e => setTextoEditadoPropuesta(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-amber-300 bg-amber-50/30 text-xs font-mono leading-relaxed"
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-end space-x-2 pt-2"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalAsistente(false),
    className: "bg-slate-100 text-slate-700 px-4 py-2 rounded-xl font-semibold"
  }, "\u2715 Descartar"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: ejecutarGeneradorPropuesta,
    className: "bg-slate-200 hover:bg-slate-300 text-slate-800 px-4 py-2 rounded-xl font-semibold"
  }, "\uD83D\uDD04 Regenerar"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: aceptarPropuestaEnPlaneacion,
    className: "bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl font-bold shadow transition"
  }, "\u2705 Aceptar e Insertar en Planeaci\xF3n")))))));
}

// =============================================================
// VISTA 3: EXPEDIENTES INTEGRALES (307 ALUMNOS, L\u00cdNEA DE TIEMPO)
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
      console.error("Error al cargar padr\u00f3n de alumnos:", err);
      setErrorAlumnos(err.message || 'Error cargando padr\u00f3n');
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
  }, ((_expediente$alumno7 = expediente.alumno) === null || _expediente$alumno7 === void 0 ? void 0 : _expediente$alumno7.condicion) || 'Atenci\u00f3n USAER')), /*#__PURE__*/React.createElement("div", {
    className: "flex border-b border-slate-200 space-x-1 text-xs font-bold overflow-x-auto pb-1"
  }, [{
    id: 'resumen',
    label: 'Resumen e Historia'
  }, {
    id: 'epp',
    label: 'Evaluaci\u00f3n Psicopedag\u00f3gica (EPP)'
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
    label: 'Derivaci\u00f3n y Salud'
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
  }, ((_expediente$alumno9 = expediente.alumno) === null || _expediente$alumno9 === void 0 ? void 0 : _expediente$alumno9.tipo_atencion) || 'Atenci\u00f3n Focalizada')), /*#__PURE__*/React.createElement("div", {
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
  }, /*#__PURE__*/React.createElement("span", null, "Detecci\xF3n BAP ", b.tipo_deteccion === 'GRUPAL' ? '\u00b7 GRUPAL DE AULA' : ''), /*#__PURE__*/React.createElement("span", {
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
// VISTA 4: EVALUACI\u00d3N PSICOPEDAG\u00d3GICA (EPP MULTI-\u00c1REA VIVA)
// =============================================================
function EPPView({
  user,
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

  // Generador de Propuestas SEGEY state
  const [propVerbo, setPropVerbo] = React.useState('consolidar');
  const [propContenido, setPropContenido] = React.useState('graf\u00edas y sonidos correspondientes en lectura funcional');
  const [propApoyo, setPropApoyo] = React.useState('mediante apoyos visuales y modelado directo');
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
    const cleanId = String(alumnoId || '').replace('epp-', '').trim();
    setSelectedAlumnoId(cleanId);
    setLoadingDoc(true);
    setGuardadoExito(false);
    try {
      const doc = await apiRequest(`/api/epp/${cleanId}`);
      setEppDoc(doc);
    } catch (err) {
      console.error("Error abriendo EPP:", err);
      alert("Error abriendo informe EPP: " + err.message);
    } finally {
      setLoadingDoc(false);
    }
  };
  const guardarEPP = async () => {
    if (!eppDoc || !selectedAlumnoId) return;
    setGuardando(true);
    setGuardadoExito(false);
    const t0 = performance.now();
    try {
      const payload = {
        alumno: selectedAlumnoId,
        ciclo: eppDoc.ciclo || '2026-2027',
        partes: eppDoc.partes || {}
      };
      await apiRequest('/api/epp', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setGuardadoExito(true);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 1
      }));
      setTimeout(() => setGuardadoExito(false), 3000);
    } catch (err) {
      console.error("Error guardando EPP:", err);
      alert("Error guardando EPP: " + err.message);
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
  const insertarInstrumento = (area, nombrePrueba) => {
    const partes = (eppDoc === null || eppDoc === void 0 ? void 0 : eppDoc.partes) || {};
    const areaObj = partes[area] || {};
    const textoActual = areaObj.instrumentos_aplicados || areaObj['3.1. Pruebas psicom\u00e9tricas'] || '';
    const nuevoTexto = textoActual ? `${textoActual}
\u2022 ${nombrePrueba}` : `\u2022 ${nombrePrueba}`;
    mutarParte(area, 'instrumentos_aplicados', nuevoTexto);
  };
  const insertarPropuestaFormula = () => {
    const partes = (eppDoc === null || eppDoc === void 0 ? void 0 : eppDoc.partes) || {};
    const concObj = partes['Conclusi\u00f3n'] || partes.Conclusion || partes.conclusion || {};
    const textoActual = concObj.conclusion_integral || concObj.propuesta || '';
    const formula = `El alumno/a necesita ${propVerbo} ${propContenido} ${propApoyo}.`;
    const nuevoTexto = textoActual ? `${textoActual}

${formula}` : formula;
    mutarParte('Conclusi\u00f3n', 'conclusion_integral', nuevoTexto);
    alert("Propuesta formal insertada en la Conclusi\u00f3n integral con la f\u00f3rmula oficial SEGEY.");
  };
  const filtrados = listaEPP.filter(e => {
    const nom = (e.nombre_alumno || e.alumno_nombre || '').toLowerCase();
    const esc = (e.escuela || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q) || (e.alumno_id || '').toLowerCase().includes(q);
  });
  const alumnoSeleccionadoInfo = alumnosList.find(a => a.id === selectedAlumnoId) || {};

  // Determinaci\u00f3n de permisos por \u00e1rea
  const rolUser = ((user === null || user === void 0 ? void 0 : user.rol) || '').toUpperCase();
  const esDirector = (user === null || user === void 0 ? void 0 : user.director) || rolUser.includes('DIRECTOR') || rolUser.includes('ADMIN');
  const puedeEditarAprendizaje = esDirector || rolUser.includes('APOYO');
  const puedeEditarPsicologia = esDirector || rolUser.includes('PSIC');
  const puedeEditarComunicacion = esDirector || rolUser.includes('COM');
  const puedeEditarTrabajoSocial = esDirector || rolUser.includes('TRABAJO');
  if (selectedAlumnoId && eppDoc) {
    const partes = eppDoc.partes || {};
    const pAprendizaje = partes.Aprendizaje || partes.APRENDIZAJE || {};
    const pPsicologia = partes.Psicolog\u00eda || partes.PSICOLOGIA || {};
    const pComunicacion = partes.Comunicaci\u00f3n || partes.COMUNICACION || {};
    const pTrabajoSocial = partes['Trabajo Social'] || partes.TRABAJO_SOCIAL || {};
    const pConclusion = partes.Conclusi\u00f3n || partes.CONCLUSION || partes.Conclusion || {};
    return /*#__PURE__*/React.createElement("div", {
      className: "space-y-5"
    }, /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-3"
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => {
        setSelectedAlumnoId(null);
        setEppDoc(null);
      },
      className: "px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition cursor-pointer"
    }, "\u2190 Volver a Lista EPP"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
      className: "text-lg font-bold text-slate-900"
    }, alumnoSeleccionadoInfo.nombre_completo || eppDoc.nombre_alumno || selectedAlumnoId), /*#__PURE__*/React.createElement("div", {
      className: "text-xs text-slate-500"
    }, "Escuela: ", alumnoSeleccionadoInfo.escuela || 'USAER 2E', " \u2022 Ciclo: ", eppDoc.ciclo || '2026-2027', " \u2022 Revisi\xF3n: ", eppDoc.revision ? eppDoc.revision.slice(0, 10) : 'Vigente'))), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, guardadoExito && /*#__PURE__*/React.createElement("span", {
      className: "text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200"
    }, "\u2713 Guardado confirmado"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => descargarArchivoAutenticado(`/api/epp/${selectedAlumnoId}/pdf`, `EPP_${selectedAlumnoId}.pdf`),
      className: "px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm cursor-pointer"
    }, /*#__PURE__*/React.createElement("span", null, "Descargar PDF (Anexo XVII)"), /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCC4")), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: guardarEPP,
      disabled: guardando,
      className: "px-4 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow cursor-pointer"
    }, /*#__PURE__*/React.createElement("span", null, guardando ? 'Guardando...' : '\u1f4be Guardar EPP')))), /*#__PURE__*/React.createElement("div", {
      className: "flex border-b border-slate-200 space-x-1 text-sm font-semibold overflow-x-auto"
    }, [{
      id: 'Aprendizaje',
      label: '\u1f4d6 Aprendizaje',
      canEdit: puedeEditarAprendizaje
    }, {
      id: 'Psicolog\u00eda',
      label: '\u1f9e0 Psicolog\u00eda',
      canEdit: puedeEditarPsicologia
    }, {
      id: 'Comunicaci\u00f3n',
      label: '\u1f5e3\ufe0f Comunicaci\u00f3n',
      canEdit: puedeEditarComunicacion
    }, {
      id: 'Trabajo Social',
      label: '\u1f3e0 Trabajo Social',
      canEdit: puedeEditarTrabajoSocial
    }, {
      id: 'Conclusi\u00f3n',
      label: '\u1f4cb Conclusi\u00f3n e Intervenci\u00f3n',
      canEdit: true
    }].map(tab => /*#__PURE__*/React.createElement("button", {
      key: tab.id,
      type: "button",
      onClick: () => setActiveArea(tab.id),
      className: `px-4 py-2.5 border-b-2 font-bold transition text-xs sm:text-sm whitespace-nowrap cursor-pointer flex items-center space-x-1.5 ${activeArea === tab.id ? 'border-amber-600 text-amber-700 bg-amber-50/50' : 'border-transparent text-slate-500 hover:text-slate-800'}`
    }, /*#__PURE__*/React.createElement("span", null, tab.label), !tab.canEdit && /*#__PURE__*/React.createElement("span", {
      className: "text-[10px] bg-slate-200 text-slate-600 px-1.5 py-0.2 rounded font-normal"
    }, "Lectura")))), activeArea === 'Aprendizaje' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center border-b border-slate-100 pb-2"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
    }, "Evaluaci\xF3n del \xC1rea Pedag\xF3gica y de Aprendizaje"), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-slate-500 font-semibold mr-1"
    }, "Cat\xE1logo SEGEY 2014:"), ['Prueba Pedag\u00f3gica', 'Margarita G\u00f3mez Palacio', 'Matem\u00e1ticas Funcionales', 'Estilo de Aprendizaje'].map(p => /*#__PURE__*/React.createElement("button", {
      key: p,
      type: "button",
      onClick: () => insertarInstrumento('Aprendizaje', p),
      disabled: !puedeEditarAprendizaje,
      className: "text-[11px] bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-800 px-2 py-0.5 rounded font-medium transition cursor-pointer"
    }, "+ ", p)))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Instrumentos y Pruebas Pedag\xF3gicas Aplicadas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pAprendizaje.instrumentos_aplicados || '',
      onChange: e => mutarParte('Aprendizaje', 'instrumentos_aplicados', e.target.value),
      disabled: !puedeEditarAprendizaje,
      placeholder: "Registrar pruebas aplicadas por el \xE1rea pedag\xF3gica...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Lectura y Escritura Funcional:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pAprendizaje['4.1. Lectura y escritura funcional'] || '',
      onChange: e => mutarParte('Aprendizaje', '4.1. Lectura y escritura funcional', e.target.value),
      disabled: !puedeEditarAprendizaje,
      placeholder: "Nivel presil\xE1bico/sil\xE1bico, reconocimiento de graf\xEDas, segmentaci\xF3n...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Pensamiento Matem\xE1tico Funcional:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pAprendizaje['4.1. Matem\u00e1ticas funcionales'] || '',
      onChange: e => mutarParte('Aprendizaje', '4.1. Matem\u00e1ticas funcionales', e.target.value),
      disabled: !puedeEditarAprendizaje,
      placeholder: "Conteo oral, resoluci\xF3n de problemas con material concreto, correspondencia 1 a 1...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })))), activeArea === 'Psicolog\u00eda' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center border-b border-slate-100 pb-2"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
    }, "Evaluaci\xF3n Psicol\xF3gica, Cognitiva y Afectivo-Social"), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-slate-500 font-semibold mr-1"
    }, "Bater\xEDa SEGEY 2014:"), ['WISC-IV', 'ENI', 'Bender', 'Raven', 'Rey', 'Frostig', 'DFH', 'CREA', 'BAS 1-3', 'Conners'].map(p => /*#__PURE__*/React.createElement("button", {
      key: p,
      type: "button",
      onClick: () => insertarInstrumento('Psicolog\u00eda', p),
      disabled: !puedeEditarPsicologia,
      className: "text-[11px] bg-blue-50 hover:bg-blue-100 border border-blue-300 text-blue-800 px-2 py-0.5 rounded font-medium transition cursor-pointer"
    }, "+ ", p)))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Pruebas Psicom\xE9tricas y Neuropsicol\xF3gicas Aplicadas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pPsicologia.instrumentos_aplicados || pPsicologia['3.1. Pruebas psicom\u00e9tricas'] || '',
      onChange: e => mutarParte('Psicolog\u00eda', 'instrumentos_aplicados', e.target.value),
      disabled: !puedeEditarPsicologia,
      placeholder: "Listar instrumentos aplicados...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Capacidad Intelectual y Funcionamiento Cognitivo:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pPsicologia['3.2. Capacidad intelectual'] || pPsicologia.capacidad_intelectual || '',
      onChange: e => mutarParte('Psicolog\u00eda', '3.2. Capacidad intelectual', e.target.value),
      disabled: !puedeEditarPsicologia,
      placeholder: "Memoria de trabajo, velocidad de procesamiento, comprensi\xF3n verbal...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Atenci\xF3n, Conducta y Autorregulaci\xF3n Emocional:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pPsicologia['3.4. Conducta adaptativa'] || pPsicologia.conducta || '',
      onChange: e => mutarParte('Psicolog\u00eda', '3.4. Conducta adaptativa', e.target.value),
      disabled: !puedeEditarPsicologia,
      placeholder: "Tolerancia a la frustraci\xF3n, permanencia en la tarea, seguimiento de reglas...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })))), activeArea === 'Comunicaci\u00f3n' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center border-b border-slate-100 pb-2"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
    }, "Evaluaci\xF3n de Comunicaci\xF3n y Lenguaje"), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-slate-500 font-semibold mr-1"
    }, "Pruebas SEGEY:"), ['Prueba Flores', 'Prueba Laiz', 'Bove & Perkins', 'Anexo X', 'Anexo XI', 'Anexo XII'].map(p => /*#__PURE__*/React.createElement("button", {
      key: p,
      type: "button",
      onClick: () => insertarInstrumento('Comunicaci\u00f3n', p),
      disabled: !puedeEditarComunicacion,
      className: "text-[11px] bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800 px-2 py-0.5 rounded font-medium transition cursor-pointer"
    }, "+ ", p)))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Instrumentos y Bater\xEDas de Lenguaje Aplicadas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pComunicacion.instrumentos_aplicados || '',
      onChange: e => mutarParte('Comunicaci\u00f3n', 'instrumentos_aplicados', e.target.value),
      disabled: !puedeEditarComunicacion,
      placeholder: "Listar instrumentos de lenguaje...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Nivel Fonol\xF3gico, Sem\xE1ntico y Sint\xE1ctico:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pComunicacion['4.1. Comprensi\u00f3n expresiva'] || pComunicacion['4.1. Lenguaje oral: fonol\u00f3gico'] || '',
      onChange: e => mutarParte('Comunicaci\u00f3n', '4.1. Comprensi\u00f3n expresiva', e.target.value),
      disabled: !puedeEditarComunicacion,
      placeholder: "Puntos y modos de articulaci\xF3n, inteligibilidad, estructuraci\xF3n de enunciados...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Pragm\xE1tica e Intenci\xF3n Comunicativa:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pComunicacion['4.1. Lenguaje oral: pragm\u00e1tico'] || '',
      onChange: e => mutarParte('Comunicaci\u00f3n', '4.1. Lenguaje oral: pragm\u00e1tico', e.target.value),
      disabled: !puedeEditarComunicacion,
      placeholder: "Contacto visual, turnos de habla, adaptaci\xF3n comunicativa en el aula...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })))), activeArea === 'Trabajo Social' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center border-b border-slate-100 pb-2"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide"
    }, "Estudio de Contexto Sociofamiliar y Din\xE1mica del Hogar"), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center gap-1.5 flex-wrap"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] text-slate-500 font-semibold mr-1"
    }, "Instrumentos SEGEY:"), ['Entrevista Sociofamiliar', 'Ficha Socioecon\u00f3mica', 'Anexo VIII'].map(p => /*#__PURE__*/React.createElement("button", {
      key: p,
      type: "button",
      onClick: () => insertarInstrumento('Trabajo Social', p),
      disabled: !puedeEditarTrabajoSocial,
      className: "text-[11px] bg-purple-50 hover:bg-purple-100 border border-purple-300 text-purple-800 px-2 py-0.5 rounded font-medium transition cursor-pointer"
    }, "+ ", p)))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Instrumentos Sociofamiliares Utilizados:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "2",
      value: pTrabajoSocial.instrumentos_aplicados || '',
      onChange: e => mutarParte('Trabajo Social', 'instrumentos_aplicados', e.target.value),
      disabled: !puedeEditarTrabajoSocial,
      placeholder: "Entrevistas realizadas, fechas y participantes...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Estructura y Din\xE1mica Familiar:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "3",
      value: pTrabajoSocial.dinamica_familiar || pTrabajoSocial['6.2. Contexto familiar'] || '',
      onChange: e => mutarParte('Trabajo Social', 'dinamica_familiar', e.target.value),
      disabled: !puedeEditarTrabajoSocial,
      placeholder: "Cuidadores principales, redes de apoyo, pautas de crianza y ambiente familiar...",
      className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 disabled:bg-slate-50 font-sans"
    })))), activeArea === 'Conclusi\u00f3n' && /*#__PURE__*/React.createElement("div", {
      className: "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-5"
    }, /*#__PURE__*/React.createElement("h3", {
      className: "text-sm font-bold text-slate-800 uppercase tracking-wide border-b border-slate-100 pb-2"
    }, "Conclusi\xF3n Integral y Propuesta de Ajustes Razonables"), /*#__PURE__*/React.createElement("div", {
      className: "bg-amber-50/70 border border-amber-200 p-4 rounded-xl space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", {
      className: "font-bold text-amber-900 flex items-center justify-between"
    }, /*#__PURE__*/React.createElement("span", null, "\u26A1 Generador Sint\xE1ctico de Propuestas (Manual SEGEY 2014)"), /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] font-normal text-amber-800"
    }, "F\xF3rmula: [Necesita] + [Verbo] + [Contenido] + [Apoyo]")), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-1 sm:grid-cols-3 gap-2.5"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
      className: "text-slate-600 block mb-1 font-semibold"
    }, "1. Verbo observable:"), /*#__PURE__*/React.createElement("select", {
      value: propVerbo,
      onChange: e => setPropVerbo(e.target.value),
      className: "w-full p-1.5 border border-amber-300 rounded bg-white text-slate-800"
    }, /*#__PURE__*/React.createElement("option", {
      value: "consolidar"
    }, "consolidar"), /*#__PURE__*/React.createElement("option", {
      value: "identificar"
    }, "identificar"), /*#__PURE__*/React.createElement("option", {
      value: "autorregular"
    }, "autorregular"), /*#__PURE__*/React.createElement("option", {
      value: "estructurar"
    }, "estructurar"), /*#__PURE__*/React.createElement("option", {
      value: "decodificar"
    }, "decodificar"), /*#__PURE__*/React.createElement("option", {
      value: "comunicar"
    }, "comunicar"), /*#__PURE__*/React.createElement("option", {
      value: "expresar"
    }, "expresar"), /*#__PURE__*/React.createElement("option", {
      value: "participar"
    }, "participar en"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
      className: "text-slate-600 block mb-1 font-semibold"
    }, "2. Contenido / Habilidad:"), /*#__PURE__*/React.createElement("input", {
      type: "text",
      value: propContenido,
      onChange: e => setPropContenido(e.target.value),
      className: "w-full p-1.5 border border-amber-300 rounded bg-white text-slate-800"
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
      className: "text-slate-600 block mb-1 font-semibold"
    }, "3. Apoyo / Ajuste:"), /*#__PURE__*/React.createElement("input", {
      type: "text",
      value: propApoyo,
      onChange: e => setPropApoyo(e.target.value),
      className: "w-full p-1.5 border border-amber-300 rounded bg-white text-slate-800"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-amber-950 font-mono bg-white px-2 py-1 rounded border border-amber-200"
    }, "Vista previa: ", /*#__PURE__*/React.createElement("em", null, "El alumno/a necesita ", propVerbo, " ", propContenido, " ", propApoyo, ".")), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: insertarPropuestaFormula,
      className: "px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded text-xs transition cursor-pointer shrink-0"
    }, "\u2795 Insertar en Conclusi\xF3n"))), /*#__PURE__*/React.createElement("div", {
      className: "space-y-3 text-xs"
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      className: "font-bold text-slate-700 block mb-1"
    }, "Conclusi\xF3n Diagn\xF3stica e Integraci\xF3n de Necesidades Espec\xEDficas:"), /*#__PURE__*/React.createElement("textarea", {
      rows: "6",
      value: pConclusion.conclusion_integral || pConclusion.propuesta || '',
      onChange: e => mutarParte('Conclusi\u00f3n', 'conclusion_integral', e.target.value),
      placeholder: "Redactar el dictamen multidisciplinario integral integrando los hallazgos de Aprendizaje, Psicolog\xEDa, Comunicaci\xF3n y Trabajo Social...",
      className: "w-full p-3 border border-slate-200 rounded-xl text-slate-800 focus:border-amber-500 font-sans leading-relaxed"
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
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition cursor-pointer"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Evaluaci\xF3n Psicopedag\xF3gica (EPP)"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Informes multidisciplinarios integrales y dictamen de apoyos espec\xEDficos"))), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " informes activos")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, escuela o clave de expediente...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando evaluaciones psicopedag\xF3gicas...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay evaluaciones registradas con los criterios especificados.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, filtrados.map((epp, idx) => {
    const targetId = String(epp.alumno_id || epp.alumno || epp.id || '').replace('epp-', '').trim();
    return /*#__PURE__*/React.createElement("div", {
      key: idx,
      className: "p-4 bg-white rounded-xl border border-slate-200 text-xs space-y-3 hover:border-amber-400 transition"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center font-bold text-slate-900"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-sm"
    }, epp.nombre_alumno || epp.alumno_nombre || targetId), /*#__PURE__*/React.createElement("span", {
      className: "text-[11px] font-normal text-slate-400"
    }, "(", targetId, ")")), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => descargarArchivoAutenticado(`/api/epp/${targetId}/pdf`, `EPP_${targetId}.pdf`),
      className: "px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer"
    }, "\uD83D\uDCC4 PDF"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => abrirEPP(targetId),
      className: "px-3 py-1 bg-slate-800 hover:bg-slate-900 text-white rounded font-bold text-[11px] transition cursor-pointer"
    }, "Abrir EPP \u2192"))), /*#__PURE__*/React.createElement("div", {
      className: "text-slate-500"
    }, /*#__PURE__*/React.createElement("span", null, "Escuela: ", /*#__PURE__*/React.createElement("strong", null, epp.escuela || 'USAER 2E')), /*#__PURE__*/React.createElement("span", {
      className: "mx-2"
    }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Ciclo: ", epp.ciclo || '2026-2027'), /*#__PURE__*/React.createElement("span", {
      className: "mx-2"
    }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Especialista: ", epp.coordinadora || epp.creada_por || 'Equipo USAER')), /*#__PURE__*/React.createElement("div", {
      className: "grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-xs"
    }, ['Aprendizaje', 'Psicolog\u00eda', 'Comunicaci\u00f3n', 'Trabajo Social'].map(area => {
      const tieneDatos = Array.isArray(epp.areas_registradas) && (epp.areas_registradas.includes(area) || epp.areas_registradas.includes(area.toUpperCase()));
      return /*#__PURE__*/React.createElement("div", {
        key: area,
        className: `p-2 rounded-lg border ${tieneDatos ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900' : 'bg-slate-50 border-slate-200 text-slate-400'}`
      }, /*#__PURE__*/React.createElement("div", {
        className: "font-bold flex items-center justify-between text-[11px]"
      }, /*#__PURE__*/React.createElement("span", null, area), /*#__PURE__*/React.createElement("span", null, tieneDatos ? '\u2713' : '\u2022')));
    })));
  })));
}

// =============================================================
// VISTA 5: ANEXO III - DETECCI\u00d3N DE BAP (INDIVIDUAL Y GRUPAL)
// =============================================================
function Anexo3View({
  user,
  onBack,
  setMetrics
}) {
  const [baps, setBaps] = React.useState([]);
  const [alumnos, setAlumnos] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [modalNuevo, setModalNuevo] = React.useState(false);
  const [editandoId, setEditandoId] = React.useState(null);

  // Form state
  const [alumnoId, setAlumnoId] = React.useState('');
  const [esGrupal, setEsGrupal] = React.useState(false);
  const [fisicas, setFisicas] = React.useState('');
  const [actitudinales, setActitudinales] = React.useState('');
  const [pedagogicas, setPedagogicas] = React.useState('');
  const [organizativas, setOrganizativas] = React.useState('');
  const [apoyos, setApoyos] = React.useState('');
  const [guardando, setGuardando] = React.useState(false);
  const cargarDatos = () => {
    setLoading(true);
    Promise.all([apiRequest('/api/anexo3'), apiRequest('/api/alumnos')]).then(([dataBaps, dataAlu]) => {
      setBaps(dataBaps || []);
      setAlumnos(dataAlu || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  React.useEffect(() => {
    cargarDatos();
  }, []);
  const abrirNuevo = () => {
    var _alumnos$;
    setEditandoId(null);
    setAlumnoId(((_alumnos$ = alumnos[0]) === null || _alumnos$ === void 0 ? void 0 : _alumnos$.id) || '');
    setEsGrupal(false);
    setFisicas('');
    setActitudinales('');
    setPedagogicas('');
    setOrganizativas('');
    setApoyos('');
    setModalNuevo(true);
  };
  const abrirEditar = b => {
    setEditandoId(b.id || b.ID_BAP);
    setAlumnoId(b.id_alumno || b.ID_Alumno || '');
    setEsGrupal(b.es_grupal || b.modalidad === 'Grupal');
    setFisicas(b.fisicas || b.Fisicas || '');
    setActitudinales(b.actitudinales || b.Actitudinales || '');
    setPedagogicas(b.pedagogicas || b.Pedagogicas || b.Curriculares || '');
    setOrganizativas(b.organizativas || b.Organizativas || '');
    setApoyos(b.apoyos || b.Apoyos || '');
    setModalNuevo(true);
  };
  const handleGuardar = async e => {
    var _user$escuelas_permit;
    e.preventDefault();
    setGuardando(true);
    const selAlu = alumnos.find(a => a.id === alumnoId);
    const payload = {
      id: editandoId || 'bap-' + Date.now(),
      id_alumno: esGrupal ? 'GRUPAL' : alumnoId,
      nombre_alumno: esGrupal ? 'Contexto \u00c1ulico / Grupal' : (selAlu === null || selAlu === void 0 ? void 0 : selAlu.nombre_completo) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.Nombre) || alumnoId,
      escuela: (selAlu === null || selAlu === void 0 ? void 0 : selAlu.nombre_escuela) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.Nombre_Escuela) || (user === null || user === void 0 || (_user$escuelas_permit = user.escuelas_permitidas) === null || _user$escuelas_permit === void 0 ? void 0 : _user$escuelas_permit[0]) || 'USAER 02E',
      es_grupal: esGrupal,
      fisicas,
      actitudinales,
      pedagogicas,
      organizativas,
      apoyos,
      fecha: new Date().toISOString().split('T')[0]
    };
    try {
      if (editandoId) {
        await apiRequest('/api/anexo3/' + editandoId, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiRequest('/api/anexo3', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      setModalNuevo(false);
      cargarDatos();
    } catch (err) {
      alert('Error al guardar BAP: ' + err.message);
    } finally {
      setGuardando(false);
    }
  };
  const handleAnular = async id => {
    if (!confirm('\u00bfConfirma la anulaci\u00f3n l\u00f3gica de esta detecci\u00f3n de BAP?')) return;
    try {
      await apiRequest('/api/anexo3/' + id, {
        method: 'DELETE'
      });
      cargarDatos();
    } catch (err) {
      alert('Error al anular: ' + err.message);
    }
  };
  const filtrados = baps.filter(b => {
    if (b.Estado === 'ANULADO') return false;
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
    className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo III \u2014 Detecci\xF3n de BAP"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Identificaci\xF3n de Barreras para el Aprendizaje y la Participaci\xF3n en 4 contextos oficiales."))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " registros"), /*#__PURE__*/React.createElement("button", {
    onClick: abrirNuevo,
    className: "text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold px-4 py-2 rounded-xl shadow transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "+ Nueva Detecci\xF3n BAP")))), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, escuela o barrera...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando registros de BAP...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 bg-white rounded-2xl border border-slate-200 p-8"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-3xl mb-2"
  }, "\uD83D\uDEA7"), /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-700"
  }, "Sin registros de BAP"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500 mt-1"
  }, "Presiona \"+ Nueva Detecci\xF3n BAP\" para registrar barreras individuales o de contexto \xE1ulico.")) : /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-left text-xs"
  }, /*#__PURE__*/React.createElement("thead", {
    className: "bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider"
  }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Alumno / Contexto"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Escuela"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "F\xEDsicas / Arq."), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Actitudinales"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Pedag\xF3gicas / Curr."), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Organizativas"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Apoyos / Recursos"), /*#__PURE__*/React.createElement("th", {
    className: "p-3 text-right"
  }, "Acciones"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, filtrados.map(b => /*#__PURE__*/React.createElement("tr", {
    key: b.id || b.ID_BAP,
    className: "hover:bg-slate-50/80 transition"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-semibold text-slate-900"
  }, b.nombre_alumno || b.Nombre_Alumno || 'Contexto \u00c1ulico'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, b.escuela || b.Escuela || 'USAER 02E'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600 max-w-[150px] truncate",
    title: b.fisicas || b.Fisicas
  }, b.fisicas || b.Fisicas || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600 max-w-[150px] truncate",
    title: b.actitudinales || b.Actitudinales
  }, b.actitudinales || b.Actitudinales || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600 max-w-[150px] truncate",
    title: b.pedagogicas || b.Pedagogicas || b.Curriculares
  }, b.pedagogicas || b.Pedagogicas || b.Curriculares || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600 max-w-[150px] truncate",
    title: b.organizativas || b.Organizativas
  }, b.organizativas || b.Organizativas || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600 max-w-[150px] truncate",
    title: b.apoyos || b.Apoyos
  }, b.apoyos || b.Apoyos || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-right space-x-1 whitespace-nowrap"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => abrirEditar(b),
    className: "bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition"
  }, "Editar"), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/anexo3/' + (b.id || b.ID_BAP) + '/pdf', 'Anexo_III_' + (b.id || b.ID_BAP) + '.pdf'),
    className: "bg-amber-100 hover:bg-amber-200 text-amber-900 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition"
  }, "PDF"), /*#__PURE__*/React.createElement("button", {
    onClick: () => handleAnular(b.id || b.ID_BAP),
    className: "text-red-600 hover:text-red-800 px-2 py-1 text-[11px] font-semibold",
    title: "Anular l\xF3gicamente"
  }, "\u2715")))))))), modalNuevo && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-base"
  }, editandoId ? 'Editar Detecci\u00f3n de BAP' : 'Nueva Detecci\u00f3n de BAP (Anexo III)'), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalNuevo(false),
    className: "text-slate-400 hover:text-slate-600 font-bold text-sm"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleGuardar,
    className: "space-y-4 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-4 bg-slate-50 p-3 rounded-xl border border-slate-200"
  }, /*#__PURE__*/React.createElement("label", {
    className: "flex items-center space-x-2 cursor-pointer"
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    checked: !esGrupal,
    onChange: () => setEsGrupal(false),
    className: "text-amber-600"
  }), /*#__PURE__*/React.createElement("span", {
    className: "font-semibold text-slate-700"
  }, "Detecci\xF3n Individual")), /*#__PURE__*/React.createElement("label", {
    className: "flex items-center space-x-2 cursor-pointer"
  }, /*#__PURE__*/React.createElement("input", {
    type: "radio",
    checked: esGrupal,
    onChange: () => setEsGrupal(true),
    className: "text-amber-600"
  }), /*#__PURE__*/React.createElement("span", {
    className: "font-semibold text-slate-700"
  }, "Contexto \xC1ulico / Grupal"))), !esGrupal && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Alumno Autorizado:"), /*#__PURE__*/React.createElement("select", {
    value: alumnoId,
    onChange: e => setAlumnoId(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white",
    required: true
  }, alumnos.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre_completo || a.Nombre, " \u2014 ", a.nombre_escuela || a.Nombre_Escuela, " (", a.Grado || a.grado, "\xB0", a.Grupo || a.grupo, ")")))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 gap-3"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "1. Barreras F\xEDsicas / Arquitect\xF3nicas:"), /*#__PURE__*/React.createElement("textarea", {
    value: fisicas,
    onChange: e => setFisicas(e.target.value),
    placeholder: "Accesibilidad, rampas, iluminaci\xF3n, mobiliario...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "2. Barreras Actitudinales / Sociales:"), /*#__PURE__*/React.createElement("textarea", {
    value: actitudinales,
    onChange: e => setActitudinales(e.target.value),
    placeholder: "Prejuicios, sobreprotecci\xF3n, exclusi\xF3n, bajas expectativas...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "3. Barreras Pedag\xF3gicas / Curriculares:"), /*#__PURE__*/React.createElement("textarea", {
    value: pedagogicas,
    onChange: e => setPedagogicas(e.target.value),
    placeholder: "Metodolog\xEDas homog\xE9neas, falta de DUA, evaluaci\xF3n r\xEDgida...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "4. Barreras Organizativas / Normativas:"), /*#__PURE__*/React.createElement("textarea", {
    value: organizativas,
    onChange: e => setOrganizativas(e.target.value),
    placeholder: "Tiempos inflexibles, falta de coordinaci\xF3n entre docentes...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200"
  }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Apoyos y Recursos Requeridos (DUA / Ajustes Razonables):"), /*#__PURE__*/React.createElement("textarea", {
    value: apoyos,
    onChange: e => setApoyos(e.target.value),
    placeholder: "Material concreto, tableros visuales, mediaci\xF3n docente, adaptaciones curriculares...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalNuevo(false),
    className: "bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-xl font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "bg-amber-600 hover:bg-amber-700 text-white px-5 py-2 rounded-xl font-bold shadow transition"
  }, guardando ? 'Guardando...' : editandoId ? 'Guardar Cambios' : 'Registrar BAP'))))));
}

// =============================================================
// VISTA 6: ANEXO IV - HOJA DE SUGERENCIAS
// =============================================================
function Anexo4View({
  onBack,
  setMetrics
}) {
  const [sugerencias, setSugerencias] = React.useState([]);
  const [alumnosList, setAlumnosList] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [mostrarModal, setMostrarModal] = React.useState(false);
  const [editandoItem, setEditandoItem] = React.useState(null);
  const [guardando, setGuardando] = React.useState(false);

  // Form state
  const [formAlumnoId, setFormAlumnoId] = React.useState('');
  const [formArea, setFormArea] = React.useState('Aprendizaje');
  const [formMotivo, setFormMotivo] = React.useState('');
  const [formSugerencias, setFormSugerencias] = React.useState('');
  const [formFecha, setFormFecha] = React.useState(new Date().toISOString().slice(0, 10));
  const [formCumplimiento, setFormCumplimiento] = React.useState('En seguimiento');
  const cargarDatos = React.useCallback(async () => {
    setLoading(true);
    try {
      const [sugs, alus] = await Promise.all([apiRequest('/api/anexo4'), apiRequest('/api/alumnos')]);
      setSugerencias(sugs || []);
      setAlumnosList(alus || []);
      if (alus && alus.length > 0 && !formAlumnoId) {
        setFormAlumnoId(alus[0].id);
      }
    } catch (err) {
      console.error("Error cargando Anexo IV:", err);
    } finally {
      setLoading(false);
    }
  }, [formAlumnoId]);
  React.useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);
  const abrirNuevo = () => {
    setEditandoItem(null);
    setFormArea('Aprendizaje');
    setFormMotivo('');
    setFormSugerencias('');
    setFormFecha(new Date().toISOString().slice(0, 10));
    setFormCumplimiento('En seguimiento');
    setMostrarModal(true);
  };
  const abrirEditar = item => {
    setEditandoItem(item);
    setFormAlumnoId(item.id_alumno || item.ID_Alumno || '');
    setFormArea(item.area || item.Area || 'Aprendizaje');
    setFormMotivo(item.motivo || item.Motivo || '');
    setFormSugerencias(item.sugerencias || item.Sugerencias || '');
    setFormFecha(item.fecha_elaboracion || item.Fecha_Elaboracion || item.fecha || new Date().toISOString().slice(0, 10));
    setFormCumplimiento(item.nivel_cumplimiento_resultados || item.Nivel_Cumplimiento_Resultados || 'En seguimiento');
    setMostrarModal(true);
  };
  const guardarFormulario = async e => {
    e.preventDefault();
    if (!formSugerencias.trim()) {
      alert("Debes capturar las sugerencias pedag\u00f3gicas.");
      return;
    }
    setGuardando(true);
    try {
      const alu = alumnosList.find(a => a.id === formAlumnoId) || {};
      const payload = {
        id_alumno: formAlumnoId,
        nombre_alumno: alu.nombre_completo || formAlumnoId,
        escuela: alu.escuela || '',
        grado_grupo: `${alu.grado || ''}\u00b0 ${alu.grupo || ''}`,
        area: formArea,
        motivo: formMotivo,
        sugerencias: formSugerencias,
        fecha_elaboracion: formFecha,
        nivel_cumplimiento_resultados: formCumplimiento,
        ciclo_escolar: '2026-2027',
        trimestre: '1'
      };
      if (editandoItem) {
        const itemId = editandoItem.id || editandoItem.ID_Anexo4;
        await apiRequest(`/api/anexo4/${itemId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiRequest('/api/anexo4', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      setMostrarModal(false);
      await cargarDatos();
    } catch (err) {
      alert("Error guardando sugerencia: " + err.message);
    } finally {
      setGuardando(false);
    }
  };
  const anularItem = async item => {
    const itemId = item.id || item.ID_Anexo4;
    if (!confirm(`\u00bfDeseas anular l\u00f3gicamente esta hoja de sugerencias? (El registro se conservar\u00e1 en el historial administrativo)`)) {
      return;
    }
    try {
      await apiRequest(`/api/anexo4/${itemId}`, {
        method: 'DELETE'
      });
      await cargarDatos();
    } catch (err) {
      alert("Error anulando registro: " + err.message);
    }
  };
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
    className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition cursor-pointer"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo IV \u2014 Hojas de Sugerencias"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Orientaciones y ajustes razonables emitidos a los docentes de grupo regular"))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2.5"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtradas.length, " hojas"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: abrirNuevo,
    className: "px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center space-x-1.5 cursor-pointer"
  }, /*#__PURE__*/React.createElement("span", null, "+ Emitir Sugerencia")))), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, \xE1rea, escuela o contenido...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando hojas de sugerencias...") : filtradas.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay hojas de sugerencias registradas para este criterio o escuela asignada.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, filtradas.map((s, i) => {
    const itemId = s.id || s.ID_Anexo4 || s.id_alumno || s.ID_Alumno;
    const estaAnulada = s.estado === 'ANULADA' || s.Estado === 'ANULADA';
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      className: `p-4 bg-white rounded-xl border text-xs space-y-2 transition ${estaAnulada ? 'border-red-200 opacity-60 bg-red-50/20' : 'border-slate-200 hover:border-amber-400'}`
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center font-bold text-slate-900"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-sm"
    }, s.nombre_alumno || s.Nombre_Alumno || s.Alumno || 'Sugerencia Grupal'), estaAnulada && /*#__PURE__*/React.createElement("span", {
      className: "bg-red-100 text-red-700 text-[10px] px-2 py-0.5 rounded font-bold"
    }, "ANULADA")), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-slate-400 font-normal"
    }, s.fecha_elaboracion || s.Fecha_Elaboracion || s.fecha || s.Fecha), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => descargarArchivoAutenticado(`/api/anexo4/${itemId}/pdf`, `Anexo_IV_${itemId}.pdf`),
      className: "px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
      title: "Descargar Anexo IV Oficial PDF"
    }, "\uD83D\uDCC4 PDF"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => abrirEditar(s),
      className: "px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-bold text-[11px] transition cursor-pointer"
    }, "\u270F\uFE0F Editar"), !estaAnulada && /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => anularItem(s),
      className: "px-2 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded font-bold text-[11px] transition cursor-pointer",
      title: "Anular registro l\xF3gicamente"
    }, "\uD83D\uDDD1\uFE0F"))), /*#__PURE__*/React.createElement("div", {
      className: "text-slate-500"
    }, /*#__PURE__*/React.createElement("span", null, "\xC1rea: ", /*#__PURE__*/React.createElement("strong", {
      className: "text-amber-800"
    }, s.area || s.Area || 'Aprendizaje')), /*#__PURE__*/React.createElement("span", {
      className: "mx-2"
    }, "\u2022"), /*#__PURE__*/React.createElement("span", null, "Especialista: ", s.docente_especialista || s.Docente_Especialista || s.Especialista || 'USAER'), (s.escuela || s.Escuela) && /*#__PURE__*/React.createElement("span", null, " \u2022 Escuela: ", s.escuela || s.Escuela)), (s.motivo || s.Motivo) && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Motivo:"), " ", s.motivo || s.Motivo), /*#__PURE__*/React.createElement("div", {
      className: "text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-100 leading-relaxed"
    }, /*#__PURE__*/React.createElement("strong", null, "Sugerencias para el Docente Regular:"), /*#__PURE__*/React.createElement("br", null), s.sugerencias || s.Sugerencias), (s.nivel_cumplimiento_resultados || s.cumplimiento || s.Cumplimiento) && /*#__PURE__*/React.createElement("div", {
      className: "text-emerald-700 font-medium"
    }, /*#__PURE__*/React.createElement("strong", null, "Resultado / Seguimiento:"), " ", s.nivel_cumplimiento_resultados || s.cumplimiento || s.Cumplimiento));
  })), mostrarModal && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-base font-bold text-slate-900"
  }, editandoItem ? 'Editar Hoja de Sugerencias (Anexo IV)' : 'Emitir Nueva Hoja de Sugerencias (Anexo IV)'), /*#__PURE__*/React.createElement("button", {
    onClick: () => setMostrarModal(false),
    className: "text-slate-400 hover:text-slate-600 font-bold"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: guardarFormulario,
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Alumno / Alumna:"), /*#__PURE__*/React.createElement("select", {
    value: formAlumnoId,
    onChange: e => setFormAlumnoId(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  }, alumnosList.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre_completo, " (", a.grado, "\xB0", a.grupo, " - ", a.escuela, ")")))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-3"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "\xC1rea Emisora:"), /*#__PURE__*/React.createElement("select", {
    value: formArea,
    onChange: e => setFormArea(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  }, /*#__PURE__*/React.createElement("option", {
    value: "Aprendizaje"
  }, "Aprendizaje (Apoyo)"), /*#__PURE__*/React.createElement("option", {
    value: "Psicolog\xEDa"
  }, "Psicolog\xEDa"), /*#__PURE__*/React.createElement("option", {
    value: "Comunicaci\xF3n"
  }, "Comunicaci\xF3n"), /*#__PURE__*/React.createElement("option", {
    value: "Trabajo Social"
  }, "Trabajo Social"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Fecha de Elaboraci\xF3n:"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: formFecha,
    onChange: e => setFormFecha(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Motivo de la Sugerencia:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: formMotivo,
    onChange: e => setFormMotivo(e.target.value),
    placeholder: "ej. Ajustes en lectoescritura, conducta o participaci\xF3n \xE1ulica",
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Sugerencias y Ajustes para el Docente de Aula:"), /*#__PURE__*/React.createElement("textarea", {
    rows: "4",
    value: formSugerencias,
    onChange: e => setFormSugerencias(e.target.value),
    placeholder: "Redactar indicaciones claras, observables y funcionales para el maestro de grupo regular...",
    className: "w-full p-2.5 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 font-sans"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Nivel de Cumplimiento / Seguimiento:"), /*#__PURE__*/React.createElement("select", {
    value: formCumplimiento,
    onChange: e => setFormCumplimiento(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  }, /*#__PURE__*/React.createElement("option", {
    value: "En seguimiento"
  }, "En seguimiento"), /*#__PURE__*/React.createElement("option", {
    value: "Cumplido satisfactoriamente"
  }, "Cumplido satisfactoriamente"), /*#__PURE__*/React.createElement("option", {
    value: "En proceso con adecuaciones"
  }, "En proceso con adecuaciones"), /*#__PURE__*/React.createElement("option", {
    value: "Requiere acompa\xF1amiento directo"
  }, "Requiere acompa\xF1amiento directo"))), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setMostrarModal(false),
    className: "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "px-5 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg font-bold shadow"
  }, guardando ? 'Guardando...' : editandoItem ? 'Guardar Cambios' : 'Emitir Sugerencia'))))));
}

// =============================================================
// VISTA 7: ANEXO V - EVENTOS SIGNIFICATIVOS (408 REGISTROS)
// =============================================================
function Anexo5View({
  onBack,
  setMetrics
}) {
  const [eventos, setEventos] = React.useState([]);
  const [alumnosList, setAlumnosList] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [mostrarModal, setMostrarModal] = React.useState(false);
  const [editandoItem, setEditandoItem] = React.useState(null);
  const [guardando, setGuardando] = React.useState(false);

  // Form state
  const [formAlumnoId, setFormAlumnoId] = React.useState('');
  const [formFecha, setFormFecha] = React.useState(new Date().toISOString().slice(0, 10));
  const [formEvento, setFormEvento] = React.useState('');
  const cargarDatos = React.useCallback(async () => {
    setLoading(true);
    try {
      const [evs, alus] = await Promise.all([apiRequest('/api/anexo5'), apiRequest('/api/alumnos')]);
      setEventos(evs || []);
      setAlumnosList(alus || []);
      if (alus && alus.length > 0 && !formAlumnoId) {
        setFormAlumnoId(alus[0].id);
      }
    } catch (err) {
      console.error("Error cargando Anexo V:", err);
    } finally {
      setLoading(false);
    }
  }, [formAlumnoId]);
  React.useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);
  const abrirNuevo = () => {
    setEditandoItem(null);
    setFormFecha(new Date().toISOString().slice(0, 10));
    setFormEvento('');
    setMostrarModal(true);
  };
  const abrirEditar = item => {
    setEditandoItem(item);
    setFormAlumnoId(item.id_alumno || item.ID_Alumno || '');
    setFormFecha(item.fecha || item.Fecha || new Date().toISOString().slice(0, 10));
    setFormEvento(item.evento || item.Evento || '');
    setMostrarModal(true);
  };
  const guardarFormulario = async e => {
    e.preventDefault();
    if (!formEvento.trim()) {
      alert("Debes capturar la narrativa del evento significativo.");
      return;
    }
    setGuardando(true);
    try {
      const alu = alumnosList.find(a => a.id === formAlumnoId) || {};
      const payload = {
        id_alumno: formAlumnoId,
        nombre_alumno: alu.nombre_completo || formAlumnoId,
        escuela: alu.escuela || '',
        id_escuela: alu.id_escuela || '',
        grado_grupo: `${alu.grado || ''}\u00b0 ${alu.grupo || ''}`,
        fecha: formFecha,
        evento: formEvento
      };
      if (editandoItem) {
        const itemId = editandoItem.id || editandoItem.ID_Evento;
        await apiRequest(`/api/anexo5/${itemId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiRequest('/api/anexo5', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      setMostrarModal(false);
      await cargarDatos();
    } catch (err) {
      alert("Error guardando evento: " + err.message);
    } finally {
      setGuardando(false);
    }
  };
  const anularItem = async item => {
    const itemId = item.id || item.ID_Evento;
    if (!confirm(`\u00bfDeseas anular l\u00f3gicamente este evento significativo? (Se conservar\u00e1 en la bit\u00e1cora hist\u00f3rica)`)) {
      return;
    }
    try {
      await apiRequest(`/api/anexo5/${itemId}`, {
        method: 'DELETE'
      });
      await cargarDatos();
    } catch (err) {
      alert("Error anulando evento: " + err.message);
    }
  };
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
    className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition cursor-pointer"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo V \u2014 Eventos Significativos"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Bit\xE1cora institucional de incidencias, citatorios, crisis conductuales y avances relevantes"))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2.5"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " eventos hist\xF3ricos"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: abrirNuevo,
    className: "px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center space-x-1.5 cursor-pointer"
  }, /*#__PURE__*/React.createElement("span", null, "+ Registrar Evento")))), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, especialista, escuela o descripci\xF3n del evento...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "Cargando eventos significativos...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-xs"
  }, "No hay eventos significativos registrados bajo este criterio de b\xFAsqueda.") : /*#__PURE__*/React.createElement("div", {
    className: "grid gap-3"
  }, filtrados.map((ev, i) => {
    const itemId = ev.id || ev.ID_Evento;
    const estaAnulado = ev.estado === 'ANULADO' || ev.Estado === 'ANULADO';
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      className: `p-4 bg-white rounded-xl border text-xs space-y-2 transition ${estaAnulado ? 'border-red-200 opacity-60 bg-red-50/20' : 'border-slate-200 hover:border-amber-400'}`
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex justify-between items-center font-bold text-slate-900"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-sm"
    }, ev.nombre_alumno || ev.Nombre_Alumno || ev.alumno_nombre || 'Evento'), estaAnulado && /*#__PURE__*/React.createElement("span", {
      className: "bg-red-100 text-red-700 text-[10px] px-2 py-0.5 rounded font-bold"
    }, "ANULADO")), /*#__PURE__*/React.createElement("div", {
      className: "flex items-center space-x-2"
    }, /*#__PURE__*/React.createElement("span", {
      className: "text-slate-400 font-normal"
    }, ev.fecha || ev.Fecha), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => descargarArchivoAutenticado(`/api/anexo5/${itemId}/pdf`, `Anexo_V_${itemId}.pdf`),
      className: "px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 rounded font-bold text-[11px] transition cursor-pointer",
      title: "Descargar Anexo V Oficial PDF"
    }, "\uD83D\uDCC4 PDF"), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => abrirEditar(ev),
      className: "px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-bold text-[11px] transition cursor-pointer"
    }, "\u270F\uFE0F Editar"), !estaAnulado && /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => anularItem(ev),
      className: "px-2 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded font-bold text-[11px] transition cursor-pointer",
      title: "Anular evento l\xF3gicamente"
    }, "\uD83D\uDDD1\uFE0F"))), /*#__PURE__*/React.createElement("div", {
      className: "text-slate-500"
    }, /*#__PURE__*/React.createElement("span", null, "Docente / Especialista: ", /*#__PURE__*/React.createElement("strong", null, ev.especialista || ev.Especialista || 'USAER 2E')), (ev.escuela || ev.Escuela) && /*#__PURE__*/React.createElement("span", null, " \u2022 Escuela: ", ev.escuela || ev.Escuela), (ev.grado_grupo || ev.Grado_Grupo) && /*#__PURE__*/React.createElement("span", null, " \u2022 Grado: ", ev.grado_grupo || ev.Grado_Grupo)), /*#__PURE__*/React.createElement("div", {
      className: "text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-100 leading-relaxed font-sans"
    }, ev.evento || ev.Evento));
  })), mostrarModal && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex justify-between items-center border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-base font-bold text-slate-900"
  }, editandoItem ? 'Editar Evento Significativo (Anexo V)' : 'Registrar Nuevo Evento Significativo (Anexo V)'), /*#__PURE__*/React.createElement("button", {
    onClick: () => setMostrarModal(false),
    className: "text-slate-400 hover:text-slate-600 font-bold"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: guardarFormulario,
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Alumno / Alumna:"), /*#__PURE__*/React.createElement("select", {
    value: formAlumnoId,
    onChange: e => setFormAlumnoId(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  }, alumnosList.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre_completo, " (", a.grado, "\xB0", a.grupo, " - ", a.escuela, ")")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Fecha del Evento:"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: formFecha,
    onChange: e => setFormFecha(e.target.value),
    className: "w-full p-2 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Narrativa Detallada del Evento Significativo:"), /*#__PURE__*/React.createElement("textarea", {
    rows: "5",
    value: formEvento,
    onChange: e => setFormEvento(e.target.value),
    placeholder: "Describir los hechos acontecidos de manera objetiva, observable y precisa (conducta, entrevista con tutor, acuerdo escolar o citatorio)...",
    className: "w-full p-2.5 border border-slate-200 rounded-lg text-slate-800 focus:border-amber-500 font-sans"
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setMostrarModal(false),
    className: "px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "px-5 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg font-bold shadow"
  }, guardando ? 'Guardando...' : editandoItem ? 'Guardar Cambios' : 'Registrar Evento'))))));
}

// =============================================================
// VISTA 8: ANEXO VII - DERIVACI\u00d3N Y SEGUIMIENTO M\u00c9DICO
// =============================================================
function Anexo7View({
  user,
  onBack,
  setMetrics
}) {
  const [derivaciones, setDerivaciones] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    apiRequest('/api/anexo7').then(data => {
      setDerivaciones(data || []);
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
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Anexo VII \u2014 Hoja de Derivaci\xF3n Oficial"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Instrumento institucional oficial en papel para entregar al docente de grupo regular."))), /*#__PURE__*/React.createElement("div", {
    className: "bg-gradient-to-r from-amber-500 to-amber-600 rounded-2xl p-6 text-white shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "space-y-1"
  }, /*#__PURE__*/React.createElement("h2", {
    className: "text-lg font-bold"
  }, "\uD83D\uDCC4 Plantilla Oficial de Derivaci\xF3n (Docente Regular)"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-amber-100 max-w-xl leading-relaxed"
  }, "Conforme a la normativa de Educaci\xF3n Especial de Yucat\xE1n (SEGEY), la Hoja de Derivaci\xF3n debe entregarse en formato oficial al maestro de grupo regular para registrar antecedentes, indicadores de alerta y motivos de solicitud.")), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/anexo7/plantilla/pdf', 'Anexo_VII_Hoja_Derivacion_Docente_Regular.pdf'),
    className: "bg-white hover:bg-amber-50 text-amber-900 font-bold text-xs px-5 py-3 rounded-xl shadow-md transition whitespace-nowrap flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCE5 Descargar Formato PDF Oficial"))), /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-xs uppercase tracking-wider"
  }, "Derivaciones Recibidas e Historial"), /*#__PURE__*/React.createElement("span", {
    className: "text-xs text-slate-500"
  }, derivaciones.length, " registradas")), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 text-slate-500 text-xs"
  }, "Cargando derivaciones...") : derivaciones.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-12 text-slate-500 text-xs"
  }, "No hay derivaciones pendientes registradas. Descarga el formato superior para entregar al docente regular.") : /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-left text-xs"
  }, /*#__PURE__*/React.createElement("thead", {
    className: "bg-slate-50 text-slate-600 font-semibold border-b border-slate-100"
  }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "ID Derivaci\xF3n"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Alumno"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Escuela"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Docente que Deriva"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Fecha"), /*#__PURE__*/React.createElement("th", {
    className: "p-3 text-right"
  }, "Descargar"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, derivaciones.map(d => /*#__PURE__*/React.createElement("tr", {
    key: d.ID_Anexo7 || d.id,
    className: "hover:bg-slate-50/80"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-mono text-[11px] text-slate-500"
  }, d.ID_Anexo7 || d.id), /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-semibold text-slate-900"
  }, d.Nombre_Alumno || d.nombre_alumno || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, d.Escuela || d.escuela || 'USAER 02E'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, d.Docente_Regular || d.docente_regular || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-500"
  }, d.Fecha || d.fecha), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-right"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/anexo7/' + (d.ID_Anexo7 || d.id) + '/pdf', 'Derivacion_' + (d.ID_Anexo7 || d.id) + '.pdf'),
    className: "bg-amber-100 hover:bg-amber-200 text-amber-900 px-3 py-1 rounded-lg text-[11px] font-semibold"
  }, "PDF")))))))));
}

// =============================================================
// VISTA 9: HORARIOS DE APOYO
// =============================================================
function HorariosView({
  user,
  onBack,
  setMetrics
}) {
  const [horariosData, setHorariosData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [modalBloque, setModalBloque] = React.useState(false);
  const [dia, setDia] = React.useState('Lunes');
  const [inicio, setInicio] = React.useState('07:30');
  const [fin, setFin] = React.useState('08:15');
  const [grado, setGrado] = React.useState('1');
  const [grupo, setGrupo] = React.useState('A');
  const [modalidad, setModalidad] = React.useState('Aula Regular');
  const [espacio, setEspacio] = React.useState('Sal\u00f3n de Clase');
  const [proposito, setProposito] = React.useState('');
  const [guardando, setGuardando] = React.useState(false);
  const cargar = () => {
    setLoading(true);
    apiRequest('/api/horarios').then(data => {
      setHorariosData(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  React.useEffect(() => {
    cargar();
  }, []);
  const sesiones = (horariosData === null || horariosData === void 0 ? void 0 : horariosData.sesiones) || [{
    Dia: 'Lunes',
    Inicio: '07:30',
    Fin: '08:15',
    Grado: '1',
    Grupo: 'A',
    Modalidad: 'Aula Regular',
    Espacio: 'Sal\u00f3n 1A',
    Proposito: 'Atenci\u00f3n pedag\u00f3gica inicial'
  }, {
    Dia: 'Lunes',
    Inicio: '08:15',
    Fin: '09:00',
    Grado: '2',
    Grupo: 'A',
    Modalidad: 'Subgrupo',
    Espacio: 'Aula Apoyo',
    Proposito: 'Fortalecimiento de lectoescritura'
  }, {
    Dia: 'Mi\u00e9rcoles',
    Inicio: '09:30',
    Fin: '10:15',
    Grado: '3',
    Grupo: 'B',
    Modalidad: 'Aula Regular',
    Espacio: 'Sal\u00f3n 3B',
    Proposito: 'Ajustes razonables y DUA'
  }, {
    Dia: 'Viernes',
    Inicio: '10:30',
    Fin: '11:15',
    Grado: '1',
    Grupo: 'A',
    Modalidad: 'Individual',
    Espacio: 'Aula Apoyo',
    Proposito: 'Seguimiento espec\u00edfico'
  }];
  const diasSemana = ['Lunes', 'Martes', 'Mi\u00e9rcoles', 'Jueves', 'Viernes'];
  const handleGuardarBloque = async e => {
    e.preventDefault();
    setGuardando(true);
    const nuevaSesion = {
      Dia: dia,
      Inicio: inicio,
      Fin: fin,
      Grado: grado,
      Grupo: grupo,
      Modalidad: modalidad,
      Espacio: espacio,
      Proposito: proposito
    };
    const nuevoLista = [...sesiones, nuevaSesion];
    try {
      var _user$escuelas_permit2;
      await apiRequest('/api/horarios', {
        method: 'POST',
        body: JSON.stringify({
          sesiones: nuevoLista,
          escuela: (user === null || user === void 0 || (_user$escuelas_permit2 = user.escuelas_permitidas) === null || _user$escuelas_permit2 === void 0 ? void 0 : _user$escuelas_permit2[0]) || 'USAER 02E'
        })
      });
      setModalBloque(false);
      cargar();
    } catch (err) {
      alert('Error al guardar bloque de horario: ' + err.message);
    } finally {
      setGuardando(false);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Horario Semanal de Atenci\xF3n de Apoyo"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Distribuci\xF3n de bloques de acompa\xF1amiento pedag\xF3gico, asesor\xEDa y atenci\xF3n en aula."))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalBloque(true),
    className: "text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold px-4 py-2 rounded-xl shadow transition"
  }, "+ Agregar Bloque"), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/horarios/pdf', 'Horario_Semanal_' + ((user === null || user === void 0 ? void 0 : user.usuario) || 'apoyo') + '.pdf'),
    className: "text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold px-4 py-2 rounded-xl shadow transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCE5 Descargar PDF Oficial")))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-5 gap-3"
  }, diasSemana.map(d => {
    const deDia = sesiones.filter(s => s.Dia === d);
    return /*#__PURE__*/React.createElement("div", {
      key: d,
      className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm flex flex-col"
    }, /*#__PURE__*/React.createElement("div", {
      className: "bg-slate-800 text-amber-400 font-bold text-center py-2 text-xs uppercase tracking-wider"
    }, d), /*#__PURE__*/React.createElement("div", {
      className: "p-2 space-y-2 flex-1"
    }, deDia.length === 0 ? /*#__PURE__*/React.createElement("div", {
      className: "text-center py-8 text-slate-400 text-[11px]"
    }, "Sin bloques") : deDia.map((s, idx) => /*#__PURE__*/React.createElement("div", {
      key: idx,
      className: "bg-slate-50 border border-slate-200 rounded-xl p-2.5 space-y-1 hover:border-amber-400 transition"
    }, /*#__PURE__*/React.createElement("div", {
      className: "flex items-center justify-between text-[11px]"
    }, /*#__PURE__*/React.createElement("span", {
      className: "font-mono font-bold text-amber-800"
    }, s.Inicio, " - ", s.Fin), /*#__PURE__*/React.createElement("span", {
      className: "bg-amber-100 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold"
    }, s.Grado, "\xB0", s.Grupo)), /*#__PURE__*/React.createElement("div", {
      className: "font-semibold text-slate-800 text-xs"
    }, s.Modalidad), /*#__PURE__*/React.createElement("div", {
      className: "text-[11px] text-slate-500 leading-tight"
    }, s.Proposito)))));
  })), modalBloque && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-sm"
  }, "Agregar Bloque de Atenci\xF3n"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalBloque(false),
    className: "text-slate-400 hover:text-slate-600 font-bold"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleGuardarBloque,
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "D\xEDa:"), /*#__PURE__*/React.createElement("select", {
    value: dia,
    onChange: e => setDia(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200"
  }, diasSemana.map(d => /*#__PURE__*/React.createElement("option", {
    key: d,
    value: d
  }, d)))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Modalidad:"), /*#__PURE__*/React.createElement("select", {
    value: modalidad,
    onChange: e => setModalidad(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200"
  }, /*#__PURE__*/React.createElement("option", {
    value: "Aula Regular"
  }, "Aula Regular"), /*#__PURE__*/React.createElement("option", {
    value: "Subgrupo"
  }, "Subgrupo"), /*#__PURE__*/React.createElement("option", {
    value: "Individual"
  }, "Individual"), /*#__PURE__*/React.createElement("option", {
    value: "Asesor\xEDa Docente"
  }, "Asesor\xEDa Docente")))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Hora Inicio:"), /*#__PURE__*/React.createElement("input", {
    type: "time",
    value: inicio,
    onChange: e => setInicio(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Hora Fin:"), /*#__PURE__*/React.createElement("input", {
    type: "time",
    value: fin,
    onChange: e => setFin(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  }))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 gap-2"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Grado:"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    min: "1",
    max: "6",
    value: grado,
    onChange: e => setGrado(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Grupo:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    maxLength: "2",
    value: grupo,
    onChange: e => setGrupo(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200 uppercase",
    required: true
  }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Prop\xF3sito / Actividad:"), /*#__PURE__*/React.createElement("textarea", {
    value: proposito,
    onChange: e => setProposito(e.target.value),
    placeholder: "Ej. Acompa\xF1amiento DUA en lectoescritura...",
    rows: 2,
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalBloque(false),
    className: "bg-slate-100 text-slate-700 px-4 py-2 rounded-xl font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "bg-amber-600 hover:bg-amber-700 text-white px-5 py-2 rounded-xl font-bold"
  }, guardando ? 'Guardando...' : 'Agregar Bloque'))))));
}

// =============================================================
// VISTA 10: CRONOGRAMA MENSUAL
// =============================================================
function CronogramasView({
  user,
  onBack,
  setMetrics
}) {
  var _user$escuelas_permit3, _user$escuelas_permit4, _user$escuelas_permit5;
  const [cronogramas, setCronogramas] = React.useState(null);
  const [mes, setMes] = React.useState('Noviembre 2026');
  const [modalAct, setModalAct] = React.useState(false);
  const [fecha, setFecha] = React.useState(new Date().toISOString().split('T')[0]);
  const [escuela, setEscuela] = React.useState((user === null || user === void 0 || (_user$escuelas_permit3 = user.escuelas_permitidas) === null || _user$escuelas_permit3 === void 0 ? void 0 : _user$escuelas_permit3[0]) || 'Escuela Adscrita');
  const [actividad, setActividad] = React.useState('');
  const [objetivo, setObjetivo] = React.useState('');
  const [guardando, setGuardando] = React.useState(false);
  const meses = ['Agosto 2026', 'Septiembre 2026', 'Octubre 2026', 'Noviembre 2026', 'Diciembre 2026', 'Enero 2027', 'Febrero 2027', 'Marzo 2027', 'Abril 2027', 'Mayo 2027', 'Junio 2027', 'Julio 2027'];
  const cargar = () => {
    apiRequest('/api/cronogramas').then(setCronogramas);
  };
  React.useEffect(() => {
    cargar();
  }, []);
  const actividades = (cronogramas === null || cronogramas === void 0 ? void 0 : cronogramas.actividades) || [{
    Fecha: '2026-11-03',
    Escuela: (user === null || user === void 0 || (_user$escuelas_permit4 = user.escuelas_permitidas) === null || _user$escuelas_permit4 === void 0 ? void 0 : _user$escuelas_permit4[0]) || 'Escuela Asignada',
    Actividad: 'Observaci\u00f3n \u00e1ulica y asesor\u00eda a docente regular',
    Objetivo: 'Identificaci\u00f3n de BAP'
  }, {
    Fecha: '2026-11-10',
    Escuela: (user === null || user === void 0 || (_user$escuelas_permit5 = user.escuelas_permitidas) === null || _user$escuelas_permit5 === void 0 ? void 0 : _user$escuelas_permit5[0]) || 'Escuela Asignada',
    Actividad: 'Evaluaci\u00f3n Psicopedag\u00f3gica inicial y entrevistas',
    Objetivo: 'Construcci\u00f3n de expediente'
  }, {
    Fecha: '2026-11-27',
    Escuela: 'Sede USAER',
    Actividad: 'Consejo T\u00e9cnico Escolar (CTE)',
    Objetivo: 'Evaluaci\u00f3n interdisciplinaria'
  }];
  const handleGuardarActividad = async e => {
    e.preventDefault();
    setGuardando(true);
    const nueva = {
      Fecha: fecha,
      Escuela: escuela,
      Actividad: actividad,
      Objetivo: objetivo
    };
    try {
      await apiRequest('/api/cronogramas', {
        method: 'POST',
        body: JSON.stringify({
          actividades: [...actividades, nueva],
          mes
        })
      });
      setModalAct(false);
      cargar();
    } catch (err) {
      alert('Error al guardar actividad: ' + err.message);
    } finally {
      setGuardando(false);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Cronograma Mensual de Especialistas"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Programaci\xF3n de visitas, evaluaciones y asesor\xEDas del equipo de apoyo."))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("select", {
    value: mes,
    onChange: e => setMes(e.target.value),
    className: "text-xs font-bold p-2 rounded-xl border border-slate-200 bg-white"
  }, meses.map(m => /*#__PURE__*/React.createElement("option", {
    key: m,
    value: m
  }, m))), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalAct(true),
    className: "text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold px-3 py-2 rounded-xl shadow transition"
  }, "+ Registrar Visita"), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/cronogramas/pdf?mes=' + encodeURIComponent(mes), 'Cronograma_' + ((user === null || user === void 0 ? void 0 : user.usuario) || 'especialista') + '_' + mes.replace(' ', '_') + '.pdf'),
    className: "text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold px-4 py-2 rounded-xl shadow transition"
  }, "\uD83D\uDCE5 PDF Oficial"))), /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-800 text-xs uppercase tracking-wider"
  }, "Actividades Programadas \u2014 ", mes), /*#__PURE__*/React.createElement("span", {
    className: "text-xs text-slate-500"
  }, actividades.length, " actividades")), /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-left text-xs"
  }, /*#__PURE__*/React.createElement("thead", {
    className: "bg-slate-50 text-slate-600 font-semibold border-b border-slate-100"
  }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Fecha"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Escuela / Sede"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Actividad"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Objetivo Pedag\xF3gico"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, actividades.map((a, idx) => /*#__PURE__*/React.createElement("tr", {
    key: idx,
    className: "hover:bg-slate-50/80 transition"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-mono font-bold text-amber-800 whitespace-nowrap"
  }, a.Fecha), /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-semibold text-slate-900"
  }, a.Escuela), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-700"
  }, a.Actividad), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-500"
  }, a.Objetivo))))))), modalAct && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-sm"
  }, "Registrar Actividad / Visita"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalAct(false),
    className: "text-slate-400 hover:text-slate-600 font-bold"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleGuardarActividad,
    className: "space-y-3 text-xs"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Fecha:"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: fecha,
    onChange: e => setFecha(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Escuela / Sede:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: escuela,
    onChange: e => setEscuela(e.target.value),
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Actividad:"), /*#__PURE__*/React.createElement("input", {
    type: "text",
    value: actividad,
    onChange: e => setActividad(e.target.value),
    placeholder: "Ej. Observaci\xF3n en aula y aplicaci\xF3n de EPP...",
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Objetivo:"), /*#__PURE__*/React.createElement("textarea", {
    value: objetivo,
    onChange: e => setObjetivo(e.target.value),
    rows: 2,
    placeholder: "Prop\xF3sito pedag\xF3gico...",
    className: "w-full p-2 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalAct(false),
    className: "bg-slate-100 text-slate-700 px-4 py-2 rounded-xl font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "bg-amber-600 hover:bg-amber-700 text-white px-5 py-2 rounded-xl font-bold"
  }, guardando ? 'Guardando...' : 'Guardar'))))));
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
  }, ev.tipo || 'Actividad Institucional', " \u2022 ", ev.responsable || 'Direcci\u00f3n / Zona')), /*#__PURE__*/React.createElement("span", {
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
// VISTA 13: NOVEDADES DE SUPERVISI\u00d3N (111 DOCUMENTOS ZONA 001)
// =============================================================
function NovedadesView({
  user,
  onBack,
  setMetrics
}) {
  const [novedades, setNovedades] = React.useState([]);
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const esDirector = (user === null || user === void 0 ? void 0 : user.director) || (user === null || user === void 0 ? void 0 : user.rol) === 'DIRECTOR';
  React.useEffect(() => {
    if (!esDirector) {
      setLoading(false);
      return;
    }
    apiRequest('/api/novedades').then(data => {
      setNovedades(data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [esDirector]);
  if (!esDirector) {
    return /*#__PURE__*/React.createElement("div", {
      className: "p-8 max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 text-center space-y-4 my-12 shadow-sm"
    }, /*#__PURE__*/React.createElement("div", {
      className: "text-4xl text-amber-500"
    }, "\uD83D\uDD12"), /*#__PURE__*/React.createElement("h2", {
      className: "text-lg font-bold text-slate-800"
    }, "M\xF3dulo Exclusivo de Direcci\xF3n"), /*#__PURE__*/React.createElement("p", {
      className: "text-xs text-slate-500 leading-relaxed"
    }, "El apartado de Novedades de Supervisi\xF3n y gesti\xF3n con ATP es reservado exclusivamente para la Direcci\xF3n de USAER 2E por pol\xEDtica institucional."), /*#__PURE__*/React.createElement("button", {
      onClick: onBack,
      className: "text-xs bg-slate-800 text-amber-300 font-bold px-4 py-2 rounded-xl"
    }, "\u2190 Regresar al Panel Principal"));
  }
  const filtradas = novedades.filter(n => {
    const tit = (n.Nombre || n.nombre || n.Titulo || '').toLowerCase();
    const sec = (n.Seccion || n.seccion || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return tit.includes(q) || sec.includes(q);
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
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Novedades de Supervisi\xF3n \u2014 Zona 001"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Documentos, circulares y orientaciones oficiales de la ATP y Supervisi\xF3n Escolar."))), /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtradas.length, " documentos")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por t\xEDtulo o secci\xF3n...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Consultando novedades de supervisi\xF3n...") : /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 gap-4"
  }, filtradas.map((doc, idx) => /*#__PURE__*/React.createElement("div", {
    key: idx,
    className: "bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2 hover:border-amber-400 transition"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded"
  }, doc.Seccion || doc.seccion || 'General'), /*#__PURE__*/React.createElement("span", {
    className: "text-[10px] text-slate-400 font-mono"
  }, doc.Modificado_En || doc.fecha)), /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-sm"
  }, doc.Nombre || doc.nombre || 'Documento de Supervisi\u00f3n'), doc.Extracto && /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-100 leading-relaxed"
  }, doc.Extracto), doc.Enlace && /*#__PURE__*/React.createElement("a", {
    href: doc.Enlace,
    target: "_blank",
    rel: "noopener noreferrer",
    className: "inline-block text-xs text-amber-700 font-bold hover:underline"
  }, "\uD83D\uDD17 Abrir Documento Original en Drive \u2192")))));
}

// =============================================================
// VISTA 14: JUNTAS ACAD\u00c9MICAS Y RELATOR\u00cdAS
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
// VISTA 16: TR\u00c1MITES
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
  user,
  onBack,
  setMetrics
}) {
  const [informes, setInformes] = React.useState([]);
  const [alumnos, setAlumnos] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [busqueda, setBusqueda] = React.useState('');
  const [modalNuevo, setModalNuevo] = React.useState(false);
  const [guardando, setGuardando] = React.useState(false);

  // Form state
  const [alumnoId, setAlumnoId] = React.useState('');
  const [tipoInforme, setTipoInforme] = React.useState('Informe de Seguimiento Pedag\u00f3gico');
  const [periodo, setPeriodo] = React.useState('1er Trimestre 2026-2027');
  const [avances, setAvances] = React.useState('');
  const [barrerasAtendidas, setBarrerasAtendidas] = React.useState('');
  const [acuerdosFamilia, setAcuerdosFamilia] = React.useState('');
  const [recomendacionesAula, setRecomendacionesAula] = React.useState('');
  const cargarInformes = () => {
    setLoading(true);
    Promise.all([apiRequest('/api/informes'), apiRequest('/api/alumnos')]).then(([dataInf, dataAlu]) => {
      setInformes(dataInf || []);
      setAlumnos(dataAlu || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  React.useEffect(() => {
    cargarInformes();
  }, []);
  const abrirModalNuevo = () => {
    var _alumnos$2;
    setAlumnoId(((_alumnos$2 = alumnos[0]) === null || _alumnos$2 === void 0 ? void 0 : _alumnos$2.id) || '');
    setTipoInforme('Informe de Seguimiento Pedag\u00f3gico');
    setPeriodo('1er Trimestre 2026-2027');
    setAvances('');
    setBarrerasAtendidas('');
    setAcuerdosFamilia('');
    setRecomendacionesAula('');
    setModalNuevo(true);
  };
  const handleGuardar = async e => {
    var _user$escuelas_permit6;
    e.preventDefault();
    setGuardando(true);
    const selAlu = alumnos.find(a => a.id === alumnoId);
    const payload = {
      id_alumno: alumnoId,
      nombre_alumno: (selAlu === null || selAlu === void 0 ? void 0 : selAlu.nombre_completo) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.Nombre) || alumnoId,
      escuela: (selAlu === null || selAlu === void 0 ? void 0 : selAlu.nombre_escuela) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.Nombre_Escuela) || (user === null || user === void 0 || (_user$escuelas_permit6 = user.escuelas_permitidas) === null || _user$escuelas_permit6 === void 0 ? void 0 : _user$escuelas_permit6[0]) || 'USAER 02E',
      grado_grupo: ((selAlu === null || selAlu === void 0 ? void 0 : selAlu.Grado) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.grado) || '1') + '\u00b0' + ((selAlu === null || selAlu === void 0 ? void 0 : selAlu.Grupo) || (selAlu === null || selAlu === void 0 ? void 0 : selAlu.grupo) || 'A'),
      periodo,
      tipo_informe: tipoInforme,
      avances,
      barreras_atendidas: barrerasAtendidas,
      acuerdos_familia: acuerdosFamilia,
      recomendaciones_aula: recomendacionesAula,
      fecha: new Date().toISOString().split('T')[0]
    };
    try {
      await apiRequest('/api/informes', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setModalNuevo(false);
      cargarInformes();
    } catch (err) {
      alert('Error al guardar informe: ' + err.message);
    } finally {
      setGuardando(false);
    }
  };
  const filtrados = informes.filter(inf => {
    const nom = (inf.nombre_alumno || '').toLowerCase();
    const esc = (inf.escuela || '').toLowerCase();
    const tip = (inf.tipo_informe || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q) || tip.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Informes Pedag\xF3gicos y Administrativos"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Expedici\xF3n de informes oficiales de seguimiento, trimestrales y de evaluaci\xF3n pedag\xF3gica."))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-xs bg-amber-50 text-amber-800 font-bold px-3 py-1 rounded-full border border-amber-200"
  }, filtrados.length, " informes"), /*#__PURE__*/React.createElement("button", {
    onClick: abrirModalNuevo,
    className: "text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold px-4 py-2 rounded-xl shadow transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "+ Elaborar Informe")))), /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por alumno, escuela o tipo de informe...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), loading ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 text-slate-500 text-sm"
  }, "Cargando informes...") : filtrados.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "text-center py-16 bg-white rounded-2xl border border-slate-200 p-8"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-3xl mb-2"
  }, "\uD83D\uDCC4"), /*#__PURE__*/React.createElement("h3", {
    className: "text-sm font-bold text-slate-700"
  }, "Sin informes registrados"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500 mt-1"
  }, "Presiona \"+ Elaborar Informe\" para redactar un informe pedag\xF3gico con precarga de datos.")) : /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-left text-xs"
  }, /*#__PURE__*/React.createElement("thead", {
    className: "bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider"
  }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Alumno"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Escuela / Grado"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Tipo de Informe"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Periodo"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Fecha"), /*#__PURE__*/React.createElement("th", {
    className: "p-3 text-right"
  }, "Descargar"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, filtrados.map(inf => /*#__PURE__*/React.createElement("tr", {
    key: inf.id,
    className: "hover:bg-slate-50/80 transition"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-semibold text-slate-900"
  }, inf.nombre_alumno || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, inf.escuela || 'USAER 02E', " \xB7 ", inf.grado_grupo || ''), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-amber-800 font-medium"
  }, inf.tipo_informe), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, inf.periodo), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-500"
  }, inf.fecha), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-right"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/informes/' + inf.id + '/pdf', 'Informe_' + inf.id + '.pdf'),
    className: "bg-amber-100 hover:bg-amber-200 text-amber-900 px-3 py-1 rounded-lg text-[11px] font-semibold transition"
  }, "\uD83D\uDCC4 PDF Oficial")))))))), modalNuevo && /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center justify-between border-b border-slate-100 pb-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-base"
  }, "Elaborar Nuevo Informe"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setModalNuevo(false),
    className: "text-slate-400 hover:text-slate-600 font-bold text-sm"
  }, "\u2715")), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleGuardar,
    className: "space-y-4 text-xs"
  }, /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 sm:grid-cols-3 gap-3"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sm:col-span-2"
  }, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Alumno Autorizado:"), /*#__PURE__*/React.createElement("select", {
    value: alumnoId,
    onChange: e => setAlumnoId(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white",
    required: true
  }, alumnos.map(a => /*#__PURE__*/React.createElement("option", {
    key: a.id,
    value: a.id
  }, a.nombre_completo || a.Nombre, " \u2014 ", a.nombre_escuela || a.Nombre_Escuela, " (", a.Grado || a.grado, "\xB0", a.Grupo || a.grupo, ")")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Periodo:"), /*#__PURE__*/React.createElement("select", {
    value: periodo,
    onChange: e => setPeriodo(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white"
  }, /*#__PURE__*/React.createElement("option", {
    value: "1er Trimestre 2026-2027"
  }, "1er Trimestre 2026-2027"), /*#__PURE__*/React.createElement("option", {
    value: "2do Trimestre 2026-2027"
  }, "2do Trimestre 2026-2027"), /*#__PURE__*/React.createElement("option", {
    value: "3er Trimestre 2026-2027"
  }, "3er Trimestre 2026-2027"), /*#__PURE__*/React.createElement("option", {
    value: "Final Ciclo Escolar 2026-2027"
  }, "Final Ciclo Escolar 2026-2027")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "Tipo de Informe:"), /*#__PURE__*/React.createElement("select", {
    value: tipoInforme,
    onChange: e => setTipoInforme(e.target.value),
    className: "w-full p-2.5 rounded-xl border border-slate-200 bg-white"
  }, /*#__PURE__*/React.createElement("option", {
    value: "Informe de Seguimiento Pedag\xF3gico"
  }, "Informe de Seguimiento Pedag\xF3gico"), /*#__PURE__*/React.createElement("option", {
    value: "Informe de Evaluaci\xF3n Psicopedag\xF3gica"
  }, "Informe de Evaluaci\xF3n Psicopedag\xF3gica"), /*#__PURE__*/React.createElement("option", {
    value: "Informe Trimestral de Aprendizaje"
  }, "Informe Trimestral de Aprendizaje"), /*#__PURE__*/React.createElement("option", {
    value: "Informe de Ajustes Razonables"
  }, "Informe de Ajustes Razonables"), /*#__PURE__*/React.createElement("option", {
    value: "Informe Administrativo de Zona"
  }, "Informe Administrativo de Zona"))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "1. Avances Pedag\xF3gicos y Logros Observados:"), /*#__PURE__*/React.createElement("textarea", {
    value: avances,
    onChange: e => setAvances(e.target.value),
    placeholder: "Describir conductas observables, habilidades consolidadas y fortalezas identificadas...",
    rows: 2,
    className: "w-full p-2.5 rounded-xl border border-slate-200",
    required: true
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "2. Barreras Atendidas y Estrategias Implementadas:"), /*#__PURE__*/React.createElement("textarea", {
    value: barrerasAtendidas,
    onChange: e => setBarrerasAtendidas(e.target.value),
    placeholder: "Ajustes DUA aplicados en el aula regular, materiales espec\xEDficos, apoyos sensoriales...",
    rows: 2,
    className: "w-full p-2.5 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "3. Acuerdos y Vinculaci\xF3n con la Familia:"), /*#__PURE__*/React.createElement("textarea", {
    value: acuerdosFamilia,
    onChange: e => setAcuerdosFamilia(e.target.value),
    placeholder: "Compromisos de acompa\xF1amiento en el hogar, asistencia, seguimiento m\xE9dico/terap\xE9utico...",
    rows: 2,
    className: "w-full p-2.5 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
    className: "font-bold text-slate-700 block mb-1"
  }, "4. Recomendaciones para el Docente Regular y Aula:"), /*#__PURE__*/React.createElement("textarea", {
    value: recomendacionesAula,
    onChange: e => setRecomendacionesAula(e.target.value),
    placeholder: "Orientaciones pr\xE1cticas para la intervenci\xF3n en el grupo regular...",
    rows: 2,
    className: "w-full p-2.5 rounded-xl border border-slate-200"
  })), /*#__PURE__*/React.createElement("div", {
    className: "flex justify-end space-x-2 pt-2 border-t border-slate-100"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setModalNuevo(false),
    className: "bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-xl font-semibold"
  }, "Cancelar"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    disabled: guardando,
    className: "bg-amber-600 hover:bg-amber-700 text-white px-5 py-2 rounded-xl font-bold shadow transition"
  }, guardando ? 'Guardando...' : 'Guardar y Expedir Informe'))))));
}

// =============================================================
// VISTA 18: ACTAS DE VISITA Y OFICIOS DE COMISI\u00d3N
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
// VISTA 19: ESTAD\u00cdSTICAS INSTITUCIONALES DE ZONA
// =============================================================
function EstadisticasView({
  user,
  onBack,
  setMetrics
}) {
  const [stats, setStats] = React.useState(null);
  const [alumnos, setAlumnos] = React.useState([]);
  const [vista, setVista] = React.useState('nominal'); // 'nominal' | 'graficas'
  const [busqueda, setBusqueda] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    const t0 = performance.now();
    Promise.all([apiRequest('/api/estadisticas/zona'), apiRequest('/api/alumnos')]).then(([dataStats, dataAlu]) => {
      setStats(dataStats);
      setAlumnos(dataAlu || []);
      setLoading(false);
      const t1 = performance.now();
      setMetrics(m => ({
        latency: Math.round(t1 - t0),
        requests: m.requests + 2
      }));
    }).catch(() => setLoading(false));
  }, [setMetrics]);
  if (loading) {
    return /*#__PURE__*/React.createElement("div", {
      className: "text-center py-16 text-slate-500 text-sm"
    }, "Calculando indicadores descriptivos y listado nominal...");
  }
  const filtrados = alumnos.filter(a => {
    const nom = (a.nombre_completo || a.Nombre || '').toLowerCase();
    const esc = (a.nombre_escuela || a.Nombre_Escuela || '').toLowerCase();
    const cur = (a.curp || a.CURP || '').toLowerCase();
    const cond = (a.condicion_discapacidad || a.Condici\u00f3n || '').toLowerCase();
    const q = busqueda.toLowerCase();
    return nom.includes(q) || esc.includes(q) || cur.includes(q) || cond.includes(q);
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-3"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    className: "text-xs bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg text-slate-700 font-semibold transition"
  }, "\u2190 Volver"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    className: "text-2xl font-bold tracking-tight text-slate-900"
  }, "Estad\xEDsticas y Padr\xF3n Nominal"), /*#__PURE__*/React.createElement("p", {
    className: "text-xs text-slate-500"
  }, "Matr\xEDcula autorizada por rol, indicadores de atenci\xF3n y listado de alumnos adscritos."))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-slate-100 p-1 rounded-xl flex items-center space-x-1 text-xs font-bold"
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setVista('nominal'),
    className: `px-3 py-1.5 rounded-lg transition ${vista === 'nominal' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`
  }, "\uD83D\uDCCB Listado Nominal (", filtrados.length, ")"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setVista('graficas'),
    className: `px-3 py-1.5 rounded-lg transition ${vista === 'graficas' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`
  }, "\uD83D\uDCCA Indicadores Gr\xE1ficos")), /*#__PURE__*/React.createElement("button", {
    onClick: () => descargarArchivoAutenticado('/api/alumnos/exportar', 'Padron_Oficial_USAER_02E.xlsx'),
    className: "text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2 rounded-xl shadow transition flex items-center space-x-1"
  }, /*#__PURE__*/React.createElement("span", null, "\uD83D\uDCE5 Exportar Excel XLSX")))), vista === 'nominal' ? /*#__PURE__*/React.createElement("div", {
    className: "space-y-4"
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    placeholder: "Buscar por nombre, escuela, CURP o condici\xF3n...",
    value: busqueda,
    onChange: e => setBusqueda(e.target.value),
    className: "w-full text-xs p-3 rounded-xl border border-slate-200 bg-white shadow-sm"
  }), /*#__PURE__*/React.createElement("div", {
    className: "bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "overflow-x-auto"
  }, /*#__PURE__*/React.createElement("table", {
    className: "w-full text-left text-xs"
  }, /*#__PURE__*/React.createElement("thead", {
    className: "bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px] tracking-wider"
  }, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "ID"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Nombre del Alumno"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Escuela Primaria"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Grado/Grupo"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Sexo"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Edad (1 Sep)"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Condici\xF3n / Discapacidad"), /*#__PURE__*/React.createElement("th", {
    className: "p-3"
  }, "Docente de Apoyo"))), /*#__PURE__*/React.createElement("tbody", {
    className: "divide-y divide-slate-100"
  }, filtrados.map(a => /*#__PURE__*/React.createElement("tr", {
    key: a.id,
    className: "hover:bg-slate-50/80 transition"
  }, /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-mono text-slate-500 font-bold"
  }, a.id), /*#__PURE__*/React.createElement("td", {
    className: "p-3 font-semibold text-slate-900"
  }, a.nombre_completo || a.Nombre), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, a.nombre_escuela || a.Nombre_Escuela), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-700 font-bold"
  }, a.Grado || a.grado, "\xB0", a.Grupo || a.grupo), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, a.Sexo || a.sexo), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, a.Edad_1_Septiembre || a.edad_1_septiembre || '\u2014'), /*#__PURE__*/React.createElement("td", {
    className: "p-3"
  }, /*#__PURE__*/React.createElement("span", {
    className: "bg-amber-50 text-amber-800 border border-amber-200 font-semibold px-2 py-0.5 rounded text-[10px]"
  }, a.condicion_discapacidad || a.Condici\u00f3n || 'Sin dato')), /*#__PURE__*/React.createElement("td", {
    className: "p-3 text-slate-600"
  }, a.maestra_apoyo || a['Maestra de Apoyo'] || '\u2014')))))))) : /*#__PURE__*/React.createElement("div", {
    className: "space-y-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 sm:grid-cols-4 gap-4"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 font-medium"
  }, "Matr\xEDcula Activa"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-slate-900 mt-1"
  }, (stats === null || stats === void 0 ? void 0 : stats.alumnos_activos) || alumnos.length)), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 font-medium"
  }, "Escuelas Primarias"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-slate-900 mt-1"
  }, (stats === null || stats === void 0 ? void 0 : stats.total_escuelas) || 8)), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 font-medium"
  }, "Planeaciones Registradas"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-amber-700 mt-1"
  }, (stats === null || stats === void 0 ? void 0 : stats.planeaciones_registradas) || 0)), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-4 rounded-2xl border border-slate-200 shadow-sm"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-xs text-slate-500 font-medium"
  }, "Eventos Significativos"), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl font-black text-amber-700 mt-1"
  }, (stats === null || stats === void 0 ? void 0 : stats.anexo5_eventos_registrados) || 0))), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-2 gap-6"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-sm"
  }, "Distribuci\xF3n por Escuela"), /*#__PURE__*/React.createElement("div", {
    className: "space-y-2"
  }, Object.entries((stats === null || stats === void 0 ? void 0 : stats.distribucion_escuela) || {}).map(([esc, cnt]) => /*#__PURE__*/React.createElement("div", {
    key: esc,
    className: "flex items-center justify-between text-xs"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-700"
  }, esc), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("div", {
    className: "w-24 bg-slate-100 rounded-full h-2 overflow-hidden"
  }, /*#__PURE__*/React.createElement("div", {
    className: "bg-amber-500 h-full",
    style: {
      width: `${Math.min(100, cnt / 81 * 100)}%`
    }
  })), /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-900 w-8 text-right"
  }, cnt)))))), /*#__PURE__*/React.createElement("div", {
    className: "bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3"
  }, /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-slate-900 text-sm"
  }, "Distribuci\xF3n por Condici\xF3n / Discapacidad"), /*#__PURE__*/React.createElement("div", {
    className: "space-y-2 max-h-80 overflow-y-auto"
  }, Object.entries((stats === null || stats === void 0 ? void 0 : stats.distribucion_condicion) || {}).map(([cond, cnt]) => /*#__PURE__*/React.createElement("div", {
    key: cond,
    className: "flex items-center justify-between text-xs"
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-slate-700 truncate max-w-[200px]",
    title: cond
  }, cond), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center space-x-2"
  }, /*#__PURE__*/React.createElement("span", {
    className: "font-bold text-slate-900"
  }, cnt, " alumnos")))))))));
}
ReactDOM.createRoot(document.getElementById('root')).render( /*#__PURE__*/React.createElement(ErrorBoundary, null, /*#__PURE__*/React.createElement(App, null)));