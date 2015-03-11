#!/usr/bin/env python
from sqlalchemy import create_engine
from mettle import models

def get_ddl():
    statements = []
    def dump(sql, *multiparams, **params):
        statements.append(str(sql.compile(dialect=engine.dialect)).strip())
    engine = create_engine('postgresql://', strategy='mock', executor=dump)
    models.Base.metadata.create_all(engine, checkfirst=False)
    return ';\n\n'.join(statements) + ';'

if __name__ == '__main__':
    print get_ddl()
