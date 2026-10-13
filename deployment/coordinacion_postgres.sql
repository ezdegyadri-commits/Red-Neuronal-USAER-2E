-- Solo un proyecto de coordinación: no modifica la base educativa de Sheets.
-- Ejecutar íntegro; las restricciones de acceso se aplican en la misma transacción.
begin;
create schema if not exists usaer_coord;
create table if not exists usaer_coord.operaciones (
 namespace text not null, clave text not null, token text not null,
 fase text not null check (fase in ('RESERVADO','INCIERTO')),
 creado timestamptz not null default clock_timestamp(),
 revision text, digest text, firma text,
 primary key(namespace,clave),
 check(namespace ~ '^[a-zA-Z0-9_-]{3,64}$'),
 check(clave ~ '^[a-f0-9]{64}$'), check(token ~ '^[a-f0-9]{32}$')
);
create table if not exists usaer_coord.cupos (
 namespace text not null, tipo text not null check(tipo in ('lectura','escritura')),
 eventos timestamptz[] not null default '{}',primary key(namespace,tipo)
);
alter table usaer_coord.operaciones enable row level security;
alter table usaer_coord.cupos enable row level security;
revoke all on schema usaer_coord from public, anon, authenticated;
revoke all on all tables in schema usaer_coord from public, anon, authenticated;

create or replace function public.usaer_coord_operar(
 p_namespace text,p_accion text,p_clave text default '',p_token text default '',
 p_revision text default '',p_digest text default '',p_firma text default '',p_tipo text default ''
) returns jsonb language plpgsql security definer set search_path=pg_catalog as $$
declare
 v_row usaer_coord.operaciones%rowtype;
 v_eventos timestamptz[];v_now timestamptz;v_count integer;
begin
 if p_namespace is null or p_namespace !~ '^[a-zA-Z0-9_-]{3,64}$' then raise exception 'namespace inválido';end if;
 if p_accion='PRESUPUESTO' then
  if p_tipo not in ('lectura','escritura') then raise exception 'presupuesto inválido';end if;
  insert into usaer_coord.cupos(namespace,tipo) values(p_namespace,p_tipo) on conflict do nothing;
  select eventos into v_eventos from usaer_coord.cupos where namespace=p_namespace and tipo=p_tipo for update;
  v_now=clock_timestamp();
  select coalesce(array_agg(e order by e),'{}'::timestamptz[]) into v_eventos from unnest(v_eventos) as e where e>v_now-interval '60 seconds';
  update usaer_coord.cupos set eventos=v_eventos where namespace=p_namespace and tipo=p_tipo;
  if cardinality(v_eventos)>=45 then
   return jsonb_build_object('ok',true,'espera',greatest(1,ceil(extract(epoch from (v_eventos[1]+interval '60 seconds'-v_now)))::integer));
  end if;
  update usaer_coord.cupos set eventos=array_append(v_eventos,v_now) where namespace=p_namespace and tipo=p_tipo;
  return jsonb_build_object('ok',true,'espera',0);
 end if;
 if p_clave is null or p_clave !~ '^[a-f0-9]{64}$' or p_token is null or p_token !~ '^[a-f0-9]{32}$' then raise exception 'metadatos inválidos';end if;
 if p_accion='ADQUIRIR' then
  insert into usaer_coord.operaciones(namespace,clave,token,fase) values(p_namespace,p_clave,p_token,'RESERVADO')
  on conflict(namespace,clave) do update set token=excluded.token,fase='RESERVADO',creado=clock_timestamp(),revision=null,digest=null,firma=null
  where operaciones.fase='RESERVADO' and operaciones.creado<clock_timestamp()-interval '120 seconds'
  returning * into v_row;
  if found then return jsonb_build_object('ok',true);end if;
  select * into v_row from usaer_coord.operaciones where namespace=p_namespace and clave=p_clave;
  if not found then return jsonb_build_object('ok',false,'meta',jsonb_build_object('fase','RESERVADO'));end if;
  return jsonb_build_object('ok',false,'meta',jsonb_build_object('token',v_row.token,'fase',v_row.fase,'creado',v_row.creado,'revision',v_row.revision,'digest',v_row.digest,'firma',v_row.firma));
 elsif p_accion='INICIAR' then
  if p_revision is null or p_revision !~ '^[a-f0-9]{32}$' or p_digest is null or p_digest !~ '^[a-f0-9]{64}$' or p_firma is null or p_firma !~ '^[a-f0-9]{64}$' then raise exception 'huellas inválidas';end if;
  update usaer_coord.operaciones set fase='INCIERTO',revision=p_revision,digest=p_digest,firma=p_firma
  where namespace=p_namespace and clave=p_clave and token=p_token and fase='RESERVADO';
 elsif p_accion='LIBERAR' then
  delete from usaer_coord.operaciones where namespace=p_namespace and clave=p_clave and token=p_token;
 elsif p_accion='RECUPERAR' then
  delete from usaer_coord.operaciones where namespace=p_namespace and clave=p_clave and token=p_token and fase='INCIERTO' and revision=p_revision and digest=p_digest;
 else raise exception 'acción inválida';end if;
 get diagnostics v_count=row_count;
 return jsonb_build_object('ok',v_count=1);
end;
$$;
revoke all on function public.usaer_coord_operar(text,text,text,text,text,text,text,text) from public,anon,authenticated;
grant execute on function public.usaer_coord_operar(text,text,text,text,text,text,text,text) to service_role;
commit;
