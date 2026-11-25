-- PMV 2 y 3: agregar perfil, práctica e historial a una base existente.
-- Ejecutar una vez en MySQL Workbench. Conserva todos los registros existentes.
USE tutorloreto;

CREATE TABLE IF NOT EXISTS perfiles_estudio (
    id CHAR(36) PRIMARY KEY,
    grado TINYINT UNSIGNED NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
      ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_perfiles_grado CHECK (grado BETWEEN 1 AND 5)
);

-- ALTER TABLE condicional para que el script pueda volver a ejecutarse.
SET @existe_perfil_consulta = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'consultas'
      AND column_name = 'perfil_id'
);
SET @sql_perfil_consulta = IF(
    @existe_perfil_consulta = 0,
    'ALTER TABLE consultas ADD COLUMN perfil_id CHAR(36) NULL AFTER asignatura_id',
    'SELECT ''La columna consultas.perfil_id ya existe'''
);
PREPARE stmt_perfil_consulta FROM @sql_perfil_consulta;
EXECUTE stmt_perfil_consulta;
DEALLOCATE PREPARE stmt_perfil_consulta;

SET @existe_indice_perfil = (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'consultas'
      AND index_name = 'ix_consultas_perfil_fecha'
);
SET @sql_indice_perfil = IF(
    @existe_indice_perfil = 0,
    'CREATE INDEX ix_consultas_perfil_fecha ON consultas (perfil_id, creado_en)',
    'SELECT ''El índice de perfil ya existe'''
);
PREPARE stmt_indice_perfil FROM @sql_indice_perfil;
EXECUTE stmt_indice_perfil;
DEALLOCATE PREPARE stmt_indice_perfil;

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

-- Comprueba las tablas agregadas; las consultas antiguas conservan perfil_id NULL.
SHOW TABLES LIKE 'perfiles_estudio';
SHOW TABLES LIKE 'practicas';
