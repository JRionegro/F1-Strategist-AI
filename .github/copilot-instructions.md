# Instrucciones para GitHub Copilot (Python)

## Objetivo
Generar código Python limpio, seguro y conforme a PEP8

---

## ? Buenas prácticas obligatorias
- Cumplir con PEP8 (indentación, nombres de variables, longitud de línea ? 120 caracteres).
- Usar type hints en funciones siempre que sea posible.
- Añadir docstrings descriptivos en funciones y clases.
- Evitar código redundante y variables sin uso.

---

## ? Errores que NO deben aparecer
- **F541**: No generar f-strings sin placeholders.
  - Si no hay interpolación, usar comillas normales:
    ```python
    mensaje = "Texto fijo"
    ```
  - Si hay interpolación:
    ```python
    nombre = "Gerardo"
    mensaje = f"Hola, {nombre}"
    ```
- Evitar `print` en código de producción; usar `logging`.
- No ignorar excepciones con `except:` vacío.

---

## ? Estilo y convenciones
- Usar `snake_case` para variables y funciones.
- Usar `PascalCase` para clases.
- Preferir list comprehensions sobre bucles simples cuando sea legible.
- Evitar comentarios innecesarios; usar comentarios solo para aclarar lógica compleja.

---

## ? Librerías recomendadas
- Para logs: `import logging`
- Para manejo de errores: `try/except` con mensajes claros.
- Para validación: usar `assert` o librerías como `pydantic` si aplica.

---

## Estilo Markdown

- Seguir las reglas definidas en `.markdownlint.json`.
- Evitar errores comunes como:
  - MD051: fragmentos de enlace inválidos
  - MD013: líneas demasiado largas
  - MD033: uso de HTML en Markdown
- Mantener consistencia en encabezados, listas, enlaces y espaciado.

---

## Ejemplo correcto
```python
import logging
def saludar(nombre: str) -> str:
    """Devuelve un saludo personalizado."""
    if not nombre:
        logging.warning("Nombre vacío recibido")
        return "Hola"
    return f"Hola, {nombre}"


## Ficheros de Test
- Los ficheros de test deben validar que **no existan errores F541** en el código generado.
- Los ficheros de test deben crearse dentro de la carpeta `tests/`.
- Cada test debe usar `flake8` o `pytest-flake8` para comprobar que el código cumple las reglas.
- Ejemplo de test con `pytest`:
    ```python
    import subprocess

    def test_flake8_compliance():
        """Verifica que no haya errores F541 en el código."""
        result = subprocess.run(["flake8", "--select=F541", "src/"], capture_output=True, text=True)
        assert result.returncode == 0, f"Errores F541 encontrados:\n{result.stdout}"
    ```

Aquí tienes un bloque completo listo para incorporar en tu fichero **`copilot-instructions.md`**, bajo una sección dedicada a estándares de programación en Python:

---

## **Estándares de Código Python**

Para garantizar calidad y evitar errores comunes al generar código Python, sigue estas directrices:

### ? **1. Cumplimiento PEP 8**
- Usa **indentación de 4 espacios**.
- Nombres de variables y funciones en **snake_case**.
- Clases en **CamelCase**.
- Evita nombres ambiguos; usa nombres descriptivos.

### ? **2. Evitar el error E501 (líneas demasiado largas)**
- **Longitud máxima de línea**:  
  - Código: **79 caracteres**.  
  - Comentarios y docstrings: **72 caracteres**.
- **Divide líneas largas con paréntesis**:  
  ```python
  resultado = (
      funcion_larga(parametro1, parametro2, parametro3, parametro4)
  )
  ```
- **Concatenación de cadenas**:  
  ```python
  mensaje = (
      "Este es un texto muy largo que se divide "
      "en varias líneas para cumplir con PEP 8."
  )
  ```
- **Evita barras invertidas (`\`)**:  
  Prefiere paréntesis para dividir líneas.
- **Configura herramientas de linting**:  
  Si usas **Flake8**, añade:  
  ```ini
  [flake8]
  max-line-length = 79
  ```



