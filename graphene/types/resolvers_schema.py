import copy
from collections import Iterable, OrderedDict, defaultdict
from functools import reduce

from graphql.utils.type_comparators import is_equal_type, is_type_sub_type_of
from graphql.type.definition import (GraphQLInputObjectType, GraphQLInterfaceType,
                                     GraphQLList, GraphQLNonNull, GraphQLObjectType,
                                     GraphQLUnionType)
from graphql.type.directives import (GraphQLDirective, GraphQLIncludeDirective,
                                     GraphQLSkipDirective)
from graphql.type.introspection import IntrospectionSchema

from .schema import Schema
from ..generators.definitions import GrapheneObjectType
from .field import Field
from ..utils.get_graphql_type import get_graphql_type


def fields_with_resolvers(fields, resolvers):
    new_fields = OrderedDict()
    if callable(fields):
        fields = fields()
    for name, field in fields.items():
        new_field = Field.copy_and_extend(field)
        new_resolver = resolvers.get(new_field.attname or new_field.name)
        new_field.resolver = new_resolver
        new_fields[name] = new_field
    return new_fields


class GraphQLObjectTypeWithResolvers(GrapheneObjectType):
    def __init__(self, original_type, resolvers):
        graphene_type = getattr(original_type, 'graphene_type', None)
        self.original_type = original_type
        self.resolvers = resolvers
        super(GraphQLObjectTypeWithResolvers, self).__init__(
            graphene_type=graphene_type,
            name=original_type.name,
            fields=fields_with_resolvers(original_type._fields, resolvers),
            interfaces=original_type._provided_interfaces,
            is_type_of=original_type.is_type_of,
            description=original_type.description,
        )

    def __eq__(self, type):
        return self.original_type == type


class ResolversSchema(Schema):
    """
    ResolversSchema Definition
    A Schema is created by supplying the root types of each type of operation, query and mutation (optional).
    A schema definition is then supplied to the validator and executor.
    Example:
        MyAppSchema = ResolversSchema(
            query=MyAppQueryRootType,
            mutation=MyAppMutationRootType,
            resolvers={
                MyAppQueryRootType: {
                    'friends': get_friends
                }
            }
        )
    """
    def __init__(self, query=None, mutation=None, subscription=None, directives=None, types=None, executor=None, resolvers=None):
        assert resolvers, 'ResolversSchema needs to recieve a tuple of types, resolvers'
        self.resolvers = {get_graphql_type(type):value for type, value in resolvers.items()}
        if query:
            query = self.type_with_resolvers(get_graphql_type(query))
        if mutation:
            mutation = self.type_with_resolvers(get_graphql_type(mutation))
        if subscription:
            subscription = self.type_with_resolvers(get_graphql_type(subscription))
        super(ResolversSchema, self).__init__(
            query=query,
            mutation=mutation,
            subscription=subscription,
            directives=directives,
            types=types,
            executor=executor)

    def _build_type_map(self, _types):
        types = [
            self.get_query_type(),
            self.get_mutation_type(),
            self.get_subscription_type(),
            IntrospectionSchema
        ]
        if _types:
            types += _types

        type_map = reduce(self._type_map_reducer, types, OrderedDict())
        return type_map

    def type_with_resolvers(self, type):
        return type_with_resolvers(type, self.resolvers.get(type, {}))

    def _type_map_reducer(self, reduced_map, type):
        if not type:
            return reduced_map

        if isinstance(type, GraphQLList) or isinstance(type, GraphQLNonNull):
            return self._type_map_reducer(reduced_map, type.of_type)

        if type.name in reduced_map:
            assert reduced_map[type.name] == type, (
                'Schema must contain unique named types but contains multiple types named "{}".'
            ).format(type.name)

            return reduced_map

        if isinstance(type, GraphQLObjectType):
            type = self.type_with_resolvers(type)
        reduced_map[type.name] = type

        if isinstance(type, (GraphQLUnionType)):
            for t in type.get_types():
                reduced_map = self._type_map_reducer(reduced_map, t)

        if isinstance(type, GraphQLObjectType):
            for t in type.get_interfaces():
                reduced_map = self._type_map_reducer(reduced_map, t)

        if isinstance(type, (GraphQLObjectType, GraphQLInterfaceType, GraphQLInputObjectType)):
            field_map = type.get_fields()
            for field in field_map.values():
                args = getattr(field, 'args', None)
                if args:
                    field_arg_types = [arg.type for arg in field.args]
                    for t in field_arg_types:
                        reduced_map = self._type_map_reducer(reduced_map, t)

                reduced_map = self._type_map_reducer(reduced_map, getattr(field, 'type', None))

        return reduced_map


def type_with_resolvers(type, resolvers):
    return GraphQLObjectTypeWithResolvers(
        original_type=type,
        resolvers=resolvers
    )
