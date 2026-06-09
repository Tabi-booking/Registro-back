-- =============================================================================
-- Validar onboarding completo — ejecutar en Supabase SQL Editor
--
-- Opción A: por ID del restaurante (recomendado)
--   Cambia el valor en la línea "params" abajo.
--
-- Opción B: por email del dueño
--   Descomenta el filtro en "por_email" al final.
-- =============================================================================

WITH params AS (
  SELECT
    16::bigint AS restaurant_id,           -- ← cambia por tu restaurant_id
    NULL::varchar AS owner_email           -- ej: 'juan.calle@roda.xyz'
),

-- ── Restaurante + ubicación ───────────────────────────────────────────────────
base AS (
  SELECT
    r.id,
    r.nombre,
    r.razon_social,
    r.descripcion,
    r.sitio_web,
    r.redes_sociales,
    r.direccion,
    r.telefono,
    r.google_maps,
    r.imagen_destacada,
    r.horarios          AS horarios_resumen,
    r.capacidad_asientos,
    r.numero_mesas,
    r.id_categoria,
    r.id_etiqueta,
    r.activo,
    r.onboarding_paso,
    r.onboarding_estado,
    r.onboarding_pct,
    r.onboarding_datos,
    r.onboarding_enviado_en,
    r.created_at,
    r.updated_at,
    u.pais,
    u.departamento,
    u.ciudad          AS ciudad_ubicacion,
    u.barrio,
    cat.nombre        AS categoria_principal
  FROM restaurante r
  CROSS JOIN params p
  LEFT JOIN ubicacion u ON u.id = r.id_ubicacion
  LEFT JOIN categorias cat ON cat.id = r.id_categoria
  WHERE r.id = p.restaurant_id
     OR (p.owner_email IS NOT NULL AND r.id IN (
           SELECT id_restaurante FROM usuario WHERE correo = p.owner_email
         ))
  LIMIT 1
),

-- ── Dueño (usuario) ───────────────────────────────────────────────────────────
owner AS (
  SELECT
    us.id,
    us.nombre,
    us.apellido,
    us.correo,
    us.telefono,
    us.activo,
    rol.nombre AS rol
  FROM usuario us
  JOIN base b ON us.id_restaurante = b.id
  JOIN rol ON rol.id = us.id_rol
  ORDER BY us.id
  LIMIT 1
),

-- ── Horarios por día ──────────────────────────────────────────────────────────
horarios_detalle AS (
  SELECT
    h.dia_semana,
    h.hora_apertura,
    h.hora_cierre,
    h.activo
  FROM horarios h
  JOIN base b ON h.id_restaurante = b.id
  ORDER BY h.dia_semana
),

-- ── Relaciones M2M ────────────────────────────────────────────────────────────
cocinas AS (
  SELECT c.nombre
  FROM restaurante_categoria rc
  JOIN categorias c ON c.id = rc.id_categoria
  JOIN base b ON rc.id_restaurante = b.id
  ORDER BY c.nombre
),

servicios AS (
  SELECT e.nombre
  FROM restaurante_etiqueta re
  JOIN etiquetas e ON e.id = re.id_etiqueta
  JOIN base b ON re.id_restaurante = b.id
  ORDER BY e.nombre
),

tipos_reserva AS (
  SELECT rtr.tipo
  FROM restaurante_tipo_reserva rtr
  JOIN base b ON rtr.id_restaurante = b.id
  ORDER BY rtr.tipo
),

imagenes AS (
  SELECT ri.url, ri.storage_key, ri.orden, ri.es_principal
  FROM restaurante_imagen ri
  JOIN base b ON ri.id_restaurante = b.id
  ORDER BY ri.orden
),

documentos AS (
  SELECT dr.tipo, dr.url, dr.nombre_archivo, dr.storage_key
  FROM documento_restaurante dr
  JOIN base b ON dr.id_restaurante = b.id
  ORDER BY dr.id
),

plan AS (
  SELECT s.plan, s.ciclo_facturacion, s.estado, s.inicio_en, s.expira_en
  FROM suscripcion_restaurante s
  JOIN base b ON s.id_restaurante = b.id
  LIMIT 1
)

-- =============================================================================
-- RESULTADO 1: Resumen legible (como la pantalla "Revisa tu información")
-- =============================================================================
SELECT
  '=== PERFIL ===' AS seccion,
  b.nombre                    AS "Nombre",
  b.categoria_principal       AS "Tipo",
  b.razon_social              AS "Razón social",
  b.sitio_web                 AS "Sitio web",
  b.descripcion               AS "Descripción",
  NULL::text                  AS extra
FROM base b

UNION ALL SELECT '=== UBICACIÓN ===', b.pais, b.ciudad_ubicacion, b.direccion, b.google_maps FROM base b
UNION ALL SELECT '=== CONTACTO ===', o.nombre || ' ' || o.apellido, o.correo, o.telefono, o.rol
  FROM owner o
