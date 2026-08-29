"""
Tests for the API extension system.
"""

import pytest
from fastapi import APIRouter, FastAPI

from aurite.bin.api.extension import Extension, ExtensionFactory


class TestExtension(Extension):
    """Test extension class for unit tests."""

    called = False
    app_instance = None

    def __call__(self, app: FastAPI):
        """Record that the extension was called."""
        TestExtension.called = True
        TestExtension.app_instance = app

        # Add a simple route
        router = APIRouter(prefix="/test", tags=["Test"])

        @router.get("/hello")
        def hello():
            return {"message": "test"}

        app.include_router(router)


class NotAnExtension:
    """Class that doesn't inherit from Extension."""

    def __call__(self, app: FastAPI):
        pass


def test_extension_is_abstract():
    """Test that Extension cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Extension()  # type: ignore[abstract]


def test_extension_can_be_subclassed():
    """Test that Extension can be subclassed properly."""
    ext = TestExtension()
    assert isinstance(ext, Extension)


def test_extension_factory_get_valid_extension():
    """Test ExtensionFactory.get() with a valid extension path."""
    extension_class = ExtensionFactory.get("tests.unit.bin.api.test_extension.TestExtension")

    # Should return the class, not an instance
    # Note: Due to dynamic import, class identity may differ, so check name and inheritance
    assert extension_class.__name__ == "TestExtension"
    assert extension_class.__module__ == "tests.unit.bin.api.test_extension"
    assert issubclass(extension_class, Extension)


def test_extension_factory_get_invalid_module():
    """Test ExtensionFactory.get() with an invalid module path."""
    with pytest.raises(ImportError):
        ExtensionFactory.get("nonexistent.module.Extension")


def test_extension_factory_get_invalid_class():
    """Test ExtensionFactory.get() with an invalid class name."""
    with pytest.raises(AttributeError):
        ExtensionFactory.get("tests.unit.bin.api.test_extension.NonExistentClass")


def test_extension_factory_get_not_extension_subclass():
    """Test ExtensionFactory.get() with a class that doesn't inherit from Extension."""
    with pytest.raises(TypeError, match="must be a subclass of Extension"):
        ExtensionFactory.get("tests.unit.bin.api.test_extension.NotAnExtension")


def test_extension_registration_with_app():
    """Test that an extension can register routes with a FastAPI app."""
    from fastapi import FastAPI

    # Reset test state
    TestExtension.called = False
    TestExtension.app_instance = None

    # Create app and extension
    app = FastAPI()
    extension = TestExtension()

    # Call the extension
    extension(app)

    # Verify it was called and received the app
    assert TestExtension.called is True
    assert TestExtension.app_instance is app

    # Verify route was registered
    routes = [getattr(route, "path", None) for route in app.routes]  # type: ignore[attr-defined]
    routes = [r for r in routes if r is not None]
    assert "/test/hello" in routes


def test_extension_factory_module_only_path():
    """Test ExtensionFactory.get() with module path only (looks for Extension class)."""
    # When given a module path only, it tries to find "Extension" class
    # This test module doesn't have an "Extension" class at the top level
    with pytest.raises((AttributeError, TypeError)):
        ExtensionFactory.get("tests.unit.bin.api.test_extension")


def test_multiple_extensions_on_same_app():
    """Test that multiple extensions can be loaded on the same app."""

    class Extension1(Extension):
        def __call__(self, app):
            router = APIRouter(prefix="/ext1")

            @router.get("/test")
            def test1():
                return {"ext": "1"}

            app.include_router(router)

    class Extension2(Extension):
        def __call__(self, app):
            router = APIRouter(prefix="/ext2")

            @router.get("/test")
            def test2():
                return {"ext": "2"}

            app.include_router(router)

    app = FastAPI()

    ext1 = Extension1()
    ext2 = Extension2()

    ext1(app)
    ext2(app)

    routes = [getattr(route, "path", None) for route in app.routes]  # type: ignore[attr-defined]
    routes = [r for r in routes if r is not None]
    assert "/ext1/test" in routes
    assert "/ext2/test" in routes
