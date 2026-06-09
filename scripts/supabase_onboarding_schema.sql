-- =============================================================================
-- Tabi — Esquema de onboarding sobre tablas existentes
-- Ejecutar en Supabase SQL Editor (no usa Alembic)
--
-- Modelo:
--   restaurante  → datos del negocio + estado del wizard
--   ubicacion    → país / departamento / ciudad (vía id_ciudad opcional)
--   horarios     → franjas por día (id_restaurante)
--   usuario      → dueño / staff (id_restaurante + id_rol)
--   tablas hijas → imágenes, documentos, etiquetas, categorías, suscripción
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. restaurante — columnas nuevas para el formulario
-- -----------------------------------------------------------------------------
ALTER TABLE restaurante
  ADD COLUMN IF NOT EXISTS razon_social           varchar,
  ADD COLUMN IF NOT EXISTS descripcion            text,
  ADD COLUMN IF NOT EXISTS sitio_web              varchar,
  ADD COLUMN IF NOT EXISTS redes_sociales         jsonb,
  ADD COLUMN IF NOT EXISTS capacidad_asientos     smallint,
  ADD COLUMN IF NOT EXISTS numero_mesas           smallint,
  ADD COLUMN IF NOT EXISTS onboarding_paso        smallint      DEFAULT 1,
  ADD COLUMN IF NOT EXISTS onboarding_estado      varchar(30)   DEFAULT 'borrador',
  ADD COLUMN IF NOT EXISTS onboarding_pct         numeric(5, 2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS onboarding_datos       jsonb,
  ADD COLUMN IF NOT EXISTS onboarding_enviado_en  timestamptz;

COMMENT ON COLUMN restaurante.razon_social IS 'Razón social / nombre legal (paso 1)';
COMMENT ON COLUMN restaurante.descripcion IS 'Descripción del restaurante (paso 1)';
COMMENT ON COLUMN restaurante.sitio_web IS 'URL del sitio web (paso 1)';
COMMENT ON COLUMN restaurante.redes_sociales IS 'JSON: instagram, facebook, twitter, tiktok, youtube, linkedin (paso 1)';
COMMENT ON COLUMN restaurante.capacidad_asientos IS 'Aforo (paso 4)';
COMMENT ON COLUMN restaurante.numero_mesas IS 'Número de mesas (paso 4)';
COMMENT ON COLUMN restaurante.onboarding_paso IS 'Paso actual del wizard (1-7)';
COMMENT ON COLUMN restaurante.onboarding_estado IS 'borrador | enviado | aprobado | rechazado';
COMMENT ON COLUMN restaurante.onboarding_pct IS 'Porcentaje de completitud 0-100';
COMMENT ON COLUMN restaurante.onboarding_datos IS 'Snapshot JSON por paso del onboarding';
COMMENT ON COLUMN restaurante.onboarding_enviado_en IS 'Fecha de envío del formulario';

-- Estado del onboarding acotado (opcional pero recomendado)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_restaurante_onboarding_estado'
  ) THEN
    ALTER TABLE restaurante
      ADD CONSTRAINT chk_restaurante_onboarding_estado
      CHECK (onboarding_estado IN ('borrador', 'enviado', 'aprobado', 'rechazado'));
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2. usuario — sesión JWT (refresh token)
-- -----------------------------------------------------------------------------
ALTER TABLE usuario
  ADD COLUMN IF NOT EXISTS refresh_token_hash varchar;

COMMENT ON COLUMN usuario.refresh_token_hash IS 'Hash del refresh token para auth del formulario';

-- -----------------------------------------------------------------------------
-- 3. Tablas hijas nuevas (FK → restaurante)
-- -----------------------------------------------------------------------------

