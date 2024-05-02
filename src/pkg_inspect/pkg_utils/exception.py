from .utils import wraps
from .util_types import *


class PkgException(BaseException):
    """Base exception class for handling all exceptions raised within the `pkg-inspect` package."""

    BASE_EXCEPTIONS: TupleExceptions = (Exception, TypeError, ValueError)

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    @classmethod
    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        return cls(*args, **kwds)

    @classmethod
    def verify_exceptions(
        cls, exceptions: ExceptionOrTupleExceptions = None
    ) -> ExceptionOrTupleExceptions:
        """
        This method ensures that the `exceptions` argument is a tuple and adds the base `Exception` class to the exceptions tuple.

        ### Args:
            - `exceptions` (Union[Type[Exception], tuple[Type[Exception]]]): The exception(s) to catch.

        ### Returns:
            - `Union[Type[Exception], tuple[Type[Exception]]]`: The exception(s) to catch with the base `Exception` class added.

        ### Raises:
            - `PkgException`: The exceptions argument must all be a subclass of BaseException.
        """

        try:
            exceptions: ExceptionOrTupleExceptions = exceptions or Exception
            # Ensure that the `exceptions` argument is a tuple to allow for multiple exceptions to be caught.
            if all(
                (
                    isinstance(exceptions, type),
                    not isinstance(exceptions, Iterable),
                    callable(exceptions),
                )
            ):
                exceptions = (exceptions,)

            # Ensure that all exceptions are subclasses of `BaseException`.
            if not all(issubclass(e, BaseException) for e in exceptions):
                raise PkgException(
                    "The exceptions argument must all be a subclass of BaseException."
                )

            # Add the base `Exception` class to the exceptions tuple
            # by default if it is not already in the exceptions tuple.
            if Exception not in exceptions:
                exceptions += (*{*cls.BASE_EXCEPTIONS, Exception},)
            # Otherwise, exceptions will be set to the `Exception` class.
        except cls.BASE_EXCEPTIONS as errs:
            raise PkgException(
                "Failed to verify the provided exceptions."
                f"\n{exceptions = !r}"
                f"\n{errs}"
            )
        # Return the exceptions (tuple).
        return exceptions

    def exception_handler(
        item: str = "",
        msg: str = "",
        exceptions: ExceptionOrTupleExceptions = Exception,
        raise_with: ExceptionT = None,
    ) -> CallableT:
        """
        This decorator catches exceptions raised by the decorated method and raises a
        `PkgException` with a custom message.

            - `item` (str): The name of the item being retrieved.
            - `exceptions` (Union[Type[Exception], tuple[Type[Exception]]]): The exception(s) to catch.

        ### Raises:
            - `PkgException`: An error occurred while attempting to retrieve the object.
        """

        # Verify the exceptions argument.
        # If the exceptions argument is not a tuple, convert it to a tuple.
        # If the exceptions argument is None, set it to the base exceptions tuple.
        exceptions = PkgException.verify_exceptions(exceptions)
        raise_with = next((e_ for e_ in exceptions if e_ == raise_with), PkgException)

        def method(func: CallableT) -> CallableT:
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                n = "\n{}\n".format
                if msg:
                    p = n(msg)
                else:
                    p = n(f"An error occurred while attempting to retrieve {item!r}")
                try:
                    f = func(self, *args, **kwargs)
                except exceptions as e:
                    raise raise_with(f"{p}\n" f"[ERROR MSG]: {e}")
                return f

            return wrapper

        return method


def RedPkgE(*args):
    """
    Creates a custom `PkgException` object with the first message in red text.

    This function takes a variable number of arguments and returns a `PkgException` object with a formatted message.
    The first argument is displayed in red text, while subsequent arguments are displayed in the default text color.
    """

    red_msg, *args = args
    return PkgException(f"\033[1;31m{red_msg}\033[0m" f"\n{' '.join(args)}")
