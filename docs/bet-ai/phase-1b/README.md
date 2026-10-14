# Fase 1B: fuente alternativa de Oracle's Elixir — NO-GO

Investigación del **14 de octubre de 2026**, America/Mexico_City, para
[Issue #17](https://github.com/diegoaranab/leagueStats/issues/17).
Base: `main` en `d7925d6d4be00e244477510c89688e464d4c8278`.

**NO-GO para LoL Bet AI con datos recientes verificables.** No se encontró una
alternativa a Drive que pudiera acreditar conjuntamente acceso estable, permiso
de uso, cobertura actual e integridad compatible con Oracle CSV. La API oficial
existe, pero eso no establece que sea una API pública autorizada para terceros.
Este resultado es limitado a las fuentes y observaciones descritas aquí; no
afirma que Oracle carezca de otras opciones privadas o futuras.

La entrega contiene evidencia, estadísticas históricas y pruebas offline.
No incluye un cliente alternativo, conversor de API, scraping del navegador ni
integración. Angular, workflows, horarios, despliegues y datasets públicos
permanecen intactos. No se ejecutó un workflow de descarga ni se contactó a terceros.

## PR #16 y run 38537687360

[PR #16](https://github.com/diegoaranab/leagueStats/pull/16) incorporó un resolver
aislado: Drive directo, Drive alternativo y `gdown`, luego caché o snapshot.
Las tres estrategias remotas dependen **del mismo archivo y proveedor**; no son
tres fuentes independientes. Usa temporales, reemplazo atómico, límites de
tamaño/tiempo, backoff exponencial, validación y SHA-256. El workflow manual
limita cada estrategia a dos intentos de 60 s, backoff de 2 s; su presupuesto
máximo remoto es 488 s. No cambió los descargadores productivos.

Los [logs del job](https://github.com/diegoaranab/leagueStats/actions/runs/38537687360/job/115764482575)
muestran dos respuestas HTML/cuota por cada endpoint de Drive y dos fallos de
`gdown` por límite de descarga. No hubo caché utilizable; se aceptó el snapshot
del commit `bbb7181beec3bfc0b19d9a341a7ae9897ad304de`. El guardado de caché se
omitió. El JSON extraído del log está en
[run-38537687360.metadata.json](run-38537687360.metadata.json):

| Campo | Resultado observado |
| --- | --- |
| Job / datos | `success` / `STALE`, `source=snapshot` |
| `downloaded_at` | `2026-10-14T08:48:17.711129Z` |
| `last_match_at` | `2026-03-20T18:38:36Z` |
| `upstream_changed_at` | No emitido por PR #16; desconocido |
| Edad de descarga / partida | 0 / 17.935.781 segundos |
| Filas / partidas | 25.764 / 2.147 |
| Bytes | 16.798.319 |
| SHA-256 | `1e9b3410a3c732a7ee66b4d40a63aee0159625c8b6584edc2fd9b178faa7a2f2` |
| `is_recent_for_bet_ai` / `cache_updated` | `false` / `false` |

La fecha de selección se captura **antes** de descargar; no es una hora exacta
de finalización. `content_changed=true` solo compara con archivos locales
anteriores: sin referencia anterior tampoco demuestra una actualización del
publicador. `checksum_verified=true` verifica contenido local; no es una firma
del publicador ni un checksum oficial independiente.

El resolver distingue descarga y partida, pero decide `FRESH`/`STALE` por
`last_match_at` con umbral de 24 h. La caché exige además checksum y edad de
descarga <=168 h. Ese criterio puede declarar obsoleta una fuente válida durante
un descanso competitivo. Se conserva el comportamiento de PR #16 para evitar
cambiar el sistema en este spike; **no usar su flag como prueba suficiente de
frescura o cobertura para Bet AI**.

## Disponibilidad, permisos y alternativas

Las consultas HTTP fueron GET anónimos, uno por URL, timeout 30 s, sin reintentos.
[source-evidence.json](source-evidence.json) registra fecha del servidor, estado,
tipo de contenido, tamaño y hash del cuerpo. Los cuerpos originales quedaron
temporales: no se redistribuyen bundles, cookies, claves, IPs ni páginas completas.
Los hashes permiten contrastarlos con originales conservados por el investigador;
un refetch puede cambiar por contenido dinámico. No prueban autenticidad por sí solos.

| Candidato | Evidencia y decisión |
| --- | --- |
| [Descargas oficiales](https://oracleselixir.com/tools/downloads) | HTTP 200 con shell React. Su [bundle oficial](https://oracleselixir.com/static/js/main.f194e6b7.js) enlaza a la carpeta de Drive. Publica CSV gratuitos y actualización diaria; no se encontró allí otro host de descarga. |
| [Carpeta oficial de Drive](https://drive.google.com/drive/u/1/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH) | Vista HTTP 200 tras redirección; el CSV 2026 apunta al mismo ID `1hnpbrUpBMS1TZI7IovfpKeZfWJH1Aptm`. Vista accesible no equivale a descarga disponible. No es fallback independiente. |
| [API oficial](https://api.oracleselixir.com/matchData) | Raíz, `/matchData` y robots devolvieron 403 HTML de Cloudflare el 14/10 a las 08:58:03 UTC. No se obtuvo JSON ni muestra de partidas. Estado `UNAVAILABLE`, contenido actual desconocido. |
| Snapshot del repositorio | CSV válido, histórico de marzo; sirve para reproducibilidad. No acredita cobertura de octubre. `STALE` por su alcance histórico conocido, no solamente por edad de la última partida. |
| Mirrors comunitarios / Kaggle / código de terceros | No son publicación oficial de OE. Ninguno se aceptó como fuente; no se descargaron ni se usaron como evidencia de actualidad o permiso. |
| [GRID](https://grid.gg/plans/) | Proveedor oficial separado: permisos, productos y cobertura dependen del acuerdo. Sin cuenta, contrato, muestra ni equivalencias de IDs verificadas. No es un reemplazo Oracle CSV. |

El bundle declara `api.oracleselixir.com` y llamadas como `/matchData`,
`/leagues/getLeagues`, `/tournaments/byLeague`, `/matches/recentResults/` y
`/games/singleGame/{id}`. Sus peticiones usan `X-Api-Key`, credenciales del
navegador y Turnstile. Estos son indicios de funciones del sitio, **no un contrato
de API**, garantía de paginación completa o permiso para copiar su configuración.
No se reutilizó la clave ni se resolvieron desafíos para extraer datos. No se
encontraron documentación pública de API, límites, SLA o licencia de extracción
en las páginas inspeccionadas; el bloqueo no permite determinar si la aplicación
subyacente aceptaría peticiones sin clave.

El [robots del sitio](https://oracleselixir.com/robots.txt) fue permisivo, pero no
otorga derechos de datos ni autoriza acceso a la API. El sitio remite a
[contacto](https://oracleselixir.com/contact) para aclarar usos, y a las
[políticas de Riot](https://developer.riotgames.com/policies/general) para los
datos de juego. Parte del contenido de Leaguepedia tiene licencia CC BY-SA;
no se puede extender esa licencia a todo OE ni al uso de su API.

Las políticas generales de Riot incluyen restricciones a funcionalidad de
apuestas; no se acreditó una autorización aplicable a Bet AI. Esto requiere
aclaración del titular, sin inferir permiso por tratarse de investigación personal.
La [documentación oficial de Riot](https://developer.riotgames.com/docs/lol)
describe API de partidas y torneos creados por desarrolladores; no acredita un
catálogo equivalente de todos los juegos profesionales de OE.

El enlace antiguo `https://grid.gg/open-access/` redirigió a planes comerciales.
La ruta antigua de LoL `https://grid.gg/get-league-of-legends/` devolvió 410 en la
consulta web. Los [planes actuales de GRID](https://grid.gg/plans/) exigen
acordar alcance y precio; el plan de medios excluye usos vinculados a apuestas.
No se presupone acceso gratuito a LoL por anuncios antiguos de Open Access.

## Integridad y compatibilidad CSV

Se extrajo el blob histórico `fbcf4f59e53481adf25934620220d01754dc2168` a `/tmp`,
sin alterar datasets. `validate_oracle_csv` reprodujo exactamente checksum,
tamaño, filas, partidas y última fecha de los logs. La fecha del commit
`2026-03-21T20:47:41Z` es procedencia del repositorio, **no** fecha de cambio de OE.
Las fechas CSV sin offset se interpretan como UTC, igual que PR #16.

[baseline-statistics.json](baseline-statistics.json) contiene las 165 columnas,
29 ligas, filas/partidas/última fecha por liga y patches `16.01`–`16.05`:

- 12 filas por partida: diez jugadores y equipos `participantid=100,200`.
- Cero claves duplicadas `(gameid, participantid)`.
- 23.196 filas `complete`; 2.568 `partial` (todas de LPL en este snapshot).
- `teamid` vacío en 978 filas, incluidas 815 de jugadores.
- `playerid` vacío en 4.903 filas: 4.294 de equipos y 609 de jugadores.

El validador de PR #16 exige 17 columnas y calidad básica, pero no exige
`teamid`/`playerid`, unicidad, doce participantes, ni `datacompleteness=complete`.
El consumidor Teamplay deduplica por juego/lado/posición, lo cual no demuestra
integridad para modelos de equipos o jugadores. Las ligas presentes en marzo
son una referencia histórica, no una lista completa de ligas activas hoy.

**Comparación API/CSV: no realizada por falta de muestra autorizada.** Campos,
IDs de juego/equipo/liga, nulls, patch y cobertura API permanecen desconocidos,
no se reportan como cero ni compatibles. Las rutas y agregados del frontend no
permiten asegurar exportación de las 165 columnas. No se rellenarán métricas
ausentes con ceros ni se equipararán IDs o nombres sin una tabla verificada.

## Contrato de frescura y controles para un futuro spike

Este contrato está documentado, **no implementado**. El ledger actual conserva
valores desconocidos como `null`, separa estado de acceso y contenido, y exige
todos los gates para pasar de NO-GO. Las pruebas protegen esas afirmaciones.

| Campo / estado | Evidencia necesaria |
| --- | --- |
| `downloaded_at` | Momento de recuperación válida de bytes del dataset; no HTTP Date de una página. |
| `upstream_changed_at` | Versión/fecha de cambio del dataset suministrada por el publicador y ligada al payload. `null` si desconocida. `Last-Modified` de HTML/JS solo fecha el despliegue web. |
| `last_match_at` | Máxima fecha de partida validada, con zona horaria y fecha por liga. Señal de actividad, no reloj de actualización. |
| `source_status` | `VALID`, `UNVERIFIED`, `UNAVAILABLE` o `HISTORICAL`, separado del estado de frescura. |
| `FRESH` | Fuente válida y autorizada, cobertura reconciliada hasta watermark del publicador y verificación reciente según su cadencia/lag. |
| `CACHED` | Snapshot íntegro, procedencia y última verificación vigente dentro del contrato aprobado; la fecha de lectura local no renueva su vigencia. |
| `STALE` | Alcance histórico conocido, watermark atrasado, juegos esperados ausentes tras el lag, o verificación expirada según contrato. |
| `FAILED` | No hay dataset utilizable; `source_status=UNAVAILABLE` si falla acceso. No inferir edad de contenido que no se obtuvo. |

Una pausa de 48 h con comprobación reciente de una versión válida, calendario
sin juegos y cobertura confirmada **puede ser FRESH**. Un CSV histórico bajado
hoy sigue siendo histórico. Si falta evidencia de versión/cobertura, mantener
`UNVERIFIED` y NO-GO; no convertir automáticamente una partida antigua en prueba
de obsolescencia. Nunca decidir con la máxima fecha global ocultando ligas ausentes.
No fijar ahora un SLA numérico para una API sin contrato. La publicación diaria
de CSV requiere tolerancia a su cadencia y lag acordado, no a la edad de un juego.

Para admitir una alternativa se necesitan: permiso explícito aplicable al uso,
documentación y autenticación propias, rate limits, muestra actual fechada,
watermark de cobertura por temporada/liga y calendario verificable. Comparar
IDs y filas de una ventana común con CSV oficial obtenido lícitamente, verificar
paginación completa, duplicados, cardinalidad, lados, posiciones, resultado,
nulls, completitud y cambios de esquema. Listar ligas faltantes y rechazar gates
desconocidos; no confundir un subset declarado con cobertura global.

La retención propuesta es privada: directorios UTC fechados con CSV/JSON original,
manifiesto de versión y fuente, SHA-256, esquema, cobertura, permiso y todos los
relojes. Crear snapshots de forma exclusiva, nunca sobrescribir; comprobar hash
al reutilizar y conservar evidencia de correcciones. Registrar cada fallo aparte
sin sustituir el último snapshot válido. Retención inicial propuesta de 30 días,
sujeta a licencia; no publicar raw data sin derechos confirmados.

Un futuro cliente tendrá presupuesto global y por fuente, backoff limitado con
jitter y `Retry-After`. Detenerse ante cuota/403/permisos; no multiplicar variantes
para eludir el mismo bloqueo. CSV: como máximo una recuperación diaria según la
cadencia publicada. API: solo la frecuencia autorizada, nunca una supuesta cuota.

## Validación y reapertura

```bash
PYTHONPATH=tools/scraper/src python3 -m unittest \
  tools.scraper.tests.test_oracle_source_evidence \
  tools.scraper.tests.test_oracle_download \
  tools.scraper.tests.test_oracle_download_workflow -v
python3 -m compileall -q tools/scraper/src tools/scraper/tests
git diff --check
```

Las nuevas pruebas comprueban consistencia del log y baseline, sumas por liga,
gates NO-GO y separación de relojes. También verifican que el validador acepta
CSV estructuralmente válido aunque no haya partidas en 48 h y rechaza HTML de
bloqueo: no prueban acceso en vivo ni implementan la nueva política de frescura.

Para reproducir el baseline desde un clon con ese objeto histórico:

```bash
git show bbb7181beec3bfc0b19d9a341a7ae9897ad304de:tools/scraper/data/raw/oracles_elixir/2026/2026_LoL_esports_match_data_from_OraclesElixir.csv > /tmp/oe-baseline-2026.csv
sha256sum /tmp/oe-baseline-2026.csv
```

Reabrir el spike cuando OE facilite acceso documentado y permitido o publique
un mirror propio con versión/coverage comprobables. GRID solo se evaluará como
suplemento identificado bajo acuerdo propio. Obtener autorización y muestra antes
de construir adaptadores. No se envió una solicitud al titular en este trabajo.

Tras superar los gates, una PR posterior podría probar el cliente manualmente,
en almacenamiento privado, comparar outputs y proponer integración preservando
League Stats. La conexión a `deploy-pages.yml`/`scrape-data.yml` requiere revisión
y aprobación separadas. Rollback: mantener el resolver previo y sus outputs,
desactivar la alternativa y restaurar el último snapshot íntegro, con su estado
real; nunca etiquetarlo como actual solo para mantener el pipeline verde.