UNION ALL SELECT '=== OPERACIONES ===',
  to_char((SELECT hora_apertura FROM horarios_detalle LIMIT 1), 'HH24:MI'),
  to_char((SELECT hora_cierre   FROM horarios_detalle LIMIT 1), 'HH24:MI'),
  b.capacidad_asientos::text || ' personas',
  b.numero_mesas::text || ' mesas'
FROM base b
UNION ALL SELECT '=== ONBOARDING ===',
  b.onboarding_estado,
  b.onboarding_paso::text,
  b.onboarding_pct::text || '%',
  CASE WHEN b.activo THEN 'activo' ELSE 'inactivo' END
FROM base b
UNION ALL SELECT '=== PLAN ===', p.plan, p.ciclo_facturacion, p.estado, NULL
FROM plan p;


-- =============================================================================
-- RESULTADO 2: Todo en una fila (fácil de comparar con el front)
-- =============================================================================
SELECT
  b.id                                                          AS restaurant_id,

  -- Paso 1
  b.nombre                                                      AS paso1_nombre,
  b.categoria_principal                                         AS paso1_tipo,
  b.razon_social                                                AS paso1_razon_social,
  b.sitio_web                                                   AS paso1_sitio_web,
  b.redes_sociales                                              AS paso1_redes_sociales,
  b.descripcion                                                 AS paso1_descripcion,
  b.onboarding_datos -> 'paso_1'                                AS paso1_json_guardado,

  -- Paso 2
  b.pais                                                        AS paso2_pais,
  b.ciudad_ubicacion                                            AS paso2_ciudad,
  b.direccion                                                   AS paso2_direccion,
  b.google_maps                                                 AS paso2_google_maps,
  b.onboarding_datos -> 'paso_2'                                AS paso2_json_guardado,

  -- Paso 3
  o.nombre || ' ' || o.apellido                                 AS paso3_propietario,
  o.correo                                                      AS paso3_email,
  COALESCE(o.telefono, b.telefono)                              AS paso3_telefono,
  b.onboarding_datos -> 'paso_3'                                AS paso3_json_guardado,

  -- Paso 4
  (SELECT hora_apertura FROM horarios_detalle LIMIT 1)          AS paso4_apertura,
  (SELECT hora_cierre   FROM horarios_detalle LIMIT 1)          AS paso4_cierre,
  b.capacidad_asientos                                          AS paso4_capacidad,
  b.numero_mesas                                                AS paso4_mesas,
  b.horarios_resumen                                            AS paso4_horarios_texto,
  b.onboarding_datos -> 'paso_4'                                AS paso4_json_guardado,

  -- Paso 5
  (SELECT json_agg(nombre ORDER BY nombre) FROM cocinas)        AS paso5_cocinas,
  (SELECT json_agg(nombre ORDER BY nombre) FROM servicios)      AS paso5_servicios,
  (SELECT json_agg(tipo  ORDER BY tipo)  FROM tipos_reserva)     AS paso5_tipos_reserva,
  b.onboarding_datos -> 'paso_5'                                AS paso5_json_guardado,

  -- Paso 6
  b.imagen_destacada                                            AS paso6_logo_url,
  (SELECT json_agg(json_build_object('url', url, 'key', storage_key, 'orden', orden))
   FROM imagenes)                                               AS paso6_fotos,
  (SELECT json_agg(json_build_object('tipo', tipo, 'url', url, 'archivo', nombre_archivo))
   FROM documentos)                                             AS paso6_documentos,
  b.onboarding_datos -> 'paso_6'                                AS paso6_json_guardado,

  -- Paso 7
  p.plan                                                        AS paso7_plan,
  p.ciclo_facturacion                                           AS paso7_facturacion,
  p.estado                                                      AS paso7_estado_suscripcion,
  b.onboarding_datos -> 'paso_7'                                AS paso7_json_guardado,

  -- Estado general
  b.onboarding_estado,
  b.onboarding_paso,
  b.onboarding_pct,
  b.onboarding_enviado_en,
  b.activo,
  b.onboarding_datos                                            AS onboarding_datos_completo

FROM base b
LEFT JOIN owner o ON true
LEFT JOIN plan p ON true;


-- =============================================================================
-- RESULTADO 3: Checklist automático vs valores esperados (tu caso concreto)
-- Cambia restaurant_id en "params" arriba y ejecuta solo este bloque si quieres.
-- =============================================================================
SELECT
  check_item,
  esperado,
  actual,
  CASE WHEN ok THEN '✓ OK' ELSE '✗ REVISAR' END AS resultado
