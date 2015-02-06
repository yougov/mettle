from mettle import models
from mettle.settings import get_settings
from mettle.db import make_session_cls, parse_pgurl

settings = get_settings()

session = make_session_cls(settings.db_url)()

foo_svc = models.Service(name='foo', updated_by='test')

ns_list = models.NotificationList(name='foo', updated_by='test', recipients=[
    'brent.tubbs@gmail.com',
])

bar_pipeline = models.Pipeline(name='bar',
                               crontab='0 2 * * *',
                               service=foo_svc,
                               notification_list=ns_list,
                               updated_by='test')

session.add_all([
    foo_svc,
    ns_list,
    bar_pipeline,
])
session.commit()
