import os
from jinja2 import Environment


class_buff = ''
model_uri_lookup_map = {}


def tsType( field ):
  suffix = ''
  if field.get( 'is_array', False ):
    suffix = '[]'

  choices = field.get( 'choices', None )

  if field[ 'type' ] == 'DateTime':
    return 'Date' + suffix

  elif field[ 'type' ] == 'Map':
    return '{}' + suffix

  elif field[ 'type' ] == 'Integer':
    if choices is not None:
      return ' | '.join( [ '{0}'.format( i ) for i in choices ] )

    return 'number' + suffix

  elif field[ 'type' ] == 'Boolean':
    return 'boolean' + suffix

  elif field[ 'type' ] == 'Model':
    return model_uri_lookup_map[ field[ 'uri' ] ] + suffix

  else:
    if choices is not None:
      return ' | '.join( [ "'{0}'".format( i ) for i in choices ] )

    return 'string' + suffix


def tsInit( field ):
  is_array = field.get( 'is_array', False )
  default = field.get( 'default', None )

  if default is None:
    return 'undefined'

  if field[ 'type' ] == 'Integer' and not is_array:
    return default

  elif field[ 'type' ] == 'String' and not is_array:
    return "'{0}'".format( default )

  elif field[ 'type' ] == 'Boolean' and not is_array:
    return 'true' if default else 'false'

  elif field[ 'type' ] == 'DateTime' and not is_array:
    return 'new Date( "{0}" )'.format( default )

  else:
    return default


def tsEmptyVal( field ):
  is_array = field.get( 'is_array', False )

  if field[ 'type' ] == 'DateTime':
    if is_array:
      return '[ Date() ]'
    else:
      return 'Date()'

  elif field[ 'type' ] == 'Map':
    if is_array:
      return '[ {} ]'
    else:
      return '{}'

  elif field[ 'type' ] == 'Integer':
    if is_array:
      return '[ 0 ]'
    else:
      return '0'

  elif field[ 'type' ] == 'Boolean':
    if is_array:
      return '[ false ]'
    else:
      return 'false'

  elif field[ 'type' ] == 'Model':
    if is_array:
      return '[ new {0}() ]'.format( model_uri_lookup_map[ field[ 'uri' ] ] )
    else:
      return 'new {0}()'.format( model_uri_lookup_map[ field[ 'uri' ] ] )

  else:
    if is_array:
      return "[ '' ]"
    else:
      return "''"


def tsParmValue( field ):
  if field[ 'type' ] == 'Model':
    if field.get( 'is_array', False ):
      return '{0}.map( i => i.toURL() )'.format( field[ 'name' ] )
    else:
      return '{0}.toURL()'.format( field[ 'name' ] )

  return field[ 'name' ]


def tsReturn( field, name ):
  if field[ 'type' ] == 'Model':
    if field.get( 'is_array', False ):
      return '{1}.map( ( val: string ) => {{ return new {0}( this, val ); }} )'.format( model_uri_lookup_map[ field[ 'uri' ] ], name )
    else:
      return 'new {0}( this, {1} )'.format( model_uri_lookup_map[ field[ 'uri' ] ], name )

  return '( {0} as {1} )'.format( name, tsType( field ) )


def tsParamaters( paramater_list ):
  if not paramater_list:
    return '', '{}', '', ''

  func_in_parms = ' ' + ', '.join( [ '{0}: {1}'.format( i[ 'name' ], tsType( i ) ) for i in paramater_list ] ) + ' '
  func_obj_parms = '{ ' + ', '.join( [ '"{0}": {1}'.format( i[ 'name' ], tsParmValue( i ) ) for i in paramater_list ] ) + ' }'
  func_out_parms = ' ' + ', '.join( [ i[ 'name' ] for i in paramater_list ] ) + ' '
  inline_type = '{ ' + ', '.join( [ '{0}: {1}'.format( i[ 'name' ], tsType( i ) ) for i in paramater_list ] ) + ' }'

  return func_in_parms, func_obj_parms, func_out_parms, inline_type


