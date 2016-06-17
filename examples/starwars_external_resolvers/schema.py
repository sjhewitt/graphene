import graphene
from graphene import resolve_only_args
from graphene.types.resolvers_schema import ResolversSchema

from .data import get_character, get_droid, get_hero, get_human


class Episode(graphene.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6


class Character(graphene.Interface):
    id = graphene.ID()
    name = graphene.String()
    friends = graphene.List(lambda: Character)
    appears_in = graphene.List(Episode)


class Human(graphene.ObjectType, Character):
    home_planet = graphene.String()


class Droid(graphene.ObjectType, Character):
    primary_function = graphene.String()


class Query(graphene.ObjectType):
    hero = graphene.Field(Character,
                          episode=Episode()
                          )
    human = graphene.Field(Human,
                           id=graphene.String()
                           )
    droid = graphene.Field(Droid,
                           id=graphene.String()
                           )


@resolve_only_args
def resolve_friends(root):
    # The character friends is a list of strings
    return [get_character(f) for f in root.friends]


@resolve_only_args
def resolve_hero(root, episode=None):
    return get_hero(episode)


@resolve_only_args
def resolve_human(root, id):
    return get_human(id)


@resolve_only_args
def resolve_droid(root, id):
    return get_droid(id)


schema = ResolversSchema(query=Query, resolvers={
    Human: {
        'friends': resolve_friends
    },
    Droid: {
        'friends': resolve_friends
    },
    Query: {
        'hero': resolve_hero,
        'human': resolve_human,
        'droid': resolve_droid
    }
})
