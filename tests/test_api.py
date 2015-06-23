import json
import random
import string

from werkzeug.test import Client
import spa

from mettle.settings import get_settings, DEV_USERNAME
from mettle.db import make_session_cls
from mettle.web import make_app
from mettle import models


def get_db():
    settings = get_settings()
    return make_session_cls(settings.db_url)


def randchars():
    return ''.join([random.choice(string.letters) for x in xrange(12)])


def random_service(num_pipelines=1):
    svc = models.Service(
        name=randchars(),
        updated_by='test',
    )
    if num_pipelines:
        svc.pipeline_names = [randchars() for x in xrange(num_pipelines)]
    return svc


def random_notification_list():
    return models.NotificationList(
        name=randchars(),
        recipients=['%s@example.org' % randchars()],
        updated_by='test',
    )


def random_pipeline():
    svc = random_service(num_pipelines=1)
    pl = models.Pipeline(
        service=svc,
        name=svc.pipeline_names[0],
        notification_list=random_notification_list(),
        crontab='0 0 1 1 0',
        updated_by='test',
    )
    return pl


def unwrap_app(app):
    if isinstance(app, spa.app.App):
        return app
    return unwrap_app(app.app)


class Resp(spa.Response):
    def json(self):
        return json.loads(self.data)


def test_get_pipeline():
    db = get_db()()
    pl = random_pipeline()
    db.add(pl)
    db.commit()
    app = make_app()
    c = Client(app, Resp)
    url = unwrap_app(app).url('pipeline_detail', dict(
        service_name=pl.service.name,
        pipeline_name=pl.name,
    ))
    resp = c.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data['name'] == pl.name
    assert data['service_id'] == pl.service.id


def test_put_pipeline():
    db = get_db()()
    pl = random_pipeline()
    db.add(pl)
    db.commit()
    app = make_app()
    c = Client(app, Resp)
    url = unwrap_app(app).url('pipeline_detail', dict(
        service_name=pl.service.name,
        pipeline_name=pl.name,
    ))

    new_data = dict(
        active=False,
        retries=10,
        crontab='1 1 1 1 1',
    )
    resp = c.put(url, data=json.dumps(new_data), content_type='application/json')
    assert resp.status_code == 200

    api_data = resp.json()
    db.refresh(pl)
    for k, v in new_data.items():
        # Response data should show our changes.
        assert api_data[k] == v
        # Database should contain our changes.
        assert getattr(pl, k) == v

    assert pl.updated_by == DEV_USERNAME


def test_cannot_change_pipeline_name():
    db = get_db()()
    pl = random_pipeline()
    db.add(pl)
    db.commit()
    app = make_app()
    c = Client(app, Resp)
    url = unwrap_app(app).url('pipeline_detail', dict(
        service_name=pl.service.name,
        pipeline_name=pl.name,
    ))

    new_data = dict(
        name='foo'
    )
    resp = c.put(url, data=json.dumps(new_data), content_type='application/json')
    assert resp.status_code == 400


def test_cannot_change_pipeline_svc():
    db = get_db()()
    pl = random_pipeline()
    db.add(pl)
    db.commit()
    app = make_app()
    c = Client(app, Resp)
    url = unwrap_app(app).url('pipeline_detail', dict(
        service_name=pl.service.name,
        pipeline_name=pl.name,
    ))

    new_data = dict(
        service_id=0
    )
    resp = c.put(url, data=json.dumps(new_data), content_type='application/json')
    assert resp.status_code == 400


def test_new_crontab_pipeline():
    db = get_db()()
    svc = random_service()
    nl = random_notification_list()
    db.add(svc)
    db.add(nl)
    db.commit()
    app = make_app()
    c = Client(app, Resp)
    url = unwrap_app(app).url('pipeline_list', dict(
        service_name=svc.name,
    ))

    data = dict(
        name=svc.pipeline_names[0],
        notification_list_id=nl.id,
        retries=4,
        crontab='0 0 0 1 1',
    )
    resp = c.post(url, data=json.dumps(data), content_type='application/json')
    assert resp.status_code == 302

    url = unwrap_app(app).url('pipeline_detail', dict(
        service_name=svc.name,
        pipeline_name=svc.pipeline_names[0],
    ))
    assert resp.headers['Location'] == 'http://localhost' + url

    content = json.loads(resp.data)
    for k, v in data.items():
        assert content[k] == v

#def test_new_crontab_chained

#def test_retries_default
