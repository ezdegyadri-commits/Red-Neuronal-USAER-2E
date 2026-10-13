"""Estado transitorio compartido por transporte, servicios e interfaz."""
class GuardadoPendiente(RuntimeError):
    def __init__(self,espera=15):
        self.espera=max(1,int(espera)+1)
        super().__init__('El guardado está pendiente para cuidar la conexión. Tu edición se conserva; se reintentará automáticamente.')
