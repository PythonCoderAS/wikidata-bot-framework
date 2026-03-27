import json
from abc import ABC
from typing import (
    TypeAlias,
    Callable,
    Any,
    TYPE_CHECKING,
    TypeVar,
    overload,
    Literal,
)

import pywikibot
from pywikibot.exceptions import OtherPageSaveError
from typing_extensions import ParamSpec
from pytest import skip
from wikidata_bot_framework import PropertyAdderBot, site


class TestPAB(PropertyAdderBot, ABC):
    pass


SetupAndTeardownModuleFunction: TypeAlias = Callable[[], None]
T = TypeVar("T")
if TYPE_CHECKING:
    P = ParamSpec("P")
    SetupAndTeardownClassmethodFunction: TypeAlias = Callable[[type[T]], None]
else:
    SetupAndTeardownClassmethodFunction: TypeAlias = (
        classmethod  # Not subscriptable in runtime
    )


@overload
def load_revision_for_test(
    revision_id: int, *, add_cls: Literal[False] = False
) -> tuple[SetupAndTeardownModuleFunction, SetupAndTeardownModuleFunction]: ...


@overload
def load_revision_for_test(
    revision_id: int, *, add_cls: Literal[True]
) -> tuple[
    SetupAndTeardownClassmethodFunction, SetupAndTeardownClassmethodFunction
]: ...


def load_revision_for_test(
    revision_id: int, *, add_cls: bool = False
) -> (
    tuple[SetupAndTeardownModuleFunction, SetupAndTeardownModuleFunction]
    | tuple[SetupAndTeardownClassmethodFunction, SetupAndTeardownClassmethodFunction]
):
    """Load a revision.

    Usage:

    setup_module, teardown_module = load_revision_for_test(123)

    class TestClass:
        setup_class, teardown_class = load_revision_for_test(123, add_cls=True)


    :param revision_id: The revision ID of the sandbox item to load.
    :param add_cls: Whether to return classmethods
    :return: A setup and teardown function
    """

    current_data: dict[str, Any] = {}
    current_revision: int

    def setup():
        import pywikibot.config

        if pywikibot.config.simulate:
            skip("Cannot load revisions when in simulate mode")
        nonlocal current_revision
        sandbox_item.get(force=True)
        current_data.update(sandbox_item.toJSON())
        current_revision = sandbox_item.latest_revision_id
        data = json.loads(sandbox_item.getOldVersion(revision_id))
        retry_count = 0
        while retry_count <= 5:
            try:
                sandbox_item.editEntity(
                    data, summary=f"Loading revision {revision_id} for test", bot=True
                )
            except OtherPageSaveError as e:
                if isinstance(e.reason, str) and e.reason.strip().startswith(
                    "no-external-page"
                ):
                    retry_count += 1
                    continue
                else:
                    raise
            break
        sandbox_item.get(force=True)

    def teardown():
        sandbox_item.get(force=True)

    if add_cls:

        @classmethod  # type: ignore[misc] # noqa
        def setup_class(cls: type[T]):
            return setup()

        @classmethod  # type: ignore[misc] # noqa
        def teardown_class(cls: type[T]):
            return teardown()

        return setup_class, teardown_class

    return setup, teardown


sandbox_item = pywikibot.ItemPage(site, "Q4115189")
