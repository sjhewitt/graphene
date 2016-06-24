import decimal
from graphql.execution import ExecutionResult, execute
from graphql.validation import validate
from graphql.language import ast
from graphql.language.printer import print_ast
from graphql.type import GraphQLField
from graphql.language.parser import parse
from graphql.language.source import Source


def selections(*fields):
    for field in fields:
        query = None
        if isinstance(field, FieldQuery):
            query = field
        elif isinstance(field, GraphQLField):
            query = FieldQuery(field)
        assert query, 'Received incompatible query field: {}'.format(field)

        yield query.ast


def get_value(value):
    if isinstance(value, (unicode, str)):
        return ast.StringValue(value=value)
    elif isinstance(value, bool):
        return ast.BooleanValue(value=value)
    elif isinstance(value, (float, decimal.Decimal)):
        return ast.FloatValue(value=value)
    elif isinstance(value, int):
        return ast.IntValue(value=value)
    return None


class FieldQuery(object):
    def __init__(self, field):
        self.field = field
        self.ast_field = ast.Field(name=ast.Name(value=field.name), arguments=[])
        self.selection_set = None

    def get(self, *fields):
        if not self.ast_field.selection_set:
            self.ast_field.selection_set = ast.SelectionSet(selections=[])
        self.ast_field.selection_set.selections.extend(selections(*fields))
        return self

    def args(self, **args):
        for name, value in args.items():
            arg = self.field.args.get(name)
            value = arg.type.serialize(value)
            self.ast_field.arguments.append(
                ast.Argument(
                    name=ast.Name(value=name),
                    value=get_value(value)
                )
            )
        return self

    @property
    def ast(self):
        return self.ast_field

    def __str__(self):
        return print_ast(self.ast_field)


class GQL(object):
    def __init__(self, request_string):
        if isinstance(request_string, (str, unicode)):
            source = Source(request_string, 'GraphQL request')
            self.ast = parse(source)
            assert not args
        else:
            raise Exception('Received incompatible request "{}".'.format(request_string))

    @staticmethod
    def field(field, **args):
        if isinstance(field, GraphQLField):
            return FieldQuery(field).args(**args)
        elif isinstance(field, FieldQuery):
            return field

        raise Exception('Received incompatible query field: "{}".'.format(field))

    @staticmethod
    def query(*fields):
        return ast.Document(
            definitions=[ast.OperationDefinition(
                operation='query',
                selection_set=ast.SelectionSet(
                    selections=list(selections(*fields))
                )
            )]
        )

    @staticmethod
    def var(name):
        return ast.Variable(name=name)


gql = GQL


class Client(object):
    def __init__(self, schema=None):
        self.schema = schema

    def validate(self, document):
        validation_errors = validate(self.schema, document)
        if validation_errors:
            raise validation_errors[0]

    def execute(self, document):
        self.validate(document)
        result = execute(
            self.schema,
            document,
        )
        if result.errors:
            raise result.errors[0]
        return result.data
