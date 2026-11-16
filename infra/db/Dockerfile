# pgvector's official image is built on the same Debian release and PostgreSQL major,
# so its compiled extension can be copied in instead of installed with apt.
FROM pgvector/pgvector:0.8.7-pg18-trixie AS pgvector

FROM postgis/postgis:18-3.7

COPY --from=pgvector /usr/lib/postgresql/18/lib/vector.so /usr/lib/postgresql/18/lib/
COPY --from=pgvector /usr/share/postgresql/18/extension/vector* /usr/share/postgresql/18/extension/
COPY init-extensions.sql /docker-entrypoint-initdb.d/20-sadu-extensions.sql
