# Plataforma de Videos en la Nube (AWS)

Arquitectura web desacoplada desplegada en Amazon Web Services:
- **Backend:** FastAPI, SQLModel y Uvicorn en EC2 (Ubuntu).
- **Base de Datos:** PostgreSQL en Amazon RDS.
- **Frontend y Media:** Amazon S3 (Hosting estático, videos y miniaturas).
