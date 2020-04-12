# Grammar Analyser

El objetivo del proyecto es diseñar un programa que permita realizar determinados procesamientos sobre gramáticas. El proyecto debe poseer una interfaz visual que permita tanto describir la gramática como reportar los resultados.

## Objetivos

Dada una gramática (representada en un formato de texto plano) realizar los siguientes análisis:

- Calcular los conjuntos _First_ y _Follow_.
- Determinar si la gramática es _LL(1)_. En caso afirmativo muestre la tabla del método predictivo no recursivo y dé los árboles de derivación para un conjunto de cadenas provistas. En caso negativo, reporte una cadena de conflicto junto con la explicación del conflicto. Transforme la gramática para el eliminar los prefijos comunes y la recursión izquierda inmediata.
- Realizar análisis similar al anterior pero con los parsers _SLR_, _LR_ y _LALR_. Incluya además en estos casos una visualización gráfica de los autómatas _LR(0)_ y _LR(1)_ según corresponda.
- Si la gramática es _regular_, convertirla a autómata y expresión regular.
- Mostrar versión de la gramática sin recursión izquierda inmediata, prefijos comunes y producciones innecesarias.

> Siéntase libre de implementar características adicionales.