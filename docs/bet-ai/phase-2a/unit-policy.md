# Bet AI — Fase 2B: unidad diaria (solo offline, sin apuestas)
**14-oct-2026**. Extiende el motor offline de Fase 2A. Las ganancias aún no cobradas no cuentan.

## Contrato
- Fuente: snapshot de la **versión más reciente del tracker en Library** que el operador debe proporcionar y verificar; GitHub Actions no tiene integración con Library en este PR.
- Cada mañana a las 10:00 CDMX: reconciliar capital, confirmar apuestas abiertas y congelar `1U = max(10 MXN, round(0.01 × capital_conciliado, 2))`. No cambiar 1U dentro del día.
- `capital_conciliado` incluye efectivo más costo de apuestas abiertas y **excluye retornos aún potenciales**; `efectivo_libre = capital_conciliado − exposición_abierta`. No apostar más si no alcanza 1U.
- Ejemplos: 425.53→10; 1,000→10; 1,300→13; 1,450→14.50. La siguiente mañana puede subir o bajar, sujeto al piso de 10.
- Por la noche a las 22:30: revisar resultados, payout real y pending; **no** recalcular la unidad matutina.
- Sin credenciales, API de apuestas, procesos programados, descargas, cambios a UI pública ni pagos. No colocar apuestas automáticamente.
- Entrada JSON `{"snapshot_date":"2026-10-14","reconciled_bankroll_mxn":"425.53","open_exposure_mxn":"20.00","source_tracker":"Bet_AI_8_tracker_2026-10-14_unidad_dinamica.xlsx","reconciliation_confirmed":true}`.
- Ejecución manual: `PYTHONPATH=tools/scraper/src python3 -m loltee_scraper.bet_ai_bankroll snapshot.json`.
- Fuente o conciliación ausentes: `UNVERIFIED`; jamás inferir dinero nuevo por una ganancia potencial.

## Límite de la fase
El módulo calcula cantidades a partir de un JSON local; **no** lee por sí mismo el tracker de Library ni hace la automatización programada. Cualquier scheduler o lector conectado necesita otro PR, autorización de fuentes y validaciones.
El riesgo por operación sigue siendo real incluso con una unidad del 1%; la rentabilidad no está garantizada.
