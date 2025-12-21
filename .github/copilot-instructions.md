# Instrucciones para GitHub Copilot (Python)

## Objetivo
Generar c�digo Python limpio, seguro y conforme a PEP8

---

## 📝 Idioma del Proyecto
- **Toda la documentación debe estar en inglés** (archivos .md, comentarios de código, docstrings).
- **Todo el código y mensajes deben estar en inglés** (nombres de variables, funciones, clases, logs).
- **Excepción**: Solo los mensajes dirigidos al usuario final en la UI pueden estar en español si es necesario.

---

## ? Buenas pr�cticas obligatorias
- Cumplir con PEP8 (indentaci�n, nombres de variables, longitud de l�nea ? 120 caracteres).
- Usar type hints en funciones siempre que sea posible.
- A�adir docstrings descriptivos en funciones y clases.
- Evitar c�digo redundante y variables sin uso.

---

## ? Errores que NO deben aparecer
- **F541**: No generar f-strings sin placeholders.
  - Si no hay interpolaci�n, usar comillas normales:
    ```python
    mensaje = "Texto fijo"
    ```
  - Si hay interpolaci�n:
    ```python
    nombre = "Gerardo"
    mensaje = f"Hola, {nombre}"
    ```
- Evitar `print` en c�digo de producci�n; usar `logging`.
- No ignorar excepciones con `except:` vac�o.

---

## ? Estilo y convenciones
- Usar `snake_case` para variables y funciones.
- Usar `PascalCase` para clases.
- Preferir list comprehensions sobre bucles simples cuando sea legible.
- Evitar comentarios innecesarios; usar comentarios solo para aclarar l�gica compleja.

---

## ? Librer�as recomendadas
- Para logs: `import logging`
- Para manejo de errores: `try/except` con mensajes claros.
- Para validaci�n: usar `assert` o librer�as como `pydantic` si aplica.

---

## Estilo Markdown

- Seguir las reglas definidas en `.markdownlint.json`.
- Evitar errores comunes como:
  - MD051: fragmentos de enlace inv�lidos
  - MD013: l�neas demasiado largas
  - MD033: uso de HTML en Markdown
- Mantener consistencia en encabezados, listas, enlaces y espaciado.

---

## Ejemplo correcto
```python
import logging
def saludar(nombre: str) -> str:
    """Devuelve un saludo personalizado."""
    if not nombre:
        logging.warning("Nombre vac�o recibido")
        return "Hola"
    return f"Hola, {nombre}"


## Ficheros de Test
- Los ficheros de test deben validar que **no existan errores F541** en el c�digo generado.
- Los ficheros de test deben crearse dentro de la carpeta `tests/`.
- Cada test debe usar `flake8` o `pytest-flake8` para comprobar que el c�digo cumple las reglas.
- Ejemplo de test con `pytest`:
    ```python
    import subprocess

    def test_flake8_compliance():
        """Verifica que no haya errores F541 en el c�digo."""
        result = subprocess.run(["flake8", "--select=F541", "src/"], capture_output=True, text=True)
        assert result.returncode == 0, f"Errores F541 encontrados:\n{result.stdout}"
    ```

Aqu� tienes un bloque completo listo para incorporar en tu fichero **`copilot-instructions.md`**, bajo una secci�n dedicada a est�ndares de programaci�n en Python:

---

## **Est�ndares de C�digo Python**

Para garantizar calidad y evitar errores comunes al generar c�digo Python, sigue estas directrices:

### ? **1. Cumplimiento PEP 8**
- Usa **indentaci�n de 4 espacios**.
- Nombres de variables y funciones en **snake_case**.
- Clases en **CamelCase**.
- Evita nombres ambiguos; usa nombres descriptivos.

### ? **2. Evitar el error E501 (l�neas demasiado largas)**
- **Longitud m�xima de l�nea**:  
  - C�digo: **79 caracteres**.  
  - Comentarios y docstrings: **72 caracteres**.
- **Divide l�neas largas con par�ntesis**:  
  ```python
  resultado = (
      funcion_larga(parametro1, parametro2, parametro3, parametro4)
  )
  ```
- **Concatenaci�n de cadenas**:  
  ```python
  mensaje = (
      "Este es un texto muy largo que se divide "
      "en varias l�neas para cumplir con PEP 8."
  )
  ```
- **Evita barras invertidas (`\`)**:  
  Prefiere par�ntesis para dividir l�neas.
- **Configura herramientas de linting**:  
  Si usas **Flake8**, a�ade:  
  ```ini
  [flake8]
  max-line-length = 79
  ```



