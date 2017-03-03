# -*- encoding: utf-8 -*-
"""A module that provides utilities to test Nailgun entities."""
import inspect
import attr
from nailgun import entities
from rizza.helpers import inputs
from rizza.helpers.misc import (combination_list, product_list,
                                       map_field_inputs, dictionary_exclusion)


@attr.s()
class EntityTester(object):
    """This class implements methods useful in testing Nailgun entities.

    :param entity: Nailgun entity, or entity name. (Case sensitive)
    :param fields: Dictionary mapping nailgun field names to nailgun input
        methods.
    :param methods: Dictionary mapping nailgun method names to their methods.
    """

    entity = attr.ib()
    fields = attr.ib(default=None)
    methods = attr.ib(default=None)

    def prep(self, entity=None, field_exclude=None, method_exclude=None):
        """Gather information about the current entity."""
        if isinstance(self.entity, str):
            entity = self.entity
        if entity:
            elist = self.pull_entities()
            if entity in elist:
                self.entity = elist[entity]
            elif entity in elist.values():
                self.entity = entity

        if self.entity:
            self.fields = self.pull_fields(self.entity, exclude=field_exclude)
            self.methods = self.pull_methods(self.entity, exclude=method_exclude)

    def test_entity(self, task=None, depth=0):
        """Run an ehaustive test of the entity."""
        if not task:
            return None
        points = 0
        return points

    def brute_force(self, max_fields=None, max_inputs=None):
        """Create a list of tests for all entity permutations.

        :param max_fields: The limit of fields desired for testing.
        :param max_inputs: The limit of inputs desired for testing.

        :returns: A generator of EntityTestTask instances.
        """
        entity_name = self.entity.__name__

        input_list = self.pull_input_methods(exclude='long').keys()
        if not max_inputs:
            max_inputs = len(input_list)
        input_combos = product_list(input_list, max_inputs)

        method_combo_dict = {}
        for method in self.methods:
            method_combo_dict[method] = []
            args = self.pull_args(self.methods[method])
            method_combo_dict[method].extend(map_field_inputs(
                args, product_list(
                    input_list,
                    max_inputs if max_inputs <= len(args) else len(args)
                )))

        field_combo_list = combination_list(self.fields, max_fields)
        for combo in field_combo_list:
            # Map all the possible input combinations to the fields
            field_inputs = map_field_inputs(combo, input_combos)
            for fi_dict in field_inputs:
                for method in method_combo_dict:
                    for mc_dict in method_combo_dict[method]:
                        yield EntityTestTask(
                            entity=entity_name,
                            method=method,
                            field_dict=fi_dict,
                            arg_dict=mc_dict
                        )
        # return test_tasks

    @staticmethod
    def pull_entities(exclude=None):
        """Return a dictionary of nailgun entities."""
        edict = {entity: entities.__dict__[entity]
                 for entity in dir(entities)
                 if entity[0] != "_" and entity[0].istitle() and
                 not entity.isupper()}
        return dictionary_exclusion(edict, exclude)

    @staticmethod
    def pull_methods(entity=None, exclude=None):
        """Return a dictionary of methods belonging to an entity."""
        if entity:
            methods = inspect.getmembers(entity(), predicate=inspect.ismethod)
            mdict = {name: method
                     for name, method in methods
                     if "__" not in name}
        return dictionary_exclusion(mdict, exclude)

    @staticmethod
    def pull_fields(entity=None, exclude=None):
        """Return a dictionary of fields belonging to an entity's method."""
        if entity:
            return dictionary_exclusion(entity()._fields, exclude)

    @staticmethod
    def pull_args(method=None):
        """Return a list of args belonging to an entity's method."""
        if method:
            return [arg for arg in inspect.getargspec(method).args
                    if arg != 'self']

    @staticmethod
    def pull_input_methods(exclude=None):
        """Return a dictionary of input methods."""
        indict = {meth: inputs.__dict__[meth]
                  for meth in dir(inputs)
                  if "__" not in meth}
        return dictionary_exclusion(indict, exclude)


@attr.s(slots=True)
class EntityTestTask(object):
    """An Entity test task object that stores relevant information.

    :params entity_tuple: A tuple matching entity name to entity class.
    :params method_tuple: A tuple matching method name to method class.
    :params fields: A dict of method fields to pass in.
    :params inputs: A dict of field inputs to pass in.

    """

    entity = attr.ib(validator=attr.validators.instance_of(str))
    method = attr.ib(validator=attr.validators.instance_of(str))
    field_dict = attr.ib(validator=attr.validators.instance_of(dict))
    arg_dict = attr.ib(validator=attr.validators.instance_of(dict))

    def execute(self):
        """Execute the task.

        :returns: Either a valid nailgun entity or an exception object.
        """
        imeths = EntityTester.pull_input_methods()
        self.field_dict = {field: imeths.get(inpt, lambda: inpt)()
                           for field, inpt in self.field_dict.items()}
        self.arg_dict = {arg: imeths.get(inpt, lambda: inpt)() for arg, inpt
                         in self.arg_dict.items()}
        entity = EntityTester.pull_entities()[self.entity](**self.field_dict)
        # Todo: come up with a better way to return a logable format
        try:
            return getattr(entity, self.method)(**self.arg_dict)
        except TypeError as err:
            return err
        except Exception as err:
            return err


@attr.s(slots=True)
class MaIMap(object):
    """Provide a map between method fields and input functions.

    :params fields: A list of tuples (field name, field).
    :params inputs: A list of tuples (input name, input function).
    :params mai_map: A pre-existing map (optional).
    """

    fields = attr.ib(validator=attr.validators.instance_of(list))
    inputs = attr.ib(validator=attr.validators.instance_of(list))
    mai_map = attr.ib(default=[])

    def create_map(self):
        """Call this immediately after creating a new instance."""
        self.mai_map = [[None for x in self.x_labels] for y in self.y_labels]

    def point(self, x, y, value=None):
        """Map must be initialized before using this method."""
        if not self.mai_map:
            self.create_map()
        if value:
            self.mai_map[x][y] = value
        return {
            'x label': self.x_labels[x],
            'y label': self.y_labels[y],
            'value': self.mai_map[x][y]
        }

    @property
    def x_labels(self):
        """Return the labels on the x axis."""
        return [label for label, _ in self.fields]

    @property
    def y_labels(self):
        """Return the labels on the y axis."""
        return [label for label, _ in self.inputs]