# BET AI | Fase 2 — diseño verificable para automatización
**14-oct-2026 | Versión 1.0 | Estado de ejecución: RESTRINGIDO / offline.**

## Punto de partida real
Repositorio **`diegoaranab/leagueStats`**, PR #16 (resolver manual) y PR #18 (auditoría Fase 1B); 85 pruebas en CI de PR #18. El PR #18 se fusionó; sin embargo el origen de datos LoL recientes quedó en **NO-GO** por límite de Drive y 403 de API. **No hay feed nuevo autorizado implementado**; no inferir que 85 pruebas garantizan cobertura actual.

## Alcance Fase 2A (sin alterar producción)
1. Aceptar únicamente **snapshot local suministrado manualmente** y metadatos fechados de procedencia; no descargar Oracle, ni iniciar sesión, ni tocar token, ni Playdoit.
2. Motor determinista de evaluación por mercado: normalizar decimales y contratos; calcular probabilidad de equilibrio, rango conservador y mínimo de momio. **Sin inventar p_modelo:** `UNVERIFIED` si no hay estimación sustentada y documentada.
3. Chequeos previos de permiso/procedencia, integridad, liga y torneo cubierto, horarios, localidad pregame, incertidumbre, cierre/líneas comparables. Bloquear `BET` si falla cualquiera; la opción `NO BET` debe ser salida explícita incluso con cuota alta.
4. Dos reportes de análisis diarios *sólo al autorizar datos suficientes*, según la ventana discutida **10:00 y 22:30 CDMX**, inicialmente **sin push**, exclusivamente lectura y simulaciones. No programar despliegue antes de pruebas.
5. Salida JSON y Markdown de máximo tres candidatos por método, más `STAR RECREATIONAL` opcional claramente etiquetado; `VALUE`/`STAR` y reales/shadows independientes. Nada de tickets automáticos.

## QA y criterios de aceptación
- Pruebas offline con fixtures: precios 1.55/1.66, desviaciones, cuotas malformadas, líneas inconsistentes, falta `p_modelo`, fuentes `STALE`/`UNVERIFIED`, formato BO1/BO5, ventanas de datos posteriores, Push y duplicados de identificadores.
- Nunca `BET` si probabilidad conservadora <= break-even o el origen no está verificado; no usar simplemente un haircut fijo del 3 pp.
- Pipeline separado de Angular, scrape-data y deploy-pages, sin recursos nuevos; los resultados privados no se publican en Pages.
- PR nuevo, no draft, con alcance/no-objetivos, pruebas Python y build Angular sin cambios. **No fusionar** hasta auditoría de seguridad y revisión; no mover el estado NO-GO por mero éxito de build.

## Pendiente antes de Fase 2B (datos automáticos)
Permiso documentado del proveedor para este uso, versión/cobertura temporal, esquema y IDs comparados, rate limits, método de autenticación permitido, costes y licencias. Una descarga manual aportada al chat no acredita permiso para scraping o distribución. No automatizar colocación de apuestas ni credenciales.

## Registro de hipótesis 14-oct
- `H1`: singles tradicionales y LoL superan en ROI a parlays tradicionales en muestra registrada; **confirmación descriptiva** (no causal / no futura).
- `H2`: filtros VALUE mejoran resultados en el futuro frente a `STAR` y `NO BET`; **no demostrada**.
- `H3`: ofertas Playdoit bajo mínimo estimado son sistemáticamente negativas; **no demostrada**, recopilar CLV y calibración.
- `H4`: props First Blood tienen mejores oportunidades en ciertos enfrentamientos; **no demostrada**: controlar selección de rivales, patch y muestras.

**Fuentes:** tracker `Bet_AI_7_tracker_2026-10-14_auditado.xlsx`, informes del proyecto, https://github.com/diegoaranab/leagueStats/pull/16, https://github.com/diegoaranab/leagueStats/pull/18, https://developer.riotgames.com/policies/general.