"""Stored secrets (flaskspark.core.secrets): the scheme with known vectors (another program with the same scheme reads
them), the key from the environment or an env file, its configurable name and the modules' own keys."""
from __future__ import annotations

import pytest

from flaskspark.core import paths, secrets

KEY = "correct horse battery staple"
#: urlsafe_b64(SHA-256(KEY)): the Fernet key of KEY
DERIVED = b"xLvLH77JnWW_WdhcjLYu4tuWPw_hBvSD2a-nO9Tjmoo="
#: Fernet tokens of KEY, made by another program with the same scheme
TOKENS = {
    "gAAAAABlU_EAM477DulT8K5YqxFjKhvPk2GYxFb8-I11lUY2M497U53Ke6MypsfTBx1CngMCL2A4edHC_ws06pMh9gzRwmxkVQ==":
        "s3cret-api-key",
    "gAAAAABq9zz123xdHKdJksc_jw3y7TlrVbjwKlNu-RCTh0NjeQw6S9Tih-h_FEUUFltQvAgM8M2JlW72Uxh3JwpikBn9KlN5jg==":
        "umlaut äöü",
}


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """No key in the environment, an empty config directory."""
    for name in ("APP_SECRET_KEY", "APP_SECRET_KEY_ENV", "APP_SECRET_KEY_SHOP", "LEGACY_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    return monkeypatch


def test_the_key_is_derived_with_sha256():
    assert secrets.derive(KEY) == DERIVED


@pytest.mark.parametrize("token, plain", TOKENS.items())
def test_known_tokens_stay_readable(token, plain):
    assert secrets.decrypt(token, KEY) == plain


def test_round_trip_with_the_environments_key(env):
    env.setenv("APP_SECRET_KEY", KEY)
    token = secrets.encrypt("pa$$word")
    assert token != "pa$$word" and secrets.decrypt(token) == "pa$$word"
    assert secrets.decrypt(token, KEY) == "pa$$word"


def test_another_key_cannot_read_it(env):
    token = next(iter(TOKENS))
    with pytest.raises(secrets.SecretKeyError, match="APP_SECRET_KEY changed"):
        secrets.decrypt(token, "another key")
    with pytest.raises(secrets.SecretKeyError):
        secrets.decrypt("not a token", KEY)


def test_without_a_key_it_says_which_variable_is_missing(env):
    with pytest.raises(secrets.SecretKeyError, match="APP_SECRET_KEY is missing"):
        secrets.encrypt("x")


def test_the_key_comes_from_the_core_env_file(env, tmp_path):
    (tmp_path / "app.env").write_text(f"APP_SECRET_KEY='{KEY}'\n")
    assert secrets.decrypt(next(iter(TOKENS))) == "s3cret-api-key"


def test_the_variables_name_can_be_changed(env):
    env.setenv("APP_SECRET_KEY_ENV", "LEGACY_KEY")
    env.setenv("LEGACY_KEY", KEY)
    assert secrets.env_key() == "LEGACY_KEY"
    assert secrets.for_module("shop").decrypt(next(iter(TOKENS))) == "s3cret-api-key"
    env.delenv("LEGACY_KEY")
    with pytest.raises(secrets.SecretKeyError, match="LEGACY_KEY is missing"):
        secrets.encrypt("x")


def test_a_module_uses_the_shared_key_unless_it_has_its_own(env, tmp_path):
    env.setenv("APP_SECRET_KEY", KEY)
    shop = secrets.for_module("shop")
    shared = shop.encrypt("shared")
    assert secrets.decrypt(shared) == "shared"  # the same key as everyone
    (tmp_path / "shop.env").write_text("APP_SECRET_KEY_SHOP=only for the shop\n")
    env.delenv("APP_SECRET_KEY")
    own = shop.encrypt("own")  # its env file brings its own key
    assert secrets.decrypt(own, "only for the shop") == "own"
    with pytest.raises(secrets.SecretKeyError):
        secrets.decrypt(own, KEY)
    assert secrets.module_env_key("web-shop") == "APP_SECRET_KEY_WEB_SHOP"


def test_mask():
    assert secrets.mask("sk-abcdef") == "sk-a…"
    assert secrets.mask("abc") == "…"
