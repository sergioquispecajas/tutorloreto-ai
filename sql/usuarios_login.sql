-- Cuentas y sesiones de acceso escolar. Ejecutar después de sql/pmv2_3.sql.
-- Esta migración solo agrega tablas; conserva perfiles, consultas y prácticas.
USE tutorloreto;

CREATE TABLE IF NOT EXISTS usuarios (
    id CHAR(36) PRIMARY KEY,
    correo VARCHAR(254) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(160) NOT NULL,
    rol VARCHAR(20) NOT NULL,
    perfil_id CHAR(36) NULL UNIQUE,
    vigente_hasta DATE NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    debe_cambiar_contrasena BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_usuarios_rol CHECK (rol IN ('directivo', 'docente', 'alumno')),
    CONSTRAINT fk_usuarios_perfil
      FOREIGN KEY (perfil_id) REFERENCES perfiles_estudio(id)
);

CREATE TABLE IF NOT EXISTS sesiones (
    token_hash CHAR(64) PRIMARY KEY,
    usuario_id CHAR(36) NOT NULL,
    vence_en DATETIME NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sesiones_usuario
      FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX ix_sesiones_usuario_vence (usuario_id, vence_en)
);

SHOW TABLES LIKE 'usuarios';
SHOW TABLES LIKE 'sesiones';