-- Galería / fotos de portada (paso 6)
CREATE TABLE IF NOT EXISTS restaurante_imagen (
  id              bigserial PRIMARY KEY,
  id_restaurante  bigint       NOT NULL,
  url             varchar      NOT NULL,
  storage_key     varchar,
  es_principal    boolean      NOT NULL DEFAULT false,
  orden           smallint     NOT NULL DEFAULT 0,
  creado_en       timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE restaurante_imagen IS 'Imágenes del restaurante (logo adicional, covers)';

-- Documentos legales (paso 6)
CREATE TABLE IF NOT EXISTS documento_restaurante (
  id              bigserial PRIMARY KEY,
  id_restaurante  bigint       NOT NULL,
  tipo            varchar(50)  NOT NULL,
  url             varchar      NOT NULL,
  storage_key     varchar,
  nombre_archivo  varchar,
  mime_type       varchar(100),
  tamano_bytes    integer,
  creado_en       timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE documento_restaurante IS 'RUT, cámara de comercio, etc.';
COMMENT ON COLUMN documento_restaurante.tipo IS 'logo | cover | business_doc | rut | otro';

-- Varias etiquetas / servicios por restaurante (paso 5)
CREATE TABLE IF NOT EXISTS restaurante_etiqueta (
  id_restaurante  bigint  NOT NULL,
  id_etiqueta     bigint  NOT NULL,
  creado_en       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id_restaurante, id_etiqueta)
);

COMMENT ON TABLE restaurante_etiqueta IS 'Servicios/etiquetas M2M (wifi, terraza, etc.)';

-- Varias categorías / tipos de cocina (paso 5)
CREATE TABLE IF NOT EXISTS restaurante_categoria (
  id_restaurante  bigint  NOT NULL,
  id_categoria    bigint  NOT NULL,
  creado_en       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id_restaurante, id_categoria)
);

COMMENT ON TABLE restaurante_categoria IS 'Tipos de cocina M2M';

-- Plan / suscripción (paso 7)
CREATE TABLE IF NOT EXISTS suscripcion_restaurante (
  id                  bigserial PRIMARY KEY,
  id_restaurante      bigint       NOT NULL,
  plan                varchar(50)  NOT NULL DEFAULT 'starter',
  ciclo_facturacion   varchar(20)  NOT NULL DEFAULT 'monthly',
  estado              varchar(30)  NOT NULL DEFAULT 'trial',
  inicio_en           timestamptz,
  expira_en           timestamptz,
  creado_en           timestamptz  NOT NULL DEFAULT now(),
  actualizado_en      timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE suscripcion_restaurante IS 'Plan Tabi: starter | pro | elite';
COMMENT ON COLUMN suscripcion_restaurante.ciclo_facturacion IS 'monthly | annual';

-- Tipos de reserva del restaurante (paso 5)
CREATE TABLE IF NOT EXISTS restaurante_tipo_reserva (
  id_restaurante  bigint      NOT NULL,
  tipo            varchar(30) NOT NULL,
  creado_en       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id_restaurante, tipo),
  CONSTRAINT chk_tipo_reserva CHECK (tipo IN ('online', 'phone', 'walk_in', 'third_party'))
);

COMMENT ON TABLE restaurante_tipo_reserva IS 'Canales de reserva aceptados';

