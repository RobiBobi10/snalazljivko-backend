@echo off
set DB=snalazljivko
set PGPASSWORD=postgres

REM 1) Drop i create baze
psql -U postgres -h localhost -p 5432 -c "DROP DATABASE IF EXISTS %DB%;"
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE %DB%;"

REM 2) Migracije
alembic upgrade head

REM 3) Seed barem jednog partnera (da PartnerDashboard ne pada)
psql -U postgres -h localhost -p 5432 -d %DB% -c ^
"INSERT INTO partners (naziv, adresa, lat, lng) VALUES ('Demo Pekara', 'Nemanjina 1, Beograd', 44.807, 20.462);"
echo Done.
