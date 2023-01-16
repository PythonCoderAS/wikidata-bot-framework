import sentry_sdk
from contextlib import contextmanager
from dotenv import dotenv_values
from typing import Iterator, Union

sentry_avilable = False


def load_sentry():
    global sentry_avilable
    data = dotenv_values(".env")
    if data.get("SENTRY_DSN", None):
        sentry_sdk.init(data["SENTRY_DSN"], traces_sample_rate=1.0)
        sentry_avilable = True


@contextmanager
def start_transaction(**kwargs) -> Iterator[Union[sentry_sdk.Transaction, None]]:
    if sentry_avilable:
        with sentry_sdk.start_transaction(**kwargs) as transaction:
            yield transaction
    else:
        yield None


@contextmanager
def start_span(**kwargs) -> Iterator[Union[sentry_sdk.Span, None]]:
    if sentry_avilable:
        span = sentry_sdk.Hub.current.scope.span
        if span is None:
            with sentry_sdk.start_span(**kwargs) as span:
                yield span
        else:
            with span.start_child(**kwargs) as span:
                yield span
    else:
        yield None
