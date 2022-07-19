import os
from jinja2 import Environment

all_upper = ( 'ip', 'id', 'uuid', 'ttl', 'url', 'http', 'https' )


def goName( word ):
  return ''.join( x.upper() if x in all_upper else x.capitalize() for x in word.split( '_' ) )


include_list = []
prefix_list = []


def goType( cinpType ):
  global include_list

  prefix = ''
  if cinpType.get( 'is_array', False ):
    prefix = '[]'

  if cinpType[ 'type' ] == 'DateTime':
    include_list.append( '"time"' )
    return prefix + 'time.Time'

  elif cinpType[ 'type' ] == 'Map':
    return prefix + 'map[string]interface{}'

  elif cinpType[ 'type' ] == 'Integer':
    return prefix + 'int'

  elif cinpType[ 'type' ] == 'Boolean':
    return prefix + 'bool'

  else:
    return prefix + 'string'


def goEmptyVal( cinpType ):
  is_array = cinpType.get( 'is_array', False )

  if cinpType[ 'type' ] == 'DateTime':
    if is_array:
      return '[]time.Time{}'
    else:
      return '0'

  elif cinpType[ 'type' ] == 'Map':
    return 'nil'

  elif cinpType[ 'type' ] == 'Integer':
    if is_array:
      return '[]int{}'
    else:
      return '0'

  elif cinpType[ 'type' ] == 'Boolean':
    if is_array:
      return '[]bool{}'
    else:
      return 'false'

  else:
    if is_array:
      return '[]string{}'
    else:
      return '""'


def goNewVal( cinpType ):
  if isinstance( cinpType, str ):
    is_array = False

  else:
    is_array = cinpType.get( 'is_array', False )
    cinpType = cinpType[ 'type' ]

  if cinpType == 'DateTime':
    if is_array:
      return '[]time.Time{}'
    else:
      return '0'

  elif cinpType == 'Map':
    if is_array:
      return '[]map[string]interface{}{}'
    else:
      return 'map[string]interface{}{}'

  elif cinpType == 'Integer':
    if is_array:
      return '[]int{}'
    else:
      return '0'

  elif cinpType == 'Boolean':
    if is_array:
      return '[]bool{}'
    else:
      return 'false'

  else:
    if is_array:
      return '[]string{}'
    else:
      return '""'


def goStringId( cinpType ):
  global include_list

  if cinpType.get( 'is_array', False ):
    raise ValueError( 'Can not string convert an array' )

  if cinpType[ 'type' ] == 'DateTime':
    raise ValueError( 'Can not use DateTime as an Id' )

  elif cinpType[ 'type' ] == 'Map':
    raise ValueError( 'Can not use Map as an Id' )

  elif cinpType[ 'type' ] == 'Integer':
    include_list.append( '"strconv"' )
    return 'strconv.FormatInt(int64(id), 10)'

  elif cinpType[ 'type' ] == 'Boolean':
    include_list.append( '"strconv"' )
    return 'strconv.FormatBool(id)'

  else:
    return 'id'


def strip_quotes( value ):
  if value[0] == '"':
    return value[1:-1]

  return value


env = Environment()
env.filters[ 'goname' ] = goName
env.filters[ 'gotype' ] = goType
env.filters[ 'goemptyval' ] = goEmptyVal
env.filters[ 'gonewval' ] = goNewVal
env.filters[ 'gostrid' ] = goStringId
env.filters[ 'capitalize' ] = lambda x: x[0].upper() + x[1:]
service_template = env.from_string( """// Package {{ service }} - Automatically generated by cinp-codegen from {{ url }} at {{ timestamp }}
package {{ service }}

import (
	"fmt"

	cinp "github.com/cinp/go"
)

// {{ service|title }} from {{ url }}
type {{ service|title }} struct {
	cinp *cinp.CInP
}

// New{{ service|title }} creates and returns a new {{ service|title }}
func New{{ service|title }}(host string, proxy string) (*{{ service|title }}, error) {
	var err error
	s := {{ service|title }}{}
	s.cinp, err = cinp.NewCInP(host, "{{ root_path }}", proxy)
	if err != nil {
		return nil, err
	}
{% for prefix in prefix_list %}
	register{{ prefix }}(s.cinp){% endfor %}

	APIVersion, err := s.GetAPIVersion("{{ root_path }}")
	if err != nil {
		return nil, err
	}

	if APIVersion != "{{ api_version }}" {
		return nil, fmt.Errorf("API version mismatch.  Got '%s', expected '{{ api_version }}'", APIVersion)
	}

	return &s, nil
}

// GetAPIVersion Get the API version number for the Namespace at the URI
func (s *{{ service|title }}) GetAPIVersion(uri string) (string, error ) {
	r, t, err := s.cinp.Describe(uri)
	if err != nil {
		return "", err
	}

	if t != "Namespace" {
		return "", fmt.Errorf("Excpected a Namespace got '%s'", t)
	}

	return r.APIVersion, nil
}

// SetHeader sets a request header
func (s *{{ service|title }}) SetHeader(name string, value string) {
	s.cinp.SetHeader(name, value )
}
""" )  # noqa