FROM (
  SELECT
    'Nombre' AS check_item,
    'tartaria de mozart' AS esperado,
    b.nombre AS actual,
    lower(trim(b.nombre)) = lower('tartaria de mozart') AS ok
  FROM base b

  UNION ALL SELECT 'Tipo', 'Casual', b.categoria_principal,
    lower(b.categoria_principal) = 'casual' FROM base b

  UNION ALL SELECT 'Razón social', 'tartaria de mozart sas', b.razon_social,
    lower(trim(b.razon_social)) = lower('tartaria de mozart sas') FROM base b

  UNION ALL SELECT 'Sitio web', 'http://192.168.1.9:3000/reportes', b.sitio_web,
    b.sitio_web = 'http://192.168.1.9:3000/reportes' FROM base b

  UNION ALL SELECT 'País', 'Colombia', b.pais,
    b.pais = 'Colombia' FROM base b

  UNION ALL SELECT 'Ciudad', 'Medellín', b.ciudad_ubicacion,
    lower(b.ciudad_ubicacion) IN ('medellín', 'medellin') FROM base b

  UNION ALL SELECT 'Dirección', 'calle 23221', b.direccion,
    lower(trim(b.direccion)) = lower('calle 23221') FROM base b

  UNION ALL SELECT 'Google Maps', 'presente', CASE WHEN b.google_maps IS NOT NULL THEN 'presente' ELSE 'ausente' END,
    b.google_maps IS NOT NULL AND length(b.google_maps) > 10 FROM base b

  UNION ALL SELECT 'Propietario', 'juanchooo', o.nombre || ' ' || o.apellido,
    lower(o.nombre) LIKE '%juanch%' OR lower(o.apellido) LIKE '%juanch%' FROM owner o

  UNION ALL SELECT 'Email', 'juan.calle@roda.xyz', o.correo,
    lower(o.correo) = lower('juan.calle@roda.xyz') FROM owner o

  UNION ALL SELECT 'Teléfono', '+573157350513', COALESCE(o.telefono, b.telefono),
    COALESCE(o.telefono, b.telefono) = '+573157350513' FROM owner o JOIN base b ON true

  UNION ALL SELECT 'Apertura', '12:30', to_char((SELECT hora_apertura FROM horarios_detalle LIMIT 1), 'HH24:MI'),
    to_char((SELECT hora_apertura FROM horarios_detalle LIMIT 1), 'HH24:MI') = '12:30' FROM base b

  UNION ALL SELECT 'Cierre', '22:00', to_char((SELECT hora_cierre FROM horarios_detalle LIMIT 1), 'HH24:MI'),
    to_char((SELECT hora_cierre FROM horarios_detalle LIMIT 1), 'HH24:MI') = '22:00' FROM base b

  UNION ALL SELECT 'Capacidad', '50', b.capacidad_asientos::text,
    b.capacidad_asientos = 50 FROM base b

  UNION ALL SELECT 'Mesas', '15', b.numero_mesas::text,
    b.numero_mesas = 15 FROM base b

  UNION ALL SELECT 'Reservas online', 'online',
    CASE WHEN EXISTS (SELECT 1 FROM tipos_reserva WHERE tipo = 'online') THEN 'online' ELSE 'ausente' END,
    EXISTS (SELECT 1 FROM tipos_reserva WHERE tipo = 'online')

  UNION ALL SELECT 'Reservas terceros', 'third_party',
    CASE WHEN EXISTS (SELECT 1 FROM tipos_reserva WHERE tipo = 'third_party') THEN 'third_party' ELSE 'ausente' END,
    EXISTS (SELECT 1 FROM tipos_reserva WHERE tipo = 'third_party')

  UNION ALL SELECT 'Cocina italiana', 'Italiana',
    CASE WHEN EXISTS (SELECT 1 FROM cocinas WHERE lower(nombre) LIKE '%italian%') THEN 'Italiana' ELSE 'ausente' END,
    EXISTS (SELECT 1 FROM cocinas WHERE lower(nombre) LIKE '%italian%')

  UNION ALL SELECT 'Cocina colombiana', 'Colombiana',
    CASE WHEN EXISTS (SELECT 1 FROM cocinas WHERE lower(nombre) LIKE '%colombian%') THEN 'Colombiana' ELSE 'ausente' END,
    EXISTS (SELECT 1 FROM cocinas WHERE lower(nombre) LIKE '%colombian%')

  UNION ALL SELECT 'Servicios', '5 servicios',
    (SELECT count(*)::text FROM servicios) || ' servicios',
    (SELECT count(*) FROM servicios) = 5

  UNION ALL SELECT 'Logo', 'No proporcionado',
    CASE WHEN b.imagen_destacada IS NULL THEN 'No proporcionado' ELSE b.imagen_destacada END,
    b.imagen_destacada IS NULL FROM base b

  UNION ALL SELECT 'Fotos', 'No proporcionado',
    CASE WHEN (SELECT count(*) FROM imagenes) = 0 THEN 'No proporcionado' ELSE (SELECT count(*)::text FROM imagenes) || ' fotos' END,
    (SELECT count(*) FROM imagenes) = 0 FROM base b

  UNION ALL SELECT 'Plan', 'pro', p.plan,
    lower(p.plan) = 'pro' FROM plan p

  UNION ALL SELECT 'Facturación', 'monthly', p.ciclo_facturacion,
    lower(p.ciclo_facturacion) = 'monthly' FROM plan p

) checks
ORDER BY check_item;