-- -----------------------------------------------------------------------------
-- 4. Foreign keys (solo si no existen)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  -- restaurante → ubicacion, categorias, etiquetas
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_ubicacion') THEN
    ALTER TABLE restaurante
      ADD CONSTRAINT fk_restaurante_ubicacion
      FOREIGN KEY (id_ubicacion) REFERENCES ubicacion(id)
      ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_categoria') THEN
    ALTER TABLE restaurante
      ADD CONSTRAINT fk_restaurante_categoria
      FOREIGN KEY (id_categoria) REFERENCES categorias(id)
      ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_etiqueta') THEN
    ALTER TABLE restaurante
      ADD CONSTRAINT fk_restaurante_etiqueta
      FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id)
      ON DELETE SET NULL;
  END IF;

  -- usuario → restaurante, rol
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_usuario_restaurante') THEN
    ALTER TABLE usuario
      ADD CONSTRAINT fk_usuario_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_usuario_rol') THEN
    ALTER TABLE usuario
      ADD CONSTRAINT fk_usuario_rol
      FOREIGN KEY (id_rol) REFERENCES rol(id)
      ON DELETE RESTRICT;
  END IF;

  -- horarios → restaurante
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_horarios_restaurante') THEN
    ALTER TABLE horarios
      ADD CONSTRAINT fk_horarios_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  -- rango_precio_restaurante → restaurante
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rango_precio_restaurante') THEN
    ALTER TABLE rango_precio_restaurante
      ADD CONSTRAINT fk_rango_precio_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  -- ubicacion → ciudad
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ubicacion_ciudad') THEN
    ALTER TABLE ubicacion
      ADD CONSTRAINT fk_ubicacion_ciudad
      FOREIGN KEY (id_ciudad) REFERENCES ciudad(id)
      ON DELETE SET NULL;
  END IF;

  -- ciudad → departamento
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ciudad_departamento') THEN
    ALTER TABLE ciudad
      ADD CONSTRAINT fk_ciudad_departamento
      FOREIGN KEY (id_departamento) REFERENCES departamento(id)
      ON DELETE RESTRICT;
  END IF;

  -- Tablas hijas nuevas
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_imagen_restaurante') THEN
    ALTER TABLE restaurante_imagen
      ADD CONSTRAINT fk_restaurante_imagen_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_documento_restaurante_restaurante') THEN
    ALTER TABLE documento_restaurante
      ADD CONSTRAINT fk_documento_restaurante_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_etiqueta_restaurante') THEN
    ALTER TABLE restaurante_etiqueta
      ADD CONSTRAINT fk_restaurante_etiqueta_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_etiqueta_etiqueta') THEN
    ALTER TABLE restaurante_etiqueta
      ADD CONSTRAINT fk_restaurante_etiqueta_etiqueta
      FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_categoria_restaurante') THEN
    ALTER TABLE restaurante_categoria
      ADD CONSTRAINT fk_restaurante_categoria_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_categoria_categoria') THEN
    ALTER TABLE restaurante_categoria
      ADD CONSTRAINT fk_restaurante_categoria_categoria
      FOREIGN KEY (id_categoria) REFERENCES categorias(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_suscripcion_restaurante_restaurante') THEN
    ALTER TABLE suscripcion_restaurante
      ADD CONSTRAINT fk_suscripcion_restaurante_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_restaurante_tipo_reserva_restaurante') THEN
    ALTER TABLE restaurante_tipo_reserva
      ADD CONSTRAINT fk_restaurante_tipo_reserva_restaurante
      FOREIGN KEY (id_restaurante) REFERENCES restaurante(id)
      ON DELETE CASCADE;
  END IF;
END $$;

-- Un restaurante = una suscripción activa
CREATE UNIQUE INDEX IF NOT EXISTS uq_suscripcion_restaurante_id
  ON suscripcion_restaurante (id_restaurante);

-- Índices de consulta frecuente
CREATE INDEX IF NOT EXISTS ix_restaurante_onboarding_estado
  ON restaurante (onboarding_estado);

CREATE INDEX IF NOT EXISTS ix_restaurante_imagen_restaurante
  ON restaurante_imagen (id_restaurante);

CREATE INDEX IF NOT EXISTS ix_documento_restaurante_restaurante
  ON documento_restaurante (id_restaurante);

CREATE INDEX IF NOT EXISTS ix_usuario_restaurante
  ON usuario (id_restaurante);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_restaurante_storage_key
  ON documento_restaurante (storage_key)
  WHERE storage_key IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 5. Rol de propietario (si no existe)
-- -----------------------------------------------------------------------------
INSERT INTO rol (nombre, created_at, updated_at)
SELECT 'Propietario', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM rol WHERE nombre = 'Propietario');

COMMIT;