env = Environment( extensions=[ 'jinja2.ext.do' ] )
env.filters[ 'tstype' ] = tsType
env.filters[ 'tsParamaters' ] = tsParamaters
env.filters[ 'tsinit' ] = tsInit
env.filters[ 'tsemptyval' ] = tsEmptyVal
env.filters[ 'tsreturn' ] = tsReturn
env.filters[ 'tsparmvalue' ] = tsParmValue
service_header = env.from_string( """// Automatically generated by cinp-codegen from {{ url }} at {{ timestamp }}

import CInP, { List } from 'cinp'

export interface ListFilter {};
export class ListFilterAll implements ListFilter {};
export interface QueryFilter {};
type ModelUpdate<T> = T | Record<string, unknown>;
type ModelConstructorSource<T> = T | Record<string, unknown> | string | number | undefined; // and any other types used by pks

export interface ListParamaters
{
  filter?: ListFilter;
  position?: number;
  count?: number;
}

export interface QueryParamaters
{
  filter?: QueryFilter;
  sort?: string[];
  position?: number;
  count?: number;
}

export class {{ service }}
{
  private cinp: CInP;

  constructor( host: string )
  {
    this.cinp = new CInP( host );
  }

  async check(): Promise<boolean>
  {
    return this.cinp.describe( '{{ root_path }}' ).then( res => res.version === '{{ api_version }}' );
  }

  isAuthencated(): boolean
  {
    return this.cinp.isAuthencated();
  }

  setAuth( username: string, token: string ): void
  {
    this.cinp.setAuth( username, token );
  }

  async login( username: string, password: string ): Promise<string>
  {
    return this.Auth_User_call_login( username, password ).then( ( res ) => { this.cinp.setAuth( username, res ); return res; } );
  }

  async logout(): Promise<void>
  {
    if ( this.cinp.isAuthencated() )
    {
      return this.Auth_User_call_logout().finally( () => this.cinp.setAuth( null, null ) );
    }

    return new Promise<void>( ( resolve ) => { resolve(); } );
  }

""" )

service_footer = env.from_string( """
}

export default {{ service }};
""" )

ns_header = env.from_string( """
  // Namespace {{ name }} at {{ url }} version {{ api_version }}
/*
{{ doc }}
*/

""" )

ns_footer = env.from_string( """
  // Namespace {{ name }} (end)
""" )


model_methods_template = env.from_string( """
  // Model {{ name }} at {{ url }}
{% if 'GET' not in not_allowed_verb_list and id_field %}
  async {{ model_name }}_get( id: {{ id_field|tstype }} ): Promise<{{ model_name }}>
  {
    const response = await this.cinp.getOne<{{ model_name }}>( "{{ url }}:" + id + ":" );

    return new {{ model_name }}( this, response );
  }
{% endif %}{% if 'CREATE' not in not_allowed_verb_list %}
  async {{ model_name }}_create( data: {{ model_name }} ): Promise<void>
  {
    const response = await this.cinp.create<{{ model_name }}>( "{{ url }}", data );

    data._update( response.data );
  }
{% endif %}{% if 'UPDATE' not in not_allowed_verb_list and id_field  %}
  async {{ model_name }}_update( id: {{ id_field|tstype }}, data: {{ model_name }} ): Promise<void>
  {
    const response = await this.cinp.update<{{ model_name }}>( "{{ url }}:" + id + ":", data );

    data._update( response.data[1] );
  }
{% endif %}{% if 'DELETE' not in not_allowed_verb_list and id_field %}
  async {{ model_name }}_delete( id: {{ id_field|tstype }} ): Promise<void>
  {
    await this.cinp.delete( "{{ url }}:" + id + ":" );
  }
{% endif %}{% if 'LIST' not in not_allowed_verb_list %}
  _{{ model_name }}_filter_lookup( filter: ListFilter | undefined ): [ string | undefined, Record<string, unknown> | undefined ]
  {
    if( filter === undefined || filter instanceof ListFilterAll )
      return [ undefined, undefined ];
{% for filter in list_filter_map %}
    if( filter instanceof {{ model_name }}_ListFilter_{{ filter }} )
      return [ '{{ filter }}', { {% for field in list_filter_map[ filter ] %}{{ field.name }}: filter.{{ field|tsparmvalue }}, {% endfor %} } ];
{% endfor %}
    throw TypeError( 'Filter ' + filter + ' Is not valid' );
  }

  async {{ model_name }}_get_multi( { filter, position, count }: ListParamaters ): Promise<Record<string, {{ model_name }}>>
  {
    const [ filter_name, filter_value_map ] = this._{{ model_name }}_filter_lookup( filter );

    const response = await this.cinp.getFilteredObjects<{{ model_name }}>( "{{ url }}", filter_name, filter_value_map, position, count );

    for ( var key in response )
    {
      response[ key ] = new {{ model_name }}( this, response[ key ] );
    }

    return response;
  }

  async {{ model_name }}_list( { filter, position, count }: ListParamaters ): Promise<List>
  {
    const [ filter_name, filter_value_map ] = this._{{ model_name }}_filter_lookup( filter );
    return await this.cinp.list( "{{ url }}", filter_name, filter_value_map, position, count );
  }

{% if query_filter_fields or query_sort_fields %}
  async {{ model_name }}_query( { filter, sort, position, count }: QueryParamaters ): Promise<List>
  {
    const filter_value_map = { 'filter': filter ? filter : {}, 'sort': sort ? sort : [] };
    return await this.cinp.list( "{{ url }}", "_query_", filter_value_map, position, count );
  }
{% endif %}{% endif %}{% if 'CALL' not in not_allowed_verb_list %}
{% for action in action_list %}
{%- set func_in_parms, func_obj_parms, _, _ = action.paramater_list|tsParamaters %}
{%- if func_in_parms and not action.static %}{% set func_in_parms = ', ' + func_in_parms %}{% endif %}
{%- if not action.static %}{% set url = url + ':" + id + ":' %}{% endif %}
  async {{ model_name }}_call_{{ action.name }}({% if not action.static %} id: {{ id_field|tstype }} {% endif %}{{ func_in_parms }}): Promise<{% if action.return_type %}{{ action.return_type|tstype }}{% else %}void{% endif %}>
  {
    {% if action.return_type %}const response = {% endif %}await this.cinp.call( "{{ url }}({{ action.name }})", {{ func_obj_parms }} );
    {% if action.return_type %}return {{ action.return_type|tsreturn( 'response.data' ) }}{% else %}return{% endif %};
  }

{% endfor %}{% endif %}
  // Model {{ name }} (end)
""" )

