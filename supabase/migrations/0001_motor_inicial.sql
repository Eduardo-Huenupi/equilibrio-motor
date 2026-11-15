-- equilibrio-motor · esquema inicial
-- Fragmentos con búsqueda vectorial y de texto, auditoría encadenada y acciones pendientes.
-- Seguridad: RLS activado SIN políticas => solo el backend (service_role) puede leer o escribir.

create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------- fragmentos
create table if not exists public.motor_fragmentos (
  id               text primary key,
  org_id           text not null,
  documento_id     text not null,
  documento_nombre text not null,
  pagina           int  not null,
  texto            text not null,
  embedding        extensions.vector(1024) not null,
  tsv              tsvector generated always as (to_tsvector('spanish', texto)) stored,
  creado           timestamptz not null default now()
);

create index if not exists motor_fragmentos_org_idx on public.motor_fragmentos (org_id, documento_nombre);
create index if not exists motor_fragmentos_tsv_idx on public.motor_fragmentos using gin (tsv);
create index if not exists motor_fragmentos_vec_idx on public.motor_fragmentos
  using hnsw (embedding extensions.vector_cosine_ops);

alter table public.motor_fragmentos enable row level security;

create or replace function public.motor_buscar_vector(p_org text, p_vec extensions.vector, p_k int)
returns table (id text, org_id text, documento_id text, documento_nombre text, pagina int, texto text, puntaje double precision)
language sql stable
set search_path = public, extensions
as $$
  select f.id, f.org_id, f.documento_id, f.documento_nombre, f.pagina, f.texto,
         1 - (f.embedding <=> p_vec) as puntaje
  from public.motor_fragmentos f
  where f.org_id = p_org
  order by f.embedding <=> p_vec
  limit least(p_k, 100);
$$;

-- Búsqueda por palabras: basta que calce alguna palabra de la consulta (OR), ordenado por relevancia.
create or replace function public.motor_buscar_texto(p_org text, p_consulta text, p_k int)
returns table (id text, org_id text, documento_id text, documento_nombre text, pagina int, texto text, puntaje double precision)
language sql stable
set search_path = public, extensions
as $$
  with q as (
    select to_tsquery('spanish',
      array_to_string(tsvector_to_array(to_tsvector('spanish', p_consulta)), ' | ')) as consulta
    where length(to_tsvector('spanish', p_consulta)) > 0
  )
  select f.id, f.org_id, f.documento_id, f.documento_nombre, f.pagina, f.texto,
         ts_rank_cd(f.tsv, q.consulta)::double precision as puntaje
  from public.motor_fragmentos f, q
  where f.org_id = p_org and f.tsv @@ q.consulta
  order by puntaje desc
  limit least(p_k, 100);
$$;

-- ---------------------------------------------------------------- auditoría
create table if not exists public.motor_auditoria (
  n             bigint generated always as identity primary key,
  momento       timestamptz not null default now(),
  org_id        text not null,
  usuario       text not null,
  accion        text not null,
  recurso       text not null default '',
  resultado     text not null default 'ok',
  detalle       text not null default '',
  hash_anterior text not null default '',
  hash          text not null default ''
);

create index if not exists motor_auditoria_org_idx on public.motor_auditoria (org_id, n);
alter table public.motor_auditoria enable row level security;

create or replace function public.motor_hash_auditoria(
  p_anterior text, p_momento timestamptz, p_org text, p_usuario text,
  p_accion text, p_recurso text, p_resultado text, p_detalle text)
returns text language sql immutable
set search_path = public
as $$
  select encode(sha256(convert_to(concat_ws('|',
    p_anterior, to_char(p_momento at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'),
    p_org, p_usuario, p_accion, p_recurso, p_resultado, p_detalle), 'UTF8')), 'hex');
$$;

create or replace function public.motor_auditoria_encadenar()
returns trigger language plpgsql
set search_path = public
as $$
declare anterior text;
begin
  perform pg_advisory_xact_lock(hashtext('motor_auditoria'));
  select a.hash into anterior from public.motor_auditoria a order by a.n desc limit 1;
  new.momento := now();
  new.hash_anterior := coalesce(anterior, repeat('0', 64));
  new.hash := public.motor_hash_auditoria(new.hash_anterior, new.momento, new.org_id,
    new.usuario, new.accion, new.recurso, new.resultado, new.detalle);
  return new;
end $$;

create or replace function public.motor_auditoria_inmutable()
returns trigger language plpgsql
set search_path = public
as $$
begin
  raise exception 'motor_auditoria es de solo inserción: no se puede modificar ni borrar.';
end $$;

drop trigger if exists motor_auditoria_encadenar on public.motor_auditoria;
create trigger motor_auditoria_encadenar before insert on public.motor_auditoria
  for each row execute function public.motor_auditoria_encadenar();

drop trigger if exists motor_auditoria_sin_cambios on public.motor_auditoria;
create trigger motor_auditoria_sin_cambios before update or delete on public.motor_auditoria
  for each row execute function public.motor_auditoria_inmutable();

drop trigger if exists motor_auditoria_sin_truncate on public.motor_auditoria;
create trigger motor_auditoria_sin_truncate before truncate on public.motor_auditoria
  for each statement execute function public.motor_auditoria_inmutable();

create or replace function public.motor_verificar_auditoria()
returns boolean language plpgsql stable
set search_path = public
as $$
declare fila record; anterior text := repeat('0', 64);
begin
  for fila in select * from public.motor_auditoria order by n loop
    if fila.hash_anterior <> anterior or fila.hash <> public.motor_hash_auditoria(
        fila.hash_anterior, fila.momento, fila.org_id, fila.usuario, fila.accion,
        fila.recurso, fila.resultado, fila.detalle) then
      return false;
    end if;
    anterior := fila.hash;
  end loop;
  return true;
end $$;

-- ---------------------------------------------------------------- acciones pendientes
create table if not exists public.motor_acciones (
  id            uuid primary key default gen_random_uuid(),
  org_id        text not null,
  solicitante   text not null,
  accion        text not null,
  justificacion text not null,
  estado        text not null default 'pendiente'
                check (estado in ('pendiente', 'aprobada', 'rechazada', 'ejecutada')),
  resuelta_por  text not null default '',
  creada        timestamptz not null default now(),
  check (resuelta_por <> solicitante)
);
alter table public.motor_acciones enable row level security;

-- ---------------------------------------------------------------- permisos de ejecución
revoke all on function public.motor_buscar_vector(text, extensions.vector, int) from public, anon, authenticated;
revoke all on function public.motor_buscar_texto(text, text, int) from public, anon, authenticated;
revoke all on function public.motor_verificar_auditoria() from public, anon, authenticated;
grant execute on function public.motor_buscar_vector(text, extensions.vector, int) to service_role;
grant execute on function public.motor_buscar_texto(text, text, int) to service_role;
grant execute on function public.motor_verificar_auditoria() to service_role;
