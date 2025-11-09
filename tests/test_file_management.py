import pytest

from file_management import extract_job_id


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("QWEN_EDIT_abcd1234_00001.png", "abcd1234"),
        ("EDIT_abcd1234_00001.png", "abcd1234"),
        ("GEN_UP_abcd1234.png", "abcd1234"),
        ("GEN_VAR_abcd1234_00001.jpg", "abcd1234"),
        ("GEN_I2I_abcd1234_00001.png", "abcd1234"),
        ("GEN_abcd1234.png", "abcd1234"),
    ],
)
def test_extract_job_id_supported_prefixes(filename, expected):
    assert extract_job_id(filename) == expected


@pytest.mark.parametrize(
    "filename",
    [
        "",
        None,
        "random_file.png",
        "QWEN_abcd1234.png",
        "EDIT_short.png",
    ],
)
def test_extract_job_id_invalid_inputs(filename):
    assert extract_job_id(filename) is None
