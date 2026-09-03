from app.core.config import Settings


def test_cors_origins_are_parsed():
    settings = Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        openrouter_api_key="test-key",
        jwt_secret_key="test-secret",
        cors_origins="http://localhost:3000, https://example.com",
    )

    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://example.com",
    ]


def test_empty_cors_origins_are_removed():
    settings = Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        openrouter_api_key="test-key",
        jwt_secret_key="test-secret",
        cors_origins="http://localhost:3000,,",
    )

    assert settings.cors_origin_list == [
        "http://localhost:3000",
    ]