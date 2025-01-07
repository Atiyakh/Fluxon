import importlib.util
import Fluxon.Database.Models as Models
import sys
import os

def get_previeus_schema(directory_path):
    files = []
    for root, _, files_in_dir in os.walk(directory_path):
        for file in files_in_dir:
            files.append(file)
    return files

def schema_number(files:list[str]):
    number = 1
    for file in files: # schema_xxxxx.sql
        if file.find("schema_") == 0 and file and file.find(".sql") == 12:
            if file[7:-4].isdigit():
                number = max(number, int(file[7:-4])+1)
    return "0"*(5-len(str(number)))+str(number)

def save_schema(schema, number, database_schema_dir_path):
    with open(os.path.join(database_schema_dir_path, f"schema_{number}.sql"), 'w') as schema_file:
        schema_file.write(schema)

class ModelsParser:
    def load_models(self, models_path):
        spec = importlib.util.spec_from_file_location("models", models_path)
        self.models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.models_module)
        sys.modules["models"] = self.models_module

    def detect_models_in_module(self):
        self.models_instances = dict()
        for attrib_name in dir(self.models_module):
            attrib = self.models_module.__getattribute__(attrib_name)
            if hasattr(attrib, '__base__'):
                if attrib.__base__.__name__ in ("Model", "AuthorizedUser"):
                    self.models_instances[attrib.__name__] = attrib()

    def extract_fields(self):
        self.fields = dict()
        for model_name, model_obj in self.models_instances.items():
            self.fields[model_name] = dict()
            for attrib_name in dir(model_obj):
                attrib = model_obj.__getattribute__(attrib_name)
                if hasattr(attrib.__class__, '__base__'):
                    if attrib.__class__.__base__.__name__ == 'Field':
                        attrib.__modelname__ = model_name
                        attrib.__fieldname__ = model_name
                        self.fields[model_name][attrib_name] = attrib

    def break_many_to_many(self):
        self.mant_to_manys = dict()
        for model_name, fields in self.fields.items():
            for field_name, field in fields.items():
                if isinstance(field, Models.ManyToManyField):
                    intermediate_table_name = field.through
                    if intermediate_table_name not in self.models_instances:
                        raise ModuleNotFoundError(
                            f"Intermediate table {field.through} doesn't exist"
                        )
                    self.mant_to_manys[intermediate_table_name] = [model_name, field.to_table.__name__]

    def look_for_primary_keys(self):
        self.primary_keys = dict()
        self.fields_to_pk_ = dict()
        for model_name, fields in self.fields.items():
            pk = None
            for field_name, field in fields.items():
                if field.primary_key:
                    if pk == None:
                        pk = field_name
                        field_ = field
                    else: raise AttributeError(
                        f"A model can't have more than one primary key ({model_name})->({pk})({field})"
                    )
            if pk:
                if isinstance(field_, (Models.ForeignKey, Models.OneToOneField)):
                    self.primary_keys[model_name] = pk
                    self.fields_to_pk_[model_name] = field_
            elif pk == None:
                field = Models.AutoField(primary_key=True)
                field.__modelname__ = model_name
                field.__fieldname__ = 'id'
                self.fields[model_name]['id'] = field
                self.primary_keys[model_name] = 'id'

    def look_for_foreign_keys(self):
        self.foreigns = dict()
        self.foreigns_tables = dict() # for "intertabular" relations
        self.one_to_ones = list()
        for model_name, fields in self.fields.items():
            foreigns = []
            foreigns_tables = []
            for field_name, field in fields.items():
                if isinstance(field, Models.ForeignKey):
                    foreigns.append(field_name)
                    if not hasattr(field, 'to_table'):
                        field.resolve_string_reference(self.models_instances)
                    foreigns_tables.append(field.to_table.__name__)
                elif isinstance(field, Models.OneToOneField):
                    self.one_to_ones.append(field)
                    foreigns.append(field_name)
                    foreigns_tables.append(field.to_table.__name__)
                self.foreigns[model_name] = foreigns
                if model_name in foreigns_tables: foreigns_tables.remove(model_name)
                self.foreigns_tables[model_name] = foreigns_tables

    def sqltype(self, field, remove_auto=False):
        if isinstance(field, Models.PositiveIntegerField):
            return field.__sqltype__(field.__fieldname__)
        elif isinstance(field, (Models.OneToOneField, Models.ForeignKey)):
            to_field_name = self.primary_keys[field.to_table.__name__]
            to_field = self.fields[field.to_table.__name__][to_field_name]
            return self.sqltype(to_field, remove_auto=True)
        elif isinstance(field, Models.AutoField):
            if field.__fieldname__ == self.primary_keys[field.__modelname__]:
                return field.__sqltype__(remove_auto=remove_auto)
            else:
                return field.__sqltype__(remove_auto=True)
        else:
            return field.__sqltype__()

    def parse_field(self, field_name, field, table_name):
        add_unique = False
        if field.unique: add_unique = True
        if not field.null: add_not_null = True
        else: add_not_null = False
        if not isinstance(field, (Models.OneToOneField, Models.ManyToManyField)):
            return f"    {field_name} {self.sqltype(field)}" + (" NOT NULL" if add_not_null else "") + (" UNIQUE" if add_unique else "") + ",\n"
        elif isinstance(field, Models.OneToOneField):
            return f"    {field_name} {self.sqltype(field)}" + (" NOT NULL" if add_not_null else "") + " UNIQUE" + ",\n"
        else: return ""

    def parse_primary_key(self, table_name):
        return f"    PRIMARY KEY ({self.primary_keys[table_name]})\n);"

    def parse_foreign_key(self, filed_name, field):
        to_field_name = self.primary_keys[field.to_table.__name__]
        return f"    FOREIGN KEY ({filed_name}) REFERENCES {field.to_table.__name__}({to_field_name}) ON DELETE {field.on_delete.__class__.__name__[:-1]},\n"

    def parse_many_to_many(self, table_name):
        table_1, table_2 = self.mant_to_manys[table_name]
        field_1 = ""; field_2 = ""
        for field_name, field in self.fields[table_name].items():
            if isinstance(field, Models.ForeignKey):
                if field.to_table.__name__ in (table_1, table_2):
                    result = f"{field_name}"
                    if field_1:
                        if not field_2:
                            field_2 = result
                        else: raise LookupError(
                            f"Invalid intermediate table ({table_name})"
                        )
                    else:
                        field_1 = result
        if not (field_1 and field_2):
            raise LookupError(
                f"Invalid intermediate table ({table_name})"
            )
        else:
            return f"    UNIQUE ({field_1}, {field_2}),\n"

    def construct_sql_syntax(self):
        self.SQL = dict()
        for table_name in self.models_instances:
            SQL_Statement = ""
            fields = self.fields[table_name]
            SQL_Statement += f"CREATE TABLE {table_name}(\n"
            for field_name, field in fields.items():
                SQL_Statement += self.parse_field(field_name, field, table_name)
            for filed_name in self.foreigns[table_name]:
                SQL_Statement += self.parse_foreign_key(filed_name, self.fields[table_name][filed_name])
            if table_name in self.mant_to_manys:
                SQL_Statement += self.parse_many_to_many(table_name)
            SQL_Statement += self.parse_primary_key(table_name)
            self.SQL[table_name] = SQL_Statement
    
    def ordering_sql_statements(self):
        avaliable_dependencies = [] # tables ordered already
        self.ordered_queries = []
        for _ in range(15): # looping throu for 15 times only
            for table_name, foreigns_tables in self.foreigns_tables.items():
                if table_name in avaliable_dependencies: pass
                elif not foreigns_tables: # good starting point; no dependencies
                    self.ordered_queries.append(self.SQL[table_name])
                    avaliable_dependencies.append(table_name)
                elif all(item in avaliable_dependencies for item in foreigns_tables):
                    self.ordered_queries.append(self.SQL[table_name])
                    avaliable_dependencies.append(table_name)
        if len(avaliable_dependencies) < len(self.models_instances):
            raise RecursionError(
                "Unable to come up with the right queries order; foriegn key dependency error"
            )

    def __init__(self, models_path, database_schema_dir_path):
        # Analyze Models
        self.load_models(models_path)
        self.detect_models_in_module()
        self.extract_fields()
        self.break_many_to_many()
        self.look_for_primary_keys()
        self.look_for_foreign_keys()
        # Generate Sql Queries
        self.construct_sql_syntax()
        self.ordering_sql_statements()
        text_output = "\n\n".join(self.ordered_queries)
        # Save schema to databse dir
        self.schema_no = schema_number(get_previeus_schema(
            database_schema_dir_path
        ))
        save_schema(
            text_output, self.schema_no, database_schema_dir_path
        )
