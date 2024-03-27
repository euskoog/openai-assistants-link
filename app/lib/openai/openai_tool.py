import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import inspect
import json
from logging import getLogger
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar, cast
from pydantic import BaseModel, Field, PrivateAttr, validate_arguments
import requests

T = TypeVar("T")

logger = getLogger("Tools")


class ExposeSyncMethodsMixin:
    """
    A mixin that can take functions decorated with `expose_sync_method`
    and automatically create synchronous versions.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for method in list(cls.__dict__.values()):
            if callable(method) and hasattr(method, "_sync_name"):
                sync_method_name = method._sync_name
                setattr(cls, sync_method_name, method._sync_wrapper)


async def run_async(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Runs a synchronous function in an asynchronous manner.

    Args:
        fn: The function to run.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The return value of the function.
    """

    async def wrapper() -> T:
        try:
            return await loop.run_in_executor(
                None, functools.partial(fn, *args, **kwargs)
            )
        except Exception as e:
            # propagate the exception to the caller
            raise e

    loop = asyncio.get_event_loop()
    return await wrapper()


def run_sync(coroutine: Coroutine[Any, Any, T]) -> T:
    """
    Runs a coroutine from a synchronous context, either in the current event
    loop or in a new one if there is no event loop running. The coroutine will
    block until it is done. A thread will be spawned to run the event loop if
    necessary, which allows coroutines to run in environments like Jupyter
    notebooks where the event loop runs on the main thread.

    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            with ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coroutine)
                return future.result()
        else:
            return asyncio.run(coroutine)
    except RuntimeError:
        return asyncio.run(coroutine)


def expose_sync_method(name: str) -> Callable[..., Any]:
    """
    Decorator that automatically exposes synchronous versions of async methods.
    Note it doesn't work with classmethods.

    Args:
        name: The name of the synchronous method.

    Returns:
        The decorated function.

    Example:
        Basic usage:
        ```python
        class MyClass(ExposeSyncMethodsMixin):

            @expose_sync_method("my_method")
            async def my_method_async(self):
                return 42

        my_instance = MyClass()
        await my_instance.my_method_async() # returns 42
        my_instance.my_method()  # returns 42
        ```
    """

    def decorator(
        async_method: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(async_method)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            coro = async_method(*args, **kwargs)
            return run_sync(coro)

        # Cast the sync_wrapper to the same type as the async_method to give the
        # type checker the needed information.
        casted_sync_wrapper = cast(Callable[..., T], sync_wrapper)

        # Attach attributes to the async wrapper
        setattr(async_method, "_sync_wrapper", casted_sync_wrapper)
        setattr(async_method, "_sync_name", name)

        # return the original async method; the sync wrapper will be added to
        # the class by the init hook
        return async_method

    return decorator


def cast_callable_to_model(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> BaseModel:
    response = validate_arguments(function).model
    for field in ["args", "kwargs", "v__duplicate_kwargs"]:
        fields = cast(Dict[str, Any], response.__fields__)
        fields.pop(field, None)
    response.__title__ = name or function.__name__
    response.__name__ = name or function.__name__
    response.__doc__ = description or function.__doc__
    return response


class Function(BaseModel):
    name: str
    description: Optional[str]
    parameters: dict[str, Any]
    fn: Callable = Field(exclude=True)

    # Private field that holds the executable function, if available
    _python_fn: Optional[Callable[..., Any]] = PrivateAttr(default=None)

    # def validate_json(self: Self, json_data: Union[str, bytes, bytearray]) -> T:
    #     if self.model is None:
    #         raise ValueError("This Function was not initialized with a model.")
    #     return self.model.model_validate_json(json_data)

    # @classmethod
    # def create(
    #     cls, *, _python_fn: Optional[Callable[..., Any]] = None, **kwargs: Any
    # ) -> "Function":
    #     """New way to create a Function"""
    #     instance = cls(**kwargs)
    #     if _python_fn is not None:
    #         instance._python_fn = _python_fn
    #     return instance

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        """Old way to create a Function"""
        model = cast_callable_to_model(fn)
        instance = cls(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=model.schema(),
            fn=fn,
        )

        if fn is not None:
            instance._python_fn = fn

        return instance


class OpenAITool(BaseModel):
    type: str
    function: Optional[Function] = None

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        return cls(
            type="function",
            function=Function.from_function(fn=fn, name=name, description=description),
        )

    def to_dict(self) -> dict:
        if self.type == "retrieval":
            return {
                "type": self.type,
            }

        return {
            "type": self.type,
        }


OpenAIRetrievalTool = OpenAITool(type="retrieval")
OpenAICodeInterpreterTool = OpenAITool(type="code_interpreter")


def web_search(url: str):
    """Get the content of a web page"""
    return requests.get(url).content.decode()


def call_function_tool(
    tools: list[OpenAITool],
    function_name: str,
    function_arguments_json: str,
    return_string: bool = False,
) -> str:
    """
    Helper function for calling a function tool from a list of tools, using the arguments
    provided by an LLM as a JSON string. This function handles many common errors.
    """

    tool = next(
        (
            tool
            for tool in tools
            if getattr(tool, "function", None) and tool.function.name == function_name
        ),
        None,
    )
    if (
        not tool
        or not tool.function
        or not tool.function._python_fn
        or not tool.function.name
    ):
        raise ValueError(f"Could not find function '{function_name}'")

    arguments = json.loads(function_arguments_json)
    logger.debug(
        f"{tool.function.name}", f"called with arguments: {json.dumps(arguments)}"
    )
    output = tool.function._python_fn(**arguments)

    if inspect.isawaitable(output):
        output = run_sync(output)
    truncated_output = str(output)[:100]
    if len(truncated_output) < len(str(output)):
        truncated_output += "..."
    logger.debug(f"{tool.function.name}", f"returned: {truncated_output}", "green")
    if return_string and not isinstance(output, str):
        output = json.dumps(output)
    return output
