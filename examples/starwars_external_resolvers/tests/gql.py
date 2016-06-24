import decimal
from graphql.execution import ExecutionResult, execute
from graphql.validation import validate
from graphql.language import ast
from graphql.language.printer import print_ast
from graphql.type import GraphQLField



def selections(*fields):
    for field in fields:
        field_query = None
        if isinstance(field, FieldQuery):
            field_query = field
        elif isinstance(field, GraphQLField):
            field_query = FieldQuery(field)

        assert field_query, 'Received incompatible field: {}'.format(field)

        yield field_query.ast


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
    def __init__(self, schema):
        self.schema = schema

    def query(self, *fields):
        return ast.Document(
            definitions=[ast.OperationDefinition(
                operation='query',
                selection_set=ast.SelectionSet(
                    selections=list(selections(*fields))
                )
            )]
        )

    def var(self, name):
        return ast.Variable(name=name)

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

    def __call__(self, field, **args):
        '''for nested queries'''
        return FieldQuery(field).args(**args)