ns_template = env.from_string( """// Package {{ service }} - (version: "{{ api_version }}") - Automatically generated by cinp-codegen from {{ url }} at {{ timestamp }}{% if doc %}
 /*
{{ doc }}
*/{% endif %}
package {{ service }}

import ({% for item in include_list %}
	{{ item }}{% endfor %}
)

""" )  # noqa

model_template = env.from_string( """{% set model_name = prefix|title + name -%}
// {{ model_name }} - Model {{ name }}({{ url }})
/*
{{ doc }}
*/
type {{ model_name }} struct {
	cinp.BaseObject
	cinp *cinp.CInP{% for field in field_list %}
	{{ field.name|goname }} {{ field|gotype }} `json:"{{ field.name }}"`{% endfor %}
}

// AsMap returns a map[string]interface{} that is required for create and update
func (object *{{ model_name }}) AsMap(isCreate bool) *map[string]interface{} {
	if isCreate {
		return &map[string]interface{}{ {% for field in field_list %}{% if field.mode in ( 'RW', 'RC' ) %}
			"{{ field.name }}": object.{{ field.name|goname }},{% endif %}{% endfor %}
		}
	}
	return &map[string]interface{}{ {% for field in field_list %}{% if field.mode in ( 'RW', ) %}
		"{{ field.name }}": object.{{ field.name|goname }},{% endif %}{% endfor %}
	}
}

// {{ model_name }}New - Make a new object of Model {{ name }}
func (service *{{ service|title }}) {{ model_name }}New() *{{ model_name }} {
	return &{{ model_name }}{cinp: service.cinp}
}{% if id_field %}

// {{ model_name }}NewWithID - Make a new object of Model {{ name }}
func (service *{{ service|title }}) {{ model_name }}NewWithID(id {{ id_field|gotype }}) *{{ model_name }} {
	result := {{ model_name }}{cinp: service.cinp}
	result.SetID("{{ url }}:" + {{ id_field|gostrid }} + ":")
	return &result
}
{% endif %}{% if 'GET' not in not_allowed_verb_list and id_field %}
// {{ model_name }}Get - Get function for Model {{ name }}
func (service *{{ service|title }}) {{ model_name }}Get(id {{ id_field|gotype }}) (*{{ model_name }}, error) {
	object, err := service.cinp.Get("{{ url }}:" + {{ id_field|gostrid }} + ":")
	if err != nil {
		return nil, err
	}
	result := (*object).(*{{ model_name }})
	result.cinp = service.cinp

	return result, nil
}
{% endif %}{% if 'CREATE' not in not_allowed_verb_list %}
// Create - Create function for Model {{ name }}
func (object *{{ model_name }}) Create() error {
	if err := object.cinp.Create("{{ url }}", object); err != nil {
		return err
	}

	return nil
}
{% endif %}{% if 'UPDATE' not in not_allowed_verb_list and id_field %}
// Update - Update function for Model {{ name }}
func (object *{{ model_name }}) Update(fieldList []string) error {
	if err := object.cinp.Update(object, fieldList); err != nil {
		return err
	}

	return nil
}
{% endif %}{% if 'DELETE' not in not_allowed_verb_list and id_field %}
// Delete - Delete function for Model {{ name }}
func (object *{{ model_name }}) Delete() error {
	if err := object.cinp.Delete(object); err != nil {
		return err
	}

	return nil
}
{% endif %}{% if 'LIST' not in not_allowed_verb_list %}
// {{ model_name }}ListFilters - Return a slice of valid filter names {{ name }}
func (service *{{ service|title }}) {{ model_name }}ListFilters() [{{ list_filter_map_names|length }}]string {
  return [{{ list_filter_map_names|length }}]string{ {{ ", ".join( list_filter_map_names ) }} }
}

// {{ model_name }}List - List function for Model {{ name }}
func (service *{{ service|title }}) {{ model_name }}List(filterName string, filterValues map[string]interface{}) (<-chan *{{ model_name }}, error) {
{%- if query_filter_fields or query_sort_fields %}
	if filterName == "_query_" {
		goto good
	}
{% endif %}
	if filterName != "" {
		for _, item := range service.{{ model_name }}ListFilters() {
			if item == filterName {
				goto good
			}
		}
		return nil, fmt.Errorf("Filter '%s' is invalid", filterName)
	}
	good:

	in := service.cinp.ListObjects("{{ url }}", reflect.TypeOf({{ model_name }}{}), filterName, filterValues, 50)
	out := make(chan *{{ model_name }})
	go func() {
		defer close(out)
		for v := range in {
			v.(*{{ model_name }}).cinp = service.cinp
			out <- v.(*{{ model_name }})
		}
	}()
	return out, nil
}
{% endif %}{% if 'CALL' not in not_allowed_verb_list %}
{% for action in action_list %}{% if action.static %}{% set funcname = model_name + "Call" + action.name|capitalize %}{% else %}{% set funcname = "Call" + action.name|capitalize %}{% endif %}
// {{ funcname }} calls {{ action.name }}{% if action.doc %}
/*
{{ action.doc }}
*/{% endif %}{% set parm_list = [] %}{% for parm in action.paramater_list %}{{ parm_list.append( parm.name|goname + " " + parm|gotype )|default( '', True ) }}{% endfor %}
func ({% if action.static %}service *{{ service|title }}{% else %}object *{{ model_name }}{% endif %}) {{ funcname }}({{ parm_list|join(", ") }}) ({% if action.return_type %}{{ action.return_type|gotype }}, {% endif %}error) {
	args := map[string]interface{}{
{% for parm in action.paramater_list %}		"{{ parm.name }}": {{ parm.name|goname }},
{% endfor %}	}{% if action.static %}
	uri := "{{ action.url }}"{% else %}
	_, _, _, ids, _, err := object.cinp.Split(object.GetID())
	if err != nil {
		return {% if action.return_type %}{{ action.return_type|goemptyval }}, {% endif %}err
	}
	uri, err := object.cinp.UpdateIDs("{{ action.url }}", ids)
	if err != nil {
		return {% if action.return_type %}{{ action.return_type|goemptyval }}, {% endif %}err
	}{% endif %}

	result := {% if action.return_type %}{{ action.return_type|gonewval }}{% else %}""{% endif %}

	if err := {% if action.static %}service{% else %}object{% endif %}.cinp.Call(uri, &args, &result); err != nil {
		return {% if action.return_type %}{{ action.return_type|goemptyval }}, {% endif %}err
	}

	return {% if action.return_type %}result, {% endif %}nil
}
{% endfor %}{% endif %}""")  # noqa

