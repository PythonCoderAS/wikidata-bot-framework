from contextlib import contextmanager
from typing import Iterator, Union

import sentry_sdk
import sentry_sdk.tracing
from dotenv import dotenv_values

sentry_avilable = False


def load_sentry():
    global sentry_avilable
    data = dotenv_values(".env")
    if data.get("SENTRY_DSN", None):
        sentry_sdk.init(
            data["SENTRY_DSN"],
            traces_sample_rate=1.0,
            _experiments={
                "profiles_sample_rate": 1.0,
            },
            ignore_errors=[KeyboardInterrupt],
            attach_stacktrace=True,
        )
        sentry_avilable = True


@contextmanager
def start_transaction(
    **kwargs,
) -> Iterator[Union[sentry_sdk.tracing.Span, None]]:
    if sentry_avilable:
        with sentry_sdk.start_transaction(**kwargs) as transaction:
            yield transaction
    else:
        yield None


@contextmanager
def start_span(**kwargs) -> Iterator[Union[sentry_sdk.tracing.Span, None]]:
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


def report_exception(*args, **kwargs) -> Union[str, None]:
    if sentry_avilable:
        return sentry_sdk.capture_exception(*args, **kwargs)
    return None
