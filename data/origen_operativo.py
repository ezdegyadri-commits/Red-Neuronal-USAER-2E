"""La interfaz usa exclusivamente el adaptador documental PostgreSQL."""
def usar_sql():
    # False desactiva SOLAMENTE el repositorio SQL parcial de la migración antigua.
    # data.google ahora es un adaptador PostgreSQL para todos los diarios y tablas.
    return False
