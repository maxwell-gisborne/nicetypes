class Option:
    something: bool

    def Some(something):
        option = object.__new__(Option)
        option.something = True
        option.value = something
        return option

    def Nothing():
        option = object.__new__(Option)
        option.something = False
        return option

    def or_else(self, default):
        if self.something:
            return self.value
        return default

    def map(self, fun, *args, **kwargs):
        if self.something:
            return Option.Some(fun(self.value, *args, **kwargs))
        return self

    def __repr__(self):
        if self.something:
            return f'Some({self.value})'
        return 'Nothing'

    def bind(self, fun, *args, **kwargs):
        if not self.something:
            return self
        return fun(self.value, *args, **kwargs)


Option.Nothing = Option.Nothing()

class Result:
    error: bool
    Exception = Exception

    def Ok(value):
        result = object.__new__(Result)
        result.error = False
        result._value = value
        return result

    def Error(error):
        result = object.__new__(Result)
        result.error = True
        result._error = error
        return result

    def map(self, fun, *args, **kwargs):
        if self.error:
            return self
        return Result.Ok(fun(self._value, *args, **kwargs))

    def bind(self, fun, *args, **kwargs):
        if self.error:
            return self
        return fun(self._value, *args, **kwargs)

    def maperr(self, fun, *args, **kwargs):
        if not self.error:
            return self
        return Result.Error(fun(self._error, *args, **kwargs))

    def unwrap(self):
        if self.error:
            raise self.Exception(self._error)
        return self._value

    def with_exception(self, exp):
        if self.error:
            result = Result.Error(self._error)
        else:
            result = Result.Ok(self._value)
        result.Exception = exp
        return result

    def or_else(self, default):
        if self.error:
            return default
        return self._value

    def __repr__(self):
        if self.error:
            return f'Error({self._error})'
        return f'Ok({self._value})'


def Enum(cls):
    variants_count = 0
    for name, given_type in cls.__annotations__.items():

        if given_type is Scailer_Variant:
            if given_id := cls.__dict__.get(name):
                assert given_id >= variants_count, (name, given_id, variants_count)
                variants_count = given_id

            variant = object.__new__(cls)
            variant._vid = variants_count
            variant._name = name

            variant._vtype = Scailer_Variant
            setattr(cls, name, variant)
            variants_count += 1

        if type(given_type) is Struct_Variant:
            if given_id := cls.__dict__.get(name):
                assert given_id >= variants_count, (name, given_id, variants_count)
                variants_count = given_id

            constructor = given_type.create_constructor(cls, name, variants_count)
            setattr(cls, name, constructor)

            variants_count += 1

    def display(variant) -> str:
        if variant._vtype is Scailer_Variant:
            return f'{cls.__qualname__}.{variant._name}'
        if variant._vtype is Struct_Variant:
            return f'{cls.__qualname__}.{variant._name}({variant._svariant_sig})'
        raise Exception('unknown variant type')
    setattr(cls, '__repr__', display)

    def to_string(variant) -> str:
        if variant._vtype is Scailer_Variant:
            return variant._name
        raise Exception('unknown variant type')
    setattr(cls, '__str__', to_string)

    def eq(variant1, variant2) -> bool:
        if variant1._vtype != variant2._vtype:
            return False

        if variant1._vtype is Scailer_Variant:
            return variant1._vid == variant2._vid

        raise Exception('unknown variant type')

    return cls


Scailer_Variant = object()


class Struct_Variant:
    def __init__(self, *args, **kwargs):
        self.tuple_args = args
        self.kwargs = kwargs

    def create_constructor(self, cls, name: str, vid=int):
        'This is some spooky shit, dont know another way of doing it'

        tuple_vars = [(f'_{i}', type) for i, type in enumerate(self.tuple_args)]
        tuple_setters = '\n    '.join([f'variant.{arg} = {arg}' for arg, type in tuple_vars])
        tuple_setters += '\n    ' + 'variant.tuple = (' + ', '.join([var[0] for var in tuple_vars]) + ')'
        tuple_args = ', '.join([name + ': ' + type.__name__ for name, type in tuple_vars])

        kw_args = '' if len(self.kwargs) == 0 else ', '.join([name + ': ' + type.__name__ for name, type in self.kwargs.items()])
        tp_kw_seperator = ', ' if (len(tuple_args) != 0) and (len(kw_args) != 0) else ''
        kw_setters = '\n    '.join([f'variant.{arg} = {arg}' for arg, type in self.kwargs.items()])
        kw_setters += '\n    ' + 'variant.dict = {' + ', '.join([f'"{arg}": {arg}' for arg in self.kwargs]) + '}'

        t_varlist_quote = [tvar[0] for tvar in tuple_vars]
        k_varlist_quote = list(self.kwargs)

        t_varlist = '[' + ','.join([v for v in t_varlist_quote]) + ']'
        k_varlist = '[' + ','.join([v for v in k_varlist_quote]) + ']'

        sig = f'{tuple_args}{tp_kw_seperator}{kw_args}'

        exec_locals = dict(constructor=None,
                           cls=cls,
                           name=name,
                           vid=vid,
                           Struct_Variant=Struct_Variant)


        exec_string = f'''
def constructor({sig}) -> cls:
    variant = object.__new__(cls)
    variant._name = name
    variant._vtype = Struct_Variant
    variant._vid = vid

    k_varlist_quote = {k_varlist_quote}
    k_varlist = {k_varlist}
    t_varlist = {t_varlist}

    variant._svariant_sig = ', '.join(str(v) for v in t_varlist)
    variant._svariant_sig += "{tp_kw_seperator}"
    variant._svariant_sig += ', '.join(str(k) + ' = ' + str(v) for k, v in zip(k_varlist_quote, k_varlist))
    {tuple_setters}
    {kw_setters}
    return variant
'''

        exec(exec_string, exec_locals)
        constructor = exec_locals['constructor']
        constructor.__doc__ = f'Constructor for {cls.__qualname__}.{name}({sig})'
        return constructor


@Enum
class Color:
    Red: Scailer_Variant
    Green: Scailer_Variant = 10
    Blue: Scailer_Variant

    RGB: Struct_Variant(int, int, int)
    RGBA: Struct_Variant(int, int, int, alpha = float)