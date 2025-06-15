import os
import traceback
import sqlite3
import logging
from Fluxon.Database.db_models_parser import ModelsParser, wipe_sqlite_database, current_schema_no, get_prev_schema
from Endpoint.async_server import AsyncServer
from Endpoint.server_utils import console_server_terminate

def interactive_console(server:AsyncServer, shared_data:dict, logger:logging.Logger):
    # NOTE this function runs in a separate thread
    while True:
        try:
            command = input()
            # command processing goes here
            if command.lower() == "terminate":
                console_server_terminate(
                    server, shared_data, logger
                )
                break
            elif command.lower() == "saveschema":
                parsed_model = ModelsParser(
                    models_path=shared_data["models"].__file__,
                    database_schema_dir_path=shared_data["database-schema-dir"],
                    dbms = server.router.database_api.DBMS
                )
                logger.info(f"[Fluxon-Console] Schema has been saved successfully - schema_file_name: {parsed_model.schema_file_name}")
                print(f"Schema saved successfully... ({parsed_model.schema_file_name})")
            elif command.lower().find("updateschema") == 0:
                number = command[13:]
                if not number:
                    number = str(current_schema_no(get_prev_schema(shared_data["database-schema-dir"])))
                sql_commands = ""
                if number.isdigit():
                    file_name = "schema_"+("0"*(5-len(str(int(number)))))+str(int(number))+".sql"
                    try:
                        with open(os.path.join(shared_data["database-schema-dir"], file_name)) as schema_file:
                            sql_commands = schema_file.read()
                    except:
                        traceback.print_exc()
                        logger.error(f"Failed to read from {file_name}")
                        print(f"ERROR: Failed to read from {file_name}")
                else:
                    logger.error(f"Invalid schema number {number}")
                    print(f"ERROR: Invalid schema number {number}")
                if sql_commands:
                    wipe_sqlite_database(shared_data["database-path"]) # TODO integrate other databases
                    conn = sqlite3.connect(shared_data["database-path"])
                    cursor = conn.cursor()
                    cursor.executescript(sql_commands)
                    conn.commit()
                    conn.close()
                    logger.info("[Fluxon-Console] Schema has been updated successfully")
                    print(f"Schema updated successfully... ({"0"*(5-len(str(number)))+str(number)})")
            else:
                try: exec(command, locals())
                except: traceback.print_exc()
        except EOFError:
            # NOTE in some text editors, EOFError is raised when ctrl-c is pressed as well, so we will simply ignore it
            pass
        except:
            traceback.print_exc()
            print("[Fluxon-Console] Error: Invalid command or execution error [UnexpectedError]")
