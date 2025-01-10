import datetime

class Model: pass
class Field: pass
class OnDelete: pass
class CASCADE_(OnDelete): pass
class PROTECT_(OnDelete): pass
class SET_NULL_(OnDelete): pass
class SET_DEFAULT_(OnDelete): pass
class NO_ACTION_(OnDelete): pass

CASCADE = CASCADE_()
PROTECT = PROTECT_()
SET_NULL = SET_NULL_()
SET_DEFAULT = SET_DEFAULT_()
NO_ACTION = NO_ACTION_()

class CharField(Field):
    def __init__(self, max_length:int, unique:bool=False, primary_key:bool=False, null:bool=True):
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(max_length, int):
            self.max_length = max_length
            if 0 < max_length < 256:
                self.max_length = max_length
            else: raise ValueError(
            "Invalid max_length: max_length should be an integer between (1-255)"
            )
        else: raise TypeError(
            "Invalid max_length: max_length should be an integer"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )

    def __sqltype__(self):
        return f"VARCHAR({self.max_length})"

class AuthorizedUser(Model): pass

class TextField(Field):
    def __init__(self, unique:bool=False, primary_key:bool=False, null:bool=True):
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
    
    def __sqltype__(self):
        return "TEXT"

class IntegerField(Field):
    def __init__(self, default:int=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, int):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
    
    def __sqltype__(self):
        return "INTEGER"

class BigIntegerField(Field):
    def __init__(self, default:int=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, int):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )

    def __sqltype__(self):
        return "INTEGER" # !!! SqLite has no distinct BIGINT datatype, yet BIGINT is used as an alias for INTEGER

class PositiveIntegerField(Field):
    def __init__(self, default:int=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, int):
            if default > 0:
                self.default = default
                self._default = True
            else: raise ValueError(
                "default should be an integer bigger than zero (PositiveIntegerField)"
            )
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )

    def __sqltype__(self, col_name):
        return f"INTEGER CHECK ({col_name} > 0)"

class FloatField(Field):
    def __init__(self, default:int=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.default = primary_key
        else: raise TypeError(
            "Invalid primary_key: default should be a boolean"
        )
        if isinstance(default, int):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )

    def __init__(self):
        return "FLOAT"

class DecimalField(Field):
    def __init__(self, default:int=None, null:bool=True, unique:bool=False, max_digits:int=10, decimal_places:int=2, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, int):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
        if isinstance(max_digits, int):
            if 3 < max_digits < 51:
                self.max_digits = max_digits
            else: raise ValueError(
                "max_digits should be an integer between (4-50)"
            )
        else: raise TypeError(
            "Invalid max_digits: max_digits should be an integer"
        )
        if isinstance(decimal_places, int):
            if decimal_places < self.max_digits:
                self.decimal_places = decimal_places
            else: raise ValueError(
                "decimal_places should be an integer smaller than max_digits (default max_digits=10)"
            )
        else: raise TypeError(
            "Invalid decimal_places: decimal_places should be an integer"
        )

    def __sqltype__(self):
        return f"DECIMAL({self.max_digits}, {self.decimal_places})"

class BooleanField(Field):
    def __init__(self, default:bool=None, null:bool=False):
        self.primary_key = False
        self.unique = False
        if default == None:
            self.default == None
        elif default in (True, False):
            self.default = default
        else: raise TypeError(
            "Invalid default: default should be a boolean"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
    def __sqltype__(self):
        return "BOOLEAN"

class AutoField(Field):
    def __init__(self, primary_key:bool=False):
        self.null = False
        self.unique = False
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )

    def __sqltype__(self, remove_auto=False):
        if remove_auto:
            return "INTEGER"
        else: # AUTOINCREMENT Deprecated (since we're using sqlite only)
            return "INTEGER"

class DateField(Field):
    def __init__(self, auto_now:bool=False, auto_now_add:bool=False, default:datetime.date=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, datetime.datetime):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
        if isinstance(auto_now, bool):
            self.auto_now = auto_now
        else: raise TypeError(
            "Invalid auto_now: auto_now should be a boolean value"
        )
        if isinstance(auto_now_add, bool):
            self.auto_now_add = auto_now_add
        else: raise TypeError(
            "Invalid auto_now_add: auto_now_add should be a boolean value"
        )

    def check_auto(self):
        if self.auto_now_add:
            return " DEFAULT CURRENT_DATE"
        else: return ""

    def __sqltype__(self):
        return f"DATE{self.check_auto()}"

