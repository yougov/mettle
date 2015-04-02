import logging
import smtplib
import email.utils
from email.mime.text import MIMEText
import urlparse
import textwrap

from mettle.settings import get_settings
from mettle.models import Notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def notify_failed_run(db, run, subject=None, body=None):
    to = run.pipeline.notification_list.recipients
    if subject is None:
        subject = "Pipeline %s has failed" % run.pipeline.name

    if body is None:
        body = textwrap.dedent("""
            Pipeline "{pipeline}" has ended with failures.
            The numbers of attempts has reached the maximum retries allowed.
            Service name: {service}
            Pipeline name: {pipeline}
            Run ID: {run_id}
            """.format(
            service=run.pipeline.service.name,
            pipeline=run.pipeline.name,
            run_id=run.id,
        ))
    send_email(to, subject, body)

    db.add(Notification(
        pipeline_run=run,
        pipeline=run.pipeline,
        service=run.pipeline.service,
        message=body,
    ))


def send_email(to, subj, body):
    """
    Send an email using the server specified by the 'smtp_url' setting.

    'to' should be a list of addresses.

    'from' should be a single address.

    Any address may be provided as a plain string like 'joe@somewhere.com', or
    as a tuple like ('Joe Somebody', 'joe@somewhere.com').
    """
    settings = get_settings()

    msg = MIMEText(body)
    msg['From'] = format_email_address(settings.smtp_sender)
    msg['Subject'] = subj
    for r in to:
        addr = format_email_address(r)
        msg.add_header('To', addr)

    logger.info('Sending email "{subject}" to {recipients}.'.format(
        subject=subj,
        recipients=', '.join([str(x) for x in to]),
    ))

    if settings.smtp_url is not None:
        with SMTPServer(settings.smtp_url) as server:
            server.sendmail(
                just_email_address(settings.smtp_sender),
                msg.get_all('To'),
                msg.as_string()
            )
    else:
        logger.warning('settings.smtp_url is None.  Email not sent!')


def just_email_address(addr):
    """Given either a plain email address string like 'joe@somewhere.com', or a
    two-item tuple like ('Joe Somebody', 'joe@somewhere.com'), return just the
    actual email address part."""
    if isinstance(addr, basestring):
        return addr
    elif len(addr) == 2:
        return addr[1]
    else:
        raise ValueError("Addr must be either a string, or a tuple of two "
                         "strings.")


def format_email_address(addr):
    if isinstance(addr, basestring):
        return addr
    elif len(addr) == 2:
        return email.utils.formataddr(addr)
    else:
        raise ValueError("Addr must be either a string, or a tuple of two "
                         "strings.")


class SMTPServer(object):
    def __init__(self, url, use_tls=True):
        self.url = url
        self.use_tls = use_tls

    def __enter__(self):
        parsed = urlparse.urlsplit(self.url)
        self.server = smtplib.SMTP(host=parsed.hostname, port=parsed.port)
        if self.use_tls:
            self.server.starttls()

        return self.server

    def __exit__(self, type, value, traceback):
        self.server.quit()
