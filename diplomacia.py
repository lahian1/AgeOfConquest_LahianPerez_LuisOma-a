def mostrar_relaciones(diplomacia, imperios):
    """Imprime la tabla de relaciones entre todos los pares de imperios y los vasallajes."""
    print("  Tabla de relaciones diplomaticas:")
    for i in range(len(imperios)):
        for j in range(i + 1, len(imperios)):
            a, b = imperios[i], imperios[j]
            print(f"    {a.nombre} <-> {b.nombre}: {diplomacia.estado(a, b)}")
    for protegido, protector in diplomacia.protecciones.items():
        print(f"    {protegido.nombre} esta protegido por {protector.nombre} (paga tributo)")
