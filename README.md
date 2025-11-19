## Database Seeding

Para cargar datos de prueba bajo demanda puedes usar el nuevo comando CLI:

```
poetry run dlms seed
```

El comando se encargará de crear las tablas si aún no existen y luego ejecutará todos los seeders. Si ya aplicaste las migraciones y solo quieres resembrar los datos, ejecuta:

```
poetry run dlms seed --skip-init-db
```

Esto evita que se intente crear el esquema nuevamente antes de sembrar los datos.