-- =============================================================================
-- EJEMPLO: flujo completo de onboarding (referencia)
-- =============================================================================
/*
-- 1) Crear restaurante vacío
INSERT INTO restaurante (
  nombre, direccion, activo,
  onboarding_paso, onboarding_estado, onboarding_pct
) VALUES (
  'Borrador', 'Pendiente', false,
  1, 'borrador', 0
) RETURNING id;

-- 2) Paso 1 — datos básicos
UPDATE restaurante SET
  nombre           = 'La Parrilla',
  razon_social     = 'La Parrilla SAS',
  descripcion      = 'Carnes a la parrilla',
  sitio_web        = 'https://laparrilla.com',
  redes_sociales   = '{"instagram":"https://instagram.com/laparrilla"}'::jsonb,
  id_categoria     = (SELECT id FROM categorias WHERE nombre = 'Casual' LIMIT 1),
  onboarding_paso  = 2,
  onboarding_pct   = 20,
  onboarding_datos = jsonb_set(
    COALESCE(onboarding_datos, '{}'::jsonb),
    '{paso_1}',
    '{"restaurant_name":"La Parrilla","legal_name":"La Parrilla SAS"}'::jsonb
  ),
  updated_at = now()
WHERE id = :restaurant_id;

-- 3) Paso 2 — ubicación
WITH nueva_ubicacion AS (
  INSERT INTO ubicacion (pais, departamento, ciudad, barrio)
  VALUES ('Colombia', 'Cundinamarca', 'Bogotá', 'Chapinero')
  RETURNING id
)
UPDATE restaurante SET
  direccion      = 'Calle 100 #15-20',
  id_ubicacion   = (SELECT id FROM nueva_ubicacion),
  google_maps    = 'https://maps.google.com/?q=4.6872,-74.0447',
  onboarding_paso = 3,
  onboarding_pct  = 40,
  updated_at = now()
WHERE id = :restaurant_id;

-- 4) Paso 3 — contacto (teléfono en restaurante; usuario se crea en register)
UPDATE restaurante SET
  telefono        = '+573001234567',
  onboarding_paso = 4,
  onboarding_pct  = 60,
  updated_at = now()
WHERE id = :restaurant_id;

-- 5) Paso 4 — horarios (7 días)
INSERT INTO horarios (id_restaurante, dia_semana, hora_apertura, hora_cierre, activo)
SELECT :restaurant_id, d, '09:00'::time, '22:00'::time, true
FROM generate_series(0, 6) AS d
ON CONFLICT DO NOTHING;

UPDATE restaurante SET
  horarios           = '09:00-22:00',
  capacidad_asientos = 80,
  numero_mesas       = 20,
  onboarding_paso    = 5,
  updated_at = now()
WHERE id = :restaurant_id;

-- 6) Paso 5 — categorías, etiquetas, tipos de reserva
INSERT INTO restaurante_categoria (id_restaurante, id_categoria)
SELECT :restaurant_id, id FROM categorias WHERE nombre IN ('Colombiana', 'Parrilla')
ON CONFLICT DO NOTHING;

INSERT INTO restaurante_etiqueta (id_restaurante, id_etiqueta)
SELECT :restaurant_id, id FROM etiquetas WHERE nombre IN ('WiFi', 'Terraza')
ON CONFLICT DO NOTHING;

INSERT INTO restaurante_tipo_reserva (id_restaurante, tipo)
VALUES (:restaurant_id, 'online'), (:restaurant_id, 'walk_in')
ON CONFLICT DO NOTHING;

-- 7) Paso 6 — imágenes y documentos
UPDATE restaurante SET imagen_destacada = 'https://storage.../logo.png' WHERE id = :restaurant_id;

INSERT INTO restaurante_imagen (id_restaurante, url, storage_key, orden)
VALUES (:restaurant_id, 'https://storage.../cover1.jpg', 'restaurants/1/cover/abc.jpg', 1);

INSERT INTO documento_restaurante (id_restaurante, tipo, url, storage_key, nombre_archivo)
VALUES (:restaurant_id, 'business_doc', 'https://storage.../rut.pdf', 'restaurants/1/docs/rut.pdf', 'rut.pdf');

-- 8) Paso 7 — plan
INSERT INTO suscripcion_restaurante (id_restaurante, plan, ciclo_facturacion, estado)
VALUES (:restaurant_id, 'pro', 'monthly', 'trial')
ON CONFLICT (id_restaurante) DO UPDATE SET
  plan = EXCLUDED.plan,
  ciclo_facturacion = EXCLUDED.ciclo_facturacion,
  actualizado_en = now();

-- 9) Registrar dueño (auth)
INSERT INTO usuario (
  nombre, apellido, telefono, correo, contrasena,
  id_rol, id_restaurante, activo
) VALUES (
  'Juan', 'Pérez', '+573001234567', 'owner@restaurant.com', '<hash_bcrypt>',
  (SELECT id FROM rol WHERE nombre = 'Propietario'),
  :restaurant_id,
  true
);

-- 10) Enviar onboarding
UPDATE restaurante SET
  onboarding_estado       = 'enviado',
  onboarding_enviado_en   = now(),
  onboarding_pct          = 100,
  activo                  = true,
  updated_at              = now()
WHERE id = :restaurant_id;
*/