model_class_template = env.from_string( """
// Model {{ name }} from {{ prefix }} at {{ url }}
/*
{{ doc }}
*/
export class {{ model_name }}
{
  private _service: {{ service }};
{% if id_field %}
  public {{ id_field.name }}: {{ id_field|tstype }} = {{ id_field|tsemptyval }};{% endif %}
{% for field in field_list %}{% if field.name != id_field.name %}
  public {{ field.name }}: {{ field|tstype }} | undefined = {{ field|tsinit }};{% endif %}{% endfor %}

  constructor( service: {{ service }}, source: ModelConstructorSource<{{ model_name }}> )
  {
    this._service = service;
    if( typeof source === 'object' )
    {
      source = source as {{ model_name }};
{%- if id_field %}
      this.{{ id_field.name }} = source.{{ id_field.name }};{% endif %}
      this._update( source );
    }
{%- if id_field %}
    else if( ( typeof source === 'string' ) && source.startsWith( '{{ url }}' ) )
    {
      this.{{ id_field.name }} = {% if id_field.type == 'Integer' %}parseInt( source.split( ':' )[ 1 ] ){% elif id_field.type == 'Model' %}new {{ model_uri_lookup_map[ id_field.uri ] }}( service, source.split( ':' )[ 1 ] ){% else %}source.split( ':' )[ 1 ]{% endif %};
    }
    else if( typeof source === '{{ id_field|tstype }}' )
    {
      this.{{ id_field.name }} = source;
    }
{%- endif %}
  }
{% if id_field %}
  toString(): string
  {
    return this.{{ id_field.name }}.toString();
  }

  toURL(): string
  {
    return '{{ url }}:' + this.{{ id_field.name }}.toString() + ':';
  }
{% endif %}
  _update( data: ModelUpdate<{{ model_name }}> ): void
  {
    data = data as {{ model_name }};
{%- for field in field_list %}{% if id_field and field.name != id_field.name %}
{%- if field.type == 'Model' %}
{%- if field.is_array %}
    if( data.{{ field.name }} !== undefined )
      this.{{ field.name }} = data.{{ field.name }}.map( ( uri ) => { return new {{ model_uri_lookup_map[ field.uri ] }}( this._service, uri ) } );
{%- else %}
    this.{{ field.name }} = new {{ model_uri_lookup_map[ field.uri ] }}( this._service, data.{{ field.name }} );
{%- endif %}
{%- else %}
    this.{{ field.name }} = data.{{ field.name }};
{%- endif %}{% endif %}{% endfor %}
  }
{% if 'GET' not in not_allowed_verb_list and id_field %}
  async _get(): Promise<void>
  {
    const record = await this._service.{{ model_name }}_get( this.{{ id_field.name }} );

    this._update( record );
  }
{% endif %}{% if 'UPDATE' not in not_allowed_verb_list and id_field %}
  async _save(): Promise<void>
  {
    return this._service.{{ model_name }}_update( this.{{ id_field.name }}, this );
  }
{% endif %}{% if 'DELETE' not in not_allowed_verb_list and id_field  %}
  async _delete(): Promise<void>
  {
    return this._service.{{ model_name }}_delete( this.{{ id_field.name }} );
  }
{% endif %}{% if 'CALL' not in not_allowed_verb_list %}
{% for action in action_list %}
{%- set func_in_parms, _, func_out_parms, _ = action.paramater_list|tsParamaters %}
{%- if func_in_parms and not action.static %}{% set func_out_parms = ', ' + func_out_parms %}{% endif %}
{%- if not action.static %}{% set url = url + ':" + id + ":' %}{% endif %}
  async _call_{{ action.name }}( {{ func_in_parms }} ): Promise<{% if action.return_type %}{{ action.return_type|tstype }}{% else %}void{% endif %}>
  {
    return this._service.{{ model_name }}_call_{{ action.name }}({% if not action.static %} this.{{ id_field.name }}{% endif %}{{ func_out_parms }} );
  }

{% endfor %}{% endif %}
}
{% if 'LIST' not in not_allowed_verb_list %}
{%- set filter_name_list = [] %}
{%- for filter in list_filter_map %}
{%- set func_in_parms, _, _, _ = list_filter_map[ filter ]|tsParamaters %}
export class {{ model_name }}_ListFilter_{{ filter }} implements ListFilter
{
{%- for field in list_filter_map[ filter ] %}
  public {{ field.name }}: {{ field|tstype }};
{%- endfor %}

  constructor({{ func_in_parms}})
  {
{%- for field in list_filter_map[ filter ] %}
    this.{{ field.name }} = {{ field.name }};
{%- endfor %}
  }
};

{% endfor %}{% if query_filter_fields or query_sort_fields %}
{%- set _, _, func_out_parms, inline_type = query_filter_fields|tsParamaters %}
export class {{ model_name }}_QueryFilter implements QueryFilter
{
{%- for field in query_filter_fields %}
  public {{ field.name }}: {{ field|tstype }} | unknown;
{%- endfor %}

  constructor( { {{ func_out_parms }} }: {{ inline_type|replace( ': ', '?: ' ) }} )
  {
{%- for field in query_filter_fields %}
    this.{{ field.name }} = {{ field.name }};
{%- endfor %}
  }
};
{% endif %}{% endif %}
""" )


