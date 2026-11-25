-- Ejecutar en MySQL Workbench como script completo.
CREATE DATABASE IF NOT EXISTS tutorloreto CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tutorloreto;

CREATE TABLE IF NOT EXISTS asignaturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS perfiles_estudio (
    id CHAR(36) PRIMARY KEY,
    grado TINYINT UNSIGNED NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
      ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_perfiles_grado CHECK (grado BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS consultas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asignatura_id INT NOT NULL,
    perfil_id CHAR(36) NULL,
    pregunta TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_consultas_asignaturas
      FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id),
    CONSTRAINT fk_consultas_perfil
      FOREIGN KEY (perfil_id) REFERENCES perfiles_estudio(id),
    INDEX ix_consultas_perfil_fecha (perfil_id, creado_en)
);

-- Preparada para implementar HU04; no se llena en esta entrega.
CREATE TABLE IF NOT EXISTS respuestas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consulta_id INT NOT NULL,
    contenido TEXT NOT NULL,
    origen VARCHAR(30) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_respuestas_consultas
      FOREIGN KEY (consulta_id) REFERENCES consultas(id)
);

CREATE TABLE IF NOT EXISTS practicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    perfil_id CHAR(36) NOT NULL,
    asignatura_id INT NOT NULL,
    tema VARCHAR(180) NOT NULL,
    dificultad VARCHAR(12) NOT NULL,
    enunciado TEXT NOT NULL,
    opciones_json JSON NOT NULL,
    respuesta_correcta TINYINT UNSIGNED NOT NULL,
    explicacion TEXT NOT NULL,
    respuesta_elegida TINYINT UNSIGNED NULL,
    correcta BOOLEAN NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    respondido_en TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT chk_practicas_dificultad
      CHECK (dificultad IN ('basico', 'intermedio', 'reto')),
    CONSTRAINT chk_practicas_respuesta
      CHECK (respuesta_correcta BETWEEN 0 AND 3),
    CONSTRAINT fk_practicas_perfil
      FOREIGN KEY (perfil_id) REFERENCES perfiles_estudio(id),
    CONSTRAINT fk_practicas_asignatura
      FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id),
    INDEX ix_practicas_perfil_tema_fecha (perfil_id, asignatura_id, tema, creado_en)
);

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

INSERT IGNORE INTO asignaturas (nombre) VALUES
('Matemática'),
('Comunicación'),
('Ciencia y Tecnología'),
('Ciencias Sociales'),
('Desarrollo Personal, Ciudadanía y Cívica'),
('Educación para el Trabajo'),
('Inglés'),
('Arte y Cultura'),
('Educación Física'),
('Educación Religiosa'),
('Castellano como Segunda Lengua');

SELECT * FROM asignaturas;