register_template = env.from_string( """func register{{ prefix }}(cinp *cinp.CInP) { {%- for model in model_list %}
	cinp.RegisterType("{{ model.url }}", reflect.TypeOf((*{{ prefix|title + model.name }})(nil)).Elem()){% endfor %}
}

""" )  # noqa


def service( wrk_dir, header_map ):
  open( os.path.join( wrk_dir, 'service.go' ), 'w' ).write( service_template.render( prefix_list=prefix_list, **header_map ) )


def do_namespace( wrk_dir, header_map, prefix, namespace ):
  global include_list, prefix_list

  if prefix:
    filename = 'ns_{0}{1}.go'.format( prefix, namespace[ 'name' ] )  # TODO: make sure this is filesystem safe
    prefix = '{0}{1}'.format( prefix, namespace[ 'name' ] )
  else:
    filename = 'ns_{0}.go'.format( namespace[ 'name' ] )  # TODO: make sure this is filesystem safe
    prefix = namespace[ 'name' ]

  include_list = []

  if namespace[ 'model_list' ]:
    include_list.append( '"reflect"' )
    include_list.append( 'cinp "github.com/cinp/go"' )

  value_map = {
                'service': header_map[ 'service' ],
                'timestamp': header_map[ 'timestamp' ],
                'name': namespace[ 'name' ],
                'url': namespace[ 'url' ],
                'doc': namespace[ 'doc' ],
                'api_version': namespace[ 'api_version' ]
              }

  with open( os.path.join( wrk_dir, filename ), 'w' ) as fp:
    model_buff = ''

    for model in namespace[ 'model_list' ]:
      model_buff += render_model( header_map[ 'service' ], prefix, model )

    include_list = sorted( list( set( include_list ) ), key=strip_quotes )

    fp.write( ns_template.render( include_list=include_list, **value_map ) )
    fp.write( model_buff )

    if namespace[ 'model_list' ]:
      fp.write( register_template.render( model_list=namespace[ 'model_list' ], prefix=prefix ) )
      prefix_list.append( prefix )

  for child in namespace[ 'namespace_list' ]:
    do_namespace( wrk_dir, header_map, prefix, child )


def render_model( service, prefix, model ):
  global include_list

  if 'LIST' not in model[ 'not_allowed_verb_list' ]:
    include_list.append( '"fmt"' )

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
                'url': model[ 'url' ],
                'doc': model[ 'doc' ],
                'field_list': model[ 'field_list' ],
                'constant_map': model[ 'constant_map' ],
                'id_field': id_field,
                'not_allowed_verb_list': model[ 'not_allowed_verb_list' ],
                'query_filter_fields': model[ 'query_filter_fields' ],
                'query_sort_fields': model[ 'query_sort_fields' ],
                'list_filter_map_names': [ '"{0}"'.format( i ) for i in model[ 'list_filter_map' ].keys() ],
                'action_list': model[ 'action_list' ]
              }

  return model_template.render( **value_map )


def go_render_func( wrk_dir, header_map, root ):
  header_map[ 'api_version' ] = root[ 'api_version' ]
  root[ 'name' ] = ''

  do_namespace( wrk_dir, header_map, '', root )
  service( wrk_dir, header_map )
