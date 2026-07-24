from app.settings import Settings


def test_gemini_settings_are_optional_for_existing_searches() -> None:
    settings = Settings(
        google_maps_api_key="google-key",
        _env_file=None,
    )

    assert settings.gemini_api_key is None
    assert settings.gemini_model == "gemini-3.6-flash"


def test_gemini_api_key_is_stored_as_a_secret() -> None:
    settings = Settings(
        google_maps_api_key="google-key",
        gemini_api_key="gemini-key",
        _env_file=None,
    )

    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "gemini-key"
    assert "gemini-key" not in repr(settings)
