"""Regras de declaração que têm **dois** consumidores: a emissão e a métrica.

O que mora aqui é o cálculo compartilhado, e não a superfície de nenhum dos
dois. A emissão vive em `range-core/participant/api/`, e os computadores de
métrica em `range-core/metrics/`; uma regra escrita nos dois seria a classe D4 —
duas implementações da mesma norma, divergindo em silêncio.
"""
