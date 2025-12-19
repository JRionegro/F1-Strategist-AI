# Prompt: Generar resumen de archivos Markdown y documentación del proyecto

## Objetivo
Leer todos los archivos `.md` del proyecto (excepto `README.md` y `ayuda.md`), resumir su contenido y generar dos archivos:

1. `README.md` en la raíz del proyecto, con un resumen general.
2. `resources/ayuda.md` con una ayuda para el usuario basada en los contenidos.

## Instrucciones para Copilot
- Recorre todos los archivos `.md` del proyecto, ignorando `README.md` y `ayuda.md`.
- Para cada archivo, extrae las primeras líneas significativas (títulos, subtítulos, descripciones).
- Genera un resumen general del proyecto en `README.md`, agrupando los contenidos por archivo.
- Crea o actualiza el archivo `resources/ayuda.md` con una ayuda para el usuario basada en los contenidos de los `.md`.
- Si la carpeta `resources` no existe, créala.
- Mantén el formato Markdown en ambos archivos.
- No modifiques el contenido original de los archivos `.md`, solo crea los resúmenes.

## Ejemplo de uso
> Usa el prompt `generar-resumen-md` para actualizar la documentación del proyecto.