class TimeField(Field):
    def __init__(self, auto_now:bool=False, auto_now_add:bool=False, default:datetime.time=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, datetime.time):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
        if isinstance(auto_now, bool):
            self.auto_now = auto_now
        else: raise TypeError(
            "Invalid auto_now: auto_now should be a boolean value"
        )
        if isinstance(auto_now_add, bool):
            self.auto_now_add = auto_now_add
        else: raise TypeError(
            "Invalid auto_now_add: auto_now_add should be a boolean value"
        )

    def check_auto(self):
        if self.auto_now_add:
            return " DEFAULT CURRENT_TIME"
        else: return ""

    def __sqltype__(self):
        return f"TIME{self.check_auto()}"

class DateTimeField(Field):
    def __init__(self, auto_now:bool=False, auto_now_add:bool=False, default:datetime.datetime=None, null:bool=True, unique:bool=False, primary_key:bool=False):
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if isinstance(default, datetime.datetime):
            self.default = default
            self._default = True
        elif not default:
            self._default = False
            self.default = None
        else: raise TypeError(
            "Invalid default: default should be an integer or a NoneType Value"
        )
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
        if isinstance(auto_now, bool):
            self.auto_now = auto_now
        else: raise TypeError(
            "Invalid auto_now: auto_now should be a boolean value"
        )
        if isinstance(auto_now_add, bool):
            self.auto_now_add = auto_now_add
        else: raise TypeError(
            "Invalid auto_now_add: auto_now_add should be a boolean value"
        )

    def check_auto(self):
        if self.auto_now_add:
            return " DEFAULT CURRENT_TIMESTAMP"
        else: return ""

    def __sqltype__(self):
        return f"DATETIME{self.check_auto()}"

class ForeignKey(Field):
    def __init__(self, to_table:Model, on_delete:OnDelete=CASCADE, default=None, null:bool=True, unique:bool=False):
        if isinstance(null, bool):
            self.null = null
        else: raise TypeError(
            "Invalid null: null should be a boolean value"
        )
        if isinstance(unique, bool):
            self.unique = unique
        else: raise TypeError(
            "Invalid unique: unique should be a boolean value"
        )
        self.primary_key = False
        if default == None:
            self.default = None
            self._default = False
        else:
            self.default = default
            self._default = True
        if isinstance(to_table, str):
            self.REFER = to_table
        else:
            if to_table.__base__ in (Model, AuthorizedUser):
                self.to_table = to_table
            else: raise TypeError(
                "Invalid to_table: to_table should be a Model"
            )
        if issubclass(on_delete.__class__, OnDelete):
            self.on_delete = on_delete
        else: raise TypeError(
            "Invalid on_delete: on_delete should be an OnDelete object (CASCADE, PROTECT, SET_NULL, SET_DEFAULT, or NO_ACTION)"
        )

    def resolve_string_reference(self, models_instances):
        to_table = models_instances[self.REFER]
        if to_table.__class__.__base__ in (Model, AuthorizedUser):
            self.to_table = to_table.__class__
        else: raise TypeError(
            "Invalid to_table: to_table should be a Model"
        )

class OneToOneField(Field):
    def __init__(self, to_table:Model, on_delete:OnDelete=CASCADE, default=None, primary_key:bool=False):
        self.null = False
        self.unique = True
        if primary_key in (True, False):
            self.primary_key = primary_key
        else: raise TypeError(
            "Invalid primary_key: primary_key should be a boolean"
        )
        if default == None:
            self.default = None
            self._default = False
        else:
            self.default = default
            self._default = True
        if to_table.__base__ in (Model, AuthorizedUser):
            self.to_table = to_table
        else: raise TypeError(
            "Invalid to_table: to_table should be a Model"
        )
        if issubclass(on_delete.__class__, OnDelete):
            self.on_delete = on_delete
        else: raise TypeError(
            "Invalid on_delete: on_delete should be an OnDelete object (CASCADE, PROTECT, SET_NULL, SET_DEFAULT, or NO_ACTION)"
        )

class ManyToManyField(Field):
    def __init__(self, to_table:Model, through:str, on_delete:OnDelete=CASCADE, default=None):
        self.null = True
        self.unique = False
        self.primary_key = False
        if isinstance(through, str):
            self.through = through
        else: TypeError(
            "Invalid through: through should be a string"
        )

        if default == None:
            self.default = None
            self._default = False
        else:
            self.default = default
            self._default = True
        if to_table.__base__ in (Model, AuthorizedUser):
            self.to_table = to_table
        else: raise TypeError(
            "Invalid to_table: to_table should be a Model"
        )
        if issubclass(on_delete.__class__, OnDelete):
            self.on_delete = on_delete
        else: raise TypeError(
            "Invalid on_delete: on_delete should be an OnDelete object (CASCADE, PROTECT, SET_NULL, SET_DEFAULT, or NO_ACTION)"
        )

    def __sqltype__(self):
        pass
