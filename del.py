import database
import inspect
print([name for name, obj in inspect.getmembers(database.Database, inspect.isfunction)])