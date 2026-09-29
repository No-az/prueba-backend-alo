# ADR 0002 · Las políticas son datos versionados, no código

**Estado:** aceptada

## Contexto

Hay tres productos con reglas distintas, y el bonus pide reevaluar "si cambian umbrales". La forma más directa sería una clase Strategy por producto con los umbrales escritos en el código. Así, cambiar un umbral implicaría un deploy y no quedaría registro de qué umbrales había antes.

## Decisión

- Reglas atómicas pequeñas (`MinScore`, `MinEmploymentMonths`, `MaxInstallmentToIncome`, `MinMonthlyIncome`) y combinadores (`AllOf`, `AnyOf`). Es el patrón Composite; cada regla es a la vez una Strategy.
- Cada política es un JSON guardado en la tabla `policy_versions` con un número de versión. Una fábrica (`domain/rules/factory.py`) lo convierte en el árbol de reglas y rechaza configuraciones inválidas antes de guardarlas.
- La política de un producto es su última versión. Publicar una versión nueva nunca modifica las anteriores.
- La selección por producto es una búsqueda (`PolicyCatalog` en memoria, o una consulta a la tabla), sin `if/elif`.
- Las proporciones se escriben como texto (`"0.25"`) para que nunca pasen por `float`.

## Consecuencias

- Cambiar un umbral es `python -m app.cli publish-policy ...`, sin deploy.
- Cada evaluación referencia la versión exacta con la que se decidió.
- Agregar un tipo de regla nuevo sí requiere código: una clase y una entrada en la fábrica.
- Para reconstruir la configuración se usa `to_config()`, y un test verifica que el JSON sobreviva ida y vuelta.