def write_model( fp, prefix, model, service ):  # TODO: throw an error if a field is named constructor, toURL or toString or starts with "_"
  global class_buff

  id_field = None
  if model[ 'id_field_name' ] is not None:
    for field in model[ 'field_list' ]:
      if field[ 'name' ] == model[ 'id_field_name' ]:
        id_field = field
        break

    if id_field is None:
      raise ValueError( 'Unable to find id field "{0}" in model "{1}"({2})'.format( model[ 'id_field_name' ], model[ 'name' ], prefix ) )

  value_map = {
                'service': service,
                'prefix': prefix,
                'name': model[ 'name' ],
                'model_name': '{0}_{1}'.format( prefix, model[ 'name' ] ),
                'url': model[ 'url' ],
                'doc': model[ 'doc' ],
                'field_list': model[ 'field_list' ],
                'constant_map': model[ 'constant_map' ],
                'id_field': id_field,
                'list_filter_map': model[ 'list_filter_map' ],
                'not_allowed_verb_list': model[ 'not_allowed_verb_list' ],
                'query_filter_fields': model[ 'query_filter_fields' ],
                'query_sort_fields': model[ 'query_sort_fields' ],
                'action_list': model[ 'action_list' ],
                'model_uri_lookup_map': model_uri_lookup_map
              }

  fp.write( model_methods_template.render( **value_map ) )

  class_buff += model_class_template.render( **value_map )


def write_namespace( fp, prefix, namespace, service ):
  if prefix:
    prefix = '{0}_{1}'.format( prefix, namespace[ 'name' ] )
  else:
    prefix = namespace[ 'name' ]

  value_map = {
                'name': namespace[ 'name' ],
                'url': namespace[ 'url' ],
                'doc': namespace[ 'doc' ],
                'api_version': namespace[ 'api_version' ]
              }
  fp.write( ns_header.render( **value_map ) )

  for model in namespace[ 'model_list' ]:
    write_model( fp, prefix, model, service )

  for child in namespace[ 'namespace_list' ]:
    write_namespace( fp, prefix, child, service )

  fp.write( ns_footer.render( **value_map ) )


def prescan_model( prefix, model ):
  global model_uri_lookup_map

  model_uri_lookup_map[ model[ 'url' ] ] = '{0}_{1}'.format( prefix, model[ 'name' ] )


def prescan_namespace( prefix, namespace ):
  if prefix:
    prefix = '{0}_{1}'.format( prefix, namespace[ 'name' ] )
  else:
    prefix = namespace[ 'name' ]

  for model in namespace[ 'model_list' ]:
    prescan_model( prefix, model )

  for child in namespace[ 'namespace_list' ]:
    prescan_namespace( prefix, child )


def ts_render_func( wrk_dir, header_map, root ):
  header_map[ 'api_version' ] = root[ 'api_version' ]
  root[ 'name' ] = ''

  prescan_namespace( '', root )

  with open( os.path.join( wrk_dir, '{0}.ts'.format( header_map[ 'service' ] ) ), 'w' ) as fp:  # TODO: make sure this is filsystem safe
    fp.write( service_header.render( **header_map ) )
    write_namespace( fp, '', root, header_map[ 'service' ] )
    fp.write( service_footer.render( **header_map ) )

    fp.write( class_buff )
