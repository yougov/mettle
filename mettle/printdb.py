from sqlalchemy import create_engine
from mettle import models

def get_ddl():
    lines = []
    def dump(sql, *multiparams, **params):
        lines.append(str(sql.compile(dialect=engine.dialect)))
    engine = create_engine('postgresql://', strategy='mock', executor=dump)
    models.Base.metadata.create_all(engine, checkfirst=False)
    return ''.join(lines)

if __name__ == '__main__':
    print get_ddl()
