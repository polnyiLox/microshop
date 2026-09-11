from app.core.config import DataBaseSettings


def test_database_url_encodes_credentials() -> None:
    config = DataBaseSettings(
        user="service@user",
        password="strong:p@ss/word#",
        host="database",
        port=5432,
        name="service database",
    )

    assert config.url == (
        "postgresql+asyncpg://service%40user:strong%3Ap%40ss%2Fword%23@"
        "database:5432/service%20database"
    )
