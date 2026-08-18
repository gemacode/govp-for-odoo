# GOVP for Odoo

Módulo AGPL-3 para configurar GOVP Exchange sin código, probar la conexión,
emitir un GOVP al validar una entrega y comprobar su estado desde el albarán.

Compatibilidad validada con Odoo 18 y PostgreSQL: instalación, actualización,
desinstalación, entregas parciales, lotes/series, orden canónico y separación
multiempresa. El smoke usa contenedores y destruye todos sus datos al terminar.
La vigencia se calcula desde la fecha estable del albarán y no cambia al reintentar.

Instalación: descarga el ZIP de la release, súbelo a tus addons como
`govp_for_odoo`, actualiza la lista de aplicaciones e instala **GOVP for Odoo**.
Después configura la URL y el token de GOVP Exchange desde Ajustes.

```bash
python3 -m unittest discover -s tests -v
bash tests/native-smoke.sh
```

Código y releases: <https://github.com/gemacode/govp-for-odoo>.
